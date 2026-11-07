#!/usr/bin/env python3
"""Read archive tails and display index together; never connect to the station."""
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import sqlite3
import time


def snapshot(runtime, now):
    data = runtime / 'root/data'
    month = dt.datetime.fromtimestamp(now, dt.timezone.utc).strftime('%Y%m')
    raw = data / 'weather' / month / 'raw'
    result = {'utc':dt.datetime.fromtimestamp(now, dt.timezone.utc).isoformat()}
    latest = {}
    try:
        with raw.open('rb') as stream:
            stream.seek(0, 2); size = stream.tell(); offset = max(0, size-262144)
            stream.seek(offset)
            if offset:stream.readline()
            lines = stream.read().splitlines(keepends=True)
        result['raw_bytes'] = size
        result['raw_write_age_s'] = round(now-raw.stat().st_mtime, 1)
        for line in lines:
            if not line.endswith(b'\n'):continue
            parts = line.split()
            if len(parts) < 3:continue
            try:
                stamp = dt.datetime.strptime(parts[0].decode(), '%Y%m%d%H%M%S').replace(tzinfo=dt.timezone.utc).timestamp()
                sensor = parts[1].decode()
                if re.fullmatch(r'[a-z]+[0-9]+', sensor):latest[sensor] = max(stamp, latest.get(sensor, stamp))
            except (ValueError, UnicodeError):continue
        result['raw_age_s'] = {k:round(now-v, 1) for k,v in sorted(latest.items())}
    except OSError as error:result['raw_error'] = type(error).__name__
    try:
        status = json.loads((data/'dashboard/status.json').read_text())
        result['index_run_age_s'] = round(now-status.get('last_success', 0), 1)
        result['index_error'] = status.get('error')
        result['index_last_added'] = status.get('records_added')
        dbpath = (data/'dashboard/weather.sqlite').resolve()
        with sqlite3.connect(dbpath.as_uri()+'?mode=ro', uri=True, timeout=2) as db:
            indexed = dict(db.execute('SELECT sensor, max(ts) FROM samples GROUP BY sensor'))
        result['index_age_s'] = {k:round(now-v, 1) for k,v in sorted(indexed.items())}
        result['index_behind_raw_s'] = {k:round(v-indexed[k], 1) for k,v in latest.items() if k in indexed}
    except (OSError, ValueError, sqlite3.Error) as error:result['index_error'] = type(error).__name__
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runtime', type=Path)
    parser.add_argument('--duration', type=int, default=240)
    args = parser.parse_args()
    if not 0 <= args.duration <= 1800:parser.error('duration must be 0..1800 seconds')
    print('READ ONLY: current UTC month, last 256 KiB of archive; no station connection or service changes.', flush=True)
    until = time.monotonic()+args.duration
    while True:
        print(json.dumps(snapshot(args.runtime, time.time()), sort_keys=True), flush=True)
        remaining = until-time.monotonic()
        if remaining <= 0:break
        time.sleep(min(15, remaining))


if __name__ == '__main__':main()
