#!/usr/bin/python3
"""Read the last 24 hours of native Meteohub archives; never restart services."""
import collections
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import re
import sqlite3
import statistics
import subprocess
import tempfile
import time
from zoneinfo import ZoneInfo

ROOT = Path('/home/meteohub/meteohub-staging/5.1e-runtime/root')
SENSORS = ('data0', 'rain0', 'sol0', 't1', 't2', 'thb0', 'uv0', 'wind0')
TZ = ZoneInfo('Europe/Berlin')


def stamp(t):
    return dt.datetime.fromtimestamp(t, TZ).isoformat()


def inspect_raw(payloads, start, end, config):
    records = collections.defaultdict(list)
    malformed = 0
    incomplete = 0
    future = 0
    for payload in payloads:
        for line in payload.splitlines(keepends=True):
            if not line.endswith(b'\n'):
                incomplete += 1
                continue
            parts = line.split()
            try:
                if len(parts) < 3 or not re.fullmatch(rb'\d{14}', parts[0]):
                    raise ValueError()
                t = dt.datetime.strptime(parts[0].decode(), '%Y%m%d%H%M%S').replace(tzinfo=dt.timezone.utc).timestamp()
                sensor = parts[1].decode('ascii')
                if not re.fullmatch(r'[a-z]+[0-9]+', sensor):
                    raise ValueError()
                if t > end:
                    future += 1
                else:
                    records[sensor].append((t, tuple(parts[2:])))
            except (ValueError, UnicodeError):
                malformed += 1
    result = {}
    intervals = config.get('sensor_intervals_seconds', {})
    for sensor in sorted(set(SENSORS) | set(records)):
        allrows = records[sensor]
        rows = [(t, value) for t, value in allrows if t >= start]
        unique = sorted(set(t for t, _ in rows))
        before = [t for t, _ in allrows if t < start]
        sequence = ([max(before)] if before else []) + unique
        gaps = [(a, b, b-a) for a, b in zip(sequence, sequence[1:]) if b >= start]
        internal = [b-a for a, b in zip(unique, unique[1:])]
        median = statistics.median(internal) if internal else None
        threshold = max(median * 1.5, median + 2) if median else None
        suspicious = [g for g in gaps if threshold is not None and g[2] > threshold]
        by_time = collections.defaultdict(list)
        for t, value in rows:
            by_time[t].append(value)
        duplicates = sum(len(v)-len(set(v)) for v in by_time.values())
        conflicts = sum(len(set(v)) > 1 for v in by_time.values())
        backwards = sum(b[0] < a[0] for a, b in zip(rows, rows[1:]))
        latest = max((t for t, _ in allrows), default=None)
        result[sensor] = {
            'records_24h': len(rows), 'first_in_window': stamp(unique[0]) if unique else None,
            'last': stamp(latest) if latest else None,
            'age_seconds': round(end-latest, 1) if latest else None,
            'dashboard_interval_seconds': intervals.get(sensor, 60),
            'observed_median_seconds': median, 'max_gap_seconds': max((g[2] for g in gaps), default=None),
            'common_intervals': collections.Counter(internal).most_common(4),
            'identical_duplicates': duplicates, 'conflicting_timestamps': conflicts,
            'backward_timestamps': backwards, 'start_boundary_covered': bool(before),
            'gaps_over_observed_cadence': len(suspicious),
            'gap_list': [{'from': stamp(a), 'to': stamp(b), 'seconds': seconds}
                         for a, b, seconds in suspicious],
        }
    return {'sensors': result, 'malformed_lines_in_scanned_files': malformed,
            'unfinished_lines': incomplete, 'future_records': future,
            'note': 'Gap threshold: >1.5x observed median (at least +2s). Dashboard intervals are display settings, not proof of source cadence. Boundary gaps may start before the window. Current age is reported separately; no exact missing-slot count is claimed.'}


def run(*args):
    p = subprocess.run(args, text=True, capture_output=True, timeout=60)
    if p.returncode:
        raise RuntimeError(' '.join(args[:2]) + ': ' + p.stderr.strip())
    return p.stdout


def main():
    if os.geteuid() != 0:
        raise ValueError('Bitte als root ausfuehren.')
    os.umask(0o077)
    end = time.time()
    start = end - 86400
    report = {'from': stamp(start), 'to': stamp(end)}
    # Prevent a concurrent checkpoint/rebase while taking the file snapshots.
    with open('/run/lock/meteohub-storage.lock', 'rb') as lock:
        fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
        cfg = json.loads((ROOT / 'etc/meteohub-dashboard.json').read_text())
        months = sorted({dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime('%Y%m')
                         for t in (start-86400, start, end)})
        payloads = []
        report['archive_files'] = []
        for month in months:
            path = ROOT / 'data/weather' / month / 'raw'
            if path.exists():
                with path.open('rb') as stream:
                    size = os.fstat(stream.fileno()).st_size
                    payloads.append(stream.read(size))
                report['archive_files'].append({'month': month, 'bytes': size})
        report['ram'] = json.loads(run('python3', '/usr/local/libexec/meteohub-ram.py', 'status'))
        report['index_status'] = json.loads((ROOT / 'data/dashboard/status.json').read_text())
        with sqlite3.connect((ROOT / 'data/dashboard/weather.sqlite').as_uri()+'?mode=ro', uri=True) as db:
            report['index_latest'] = {s: stamp(t) for s, t in db.execute('SELECT sensor,max(ts) FROM samples GROUP BY sensor')}
            report['index_positions'] = []
            for path, inode, offset in db.execute('SELECT path,inode,offset FROM positions'):
                source = ROOT / path.lstrip('/')
                st = source.stat()
                report['index_positions'].append({'path': path, 'offset': offset, 'size': st.st_size,
                                                  'inode_matches': inode == st.st_ino})
        logpath = ROOT / 'data/log/meteohub.log'
        log = logpath.read_text(errors='replace') if logpath.exists() else ''
    report['archive'] = inspect_raw(payloads, start, end, cfg)
    logrows = []
    for line in log.splitlines():
        match = re.search(r'\((\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2})\)', line)
        if match:
            t = dt.datetime.strptime(match[1], '%d.%m.%Y %H:%M:%S').replace(tzinfo=TZ).timestamp()
            if start <= t <= end:
                logrows.append(line)
    report['native_log_window'] = logrows
    report['native_log_note'] = 'Current log file only; rotated/missing earlier logs cannot be reconstructed here.'
    report['mounts'] = json.loads(run('findmnt', '-J', '-o', 'TARGET,SOURCE,FSTYPE,OPTIONS'))
    report['failed_units'] = run('systemctl', '--failed', '--no-pager', '--plain')
    report['timers'] = run('systemctl', 'list-timers', '--all', '--no-pager', '--full', 'meteohub-ram-*')
    report['time'] = run('timedatectl', 'show', '-p', 'NTPSynchronized')
    report['memory'] = run('free', '-h')
    report['journal'] = run('journalctl', '--since', '@'+str(int(start)), '--until', '@'+str(int(end)),
                            '--no-pager', '-o', 'short-iso', '-u', 'meteohub-ram-checkpoint.service',
                            '-u', 'meteohub-live-logger.service', '-u', 'meteohub-ram-check.service')
    report['kernel_warnings'] = run('journalctl', '-k', '--since', '@'+str(int(start)),
                                    '--until', '@'+str(int(end)), '-p', 'warning', '--no-pager')
    folder = Path(tempfile.mkdtemp(prefix='meteohub-day-audit-', dir='/root'))
    (folder / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    print('Zeitraum:', report['from'], 'bis', report['to'])
    print('Vollstaendiger lokaler Bericht:', folder / 'report.json')
    for sensor, values in report['archive']['sensors'].items():
        summary = dict(values)
        summary['gap_list'] = sorted(values['gap_list'], key=lambda g:g['seconds'], reverse=True)[:5]
        print(sensor, json.dumps(summary, ensure_ascii=False))
    print('Archivformat:', json.dumps({k:v for k,v in report['archive'].items() if k != 'sensors'}))
    print('Index:', json.dumps(report['index_positions']))
    print('Indexstatus:', json.dumps(report['index_status']))
    print('Native Logereignisse im Fenster:', len(logrows))
    anomalies = [s for s in logrows if re.search(r'timeout|no signal|no synchronization|unexpected|without data|error', s, re.I)]
    print('Native Auffaelligkeiten:', len(anomalies))
    print('\n'.join(anomalies[-12:]))
    print('RAM:', json.dumps(report['ram']))
    print(report['failed_units'], report['timers'], report['kernel_warnings'])
    print('Nur gelesen und Bericht gespeichert. Keine Dienste, Mounts oder Bootparameter geaendert.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, sqlite3.Error, subprocess.TimeoutExpired) as error:
        raise SystemExit('STOP: '+str(error))
