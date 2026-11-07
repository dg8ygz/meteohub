#!/usr/bin/env python3
"""Configure one sensor's expected interval for both dashboard and SVG."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile
import time


def configure(path, sensor, interval):
    if not re.fullmatch(r'[a-z]+[0-9]+', sensor):
        raise ValueError('Invalid sensor ID')
    if isinstance(interval, bool) or not 1 <= interval <= 86400:
        raise ValueError('Interval must be 1..86400 seconds')
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError('Configuration must be an ordinary file')
    before = path.read_bytes() if path.exists() else None
    data = json.loads(before) if before is not None else {}
    if not isinstance(data, dict):
        raise ValueError('Configuration must be an object')
    intervals = data.setdefault('sensor_intervals_seconds', {})
    if not isinstance(intervals, dict):
        raise ValueError('Invalid sensor interval configuration')
    previous = intervals.get(sensor, 60)
    intervals[sensor] = interval
    if before is not None:
        backup = path.with_name(path.name + '.before-' + str(time.time_ns()))
        fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(before)
        print('BACKUP:', backup)
    fd, temporary = tempfile.mkstemp(prefix='.dashboard-interval-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream, indent=2); stream.write('\n')
            stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)
    print(f'{sensor}: interval {previous}s -> {interval}s; stale after {max(90, 2*interval+60)}s')
    print('Reload dashboard/SVG. No service restart; archive and timestamps unchanged.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runtime', type=Path)
    parser.add_argument('--sensor', required=True)
    parser.add_argument('--interval', type=int, required=True, help='Expected sensor interval in seconds')
    args = parser.parse_args()
    if os.geteuid() == 0:parser.error('Run as the normal application user')
    spec = importlib.util.spec_from_file_location('probe', Path(__file__).with_name('probe-cgi.py'))
    probe = importlib.util.module_from_spec(spec); spec.loader.exec_module(probe)
    runtime = args.runtime.resolve(strict=True)
    probe.verify_runtime(runtime)
    configure(runtime / 'root/etc/meteohub-dashboard.json', args.sensor, args.interval)


if __name__ == '__main__':
    try:main()
    except (OSError, ValueError) as error:raise SystemExit('STOP: ' + str(error))
