#!/usr/bin/env python3
"""Install the read-only TCP snapshot plugin into an existing PRIVATE test root.

Does not connect to the source, launch loggerd or change host services.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path

WRAPPER = '''#!/bin/sh
set -eu
exec /usr/bin/python3 /home/meteohub/live_feed_plugin.py /data/tcp-feed/feed.json /data/tcp-feed/state
'''


def probe_tool():
    spec = importlib.util.spec_from_file_location('probe', Path(__file__).with_name('probe-cgi.py'))
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    return tool


def check_config(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 262144:
        raise ValueError('Generate a private regular logger.conf first')
    entries = [line.split() for line in path.read_text().splitlines() if line.split()]
    stations = [p for p in entries if p[0] == '@WEATHERSTATION']
    if len(stations) != 1 or stations[0][:5] != ['@WEATHERSTATION', '0', '9', '5', '/home/meteohub/plugin.sh']:
        raise ValueError('Expected exactly station 0, connection Plug-in, path /home/meteohub/plugin.sh; no changes made')
    for key, value in (('@DATAPATH', '/data/weather/'), ('@ERRORLOG', '/data/log/meteohub.log')):
        if [p for p in entries if p[0] == key] != [[key, value]]:
            raise ValueError('Unexpected private data/log path; no changes made')


def verify_prepared(runtime):
    probe_tool().verify_runtime(runtime)
    check_config(runtime/'root/home/meteohub/logger.conf')
    manifest = runtime/'tcp-plugin-prepared.json'
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError('Prepare the private TCP plugin first')
    record = json.loads(manifest.read_text())
    expected = {
        'root/home/meteohub/plugin.sh': WRAPPER.encode(),
        'root/home/meteohub/live_feed_plugin.py':
            (Path(__file__).resolve().parent.parent/'live_feed_plugin.py').read_bytes(),
    }
    if record.get('schema') != 1 or set(record.get('files', {})) != set(expected):
        raise ValueError('Unexpected plugin preparation manifest')
    for name, data in expected.items():
        path = runtime/name
        if path.is_symlink() or not path.is_file() or path.read_bytes() != data:
            raise ValueError('Installed private plugin differs from reviewed source')
        if hashlib.sha256(data).hexdigest() != record['files'][name]:
            raise ValueError('Prepared plugin hash mismatch')
    for name in ('root/data/tcp-feed', 'root/data/tcp-feed/state'):
        path = runtime/name
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise ValueError('Unexpected feed/state path')
    for name in ('feed.json', 'state/cursor.json', 'state/provenance.jsonl'):
        path = runtime/'root/data/tcp-feed'/name
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError('Unexpected feed/state file')


def prepare(runtime):
    runtime = runtime.resolve(strict=True)
    probe_tool().verify_runtime(runtime)
    home = runtime/'root/home/meteohub'
    check_config(home/'logger.conf')
    plugin = Path(__file__).resolve().parent.parent/'live_feed_plugin.py'
    code = plugin.read_bytes()
    files = {home/'plugin.sh': WRAPPER.encode(), home/'live_feed_plugin.py': code}
    feed = runtime/'root/data/tcp-feed'
    manifest = runtime/'tcp-plugin-prepared.json'
    for path in [*files, feed, manifest]:
        if path.exists() or path.is_symlink():
            raise ValueError('Preparation target already exists; leave existing data intact: ' + str(path))
    os.umask(0o077)
    created = []
    try:
        for path, content in files.items():
            with path.open('xb') as stream:
                created.append(path)
                stream.write(content)
            path.chmod(0o700)
        feed.mkdir(mode=0o700);created.append(feed)
        with manifest.open('x') as stream:
            created.append(manifest)
            json.dump({'schema': 1, 'status': 'prepared only; collector and logger not started',
                'plugin_sha256': hashlib.sha256(code).hexdigest(),
                'feed_path': '/data/tcp-feed/feed.json',
                'host_feed_path': str(feed/'feed.json'),
                'pressure_policy': 'THB pressure in private provenance only; no THB temperature/humidity sent to native logger',
                'files': {str(p.relative_to(runtime)): hashlib.sha256(data).hexdigest() for p, data in files.items()},
            }, stream, indent=2)
            stream.write('\n')
    except Exception:
        for path in reversed(created):
            if path.is_dir(): path.rmdir()
            else: path.unlink()
        raise
    print('PREPARED: private plugin /home/meteohub/plugin.sh')
    print('HOST_FEED:', feed/'feed.json')
    print('PRESSURE: THB pressure retained separately; THB temperature/humidity excluded')
    print('No TCP connection, native logger or service started. Missing feed is expected until collector start.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runtime', type=Path)
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error('Run as the normal login user, without sudo')
    try:
        prepare(args.runtime)
    except (OSError, ValueError) as error:
        parser.exit(1, 'STOP: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
