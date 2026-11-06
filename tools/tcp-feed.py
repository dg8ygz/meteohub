#!/usr/bin/env python3
"""Receive the existing Meteohub plugin-copy TCP stream; never send commands."""
import argparse
from collections import Counter, deque
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import signal
import socket
import stat
import sys
import tempfile
import time

ARITY = {'data': 1, 't': 1, 'uv': 1, 'sol': 2, 'wind': 3,
         'rain': 2, 'th': 2, 'thb': 4}


def validate(raw):
    line = raw.decode('ascii').strip()
    parts = line.split()
    if not parts:
        raise ValueError('empty record')
    match = re.fullmatch(r'(data|t|uv|sol|wind|rain|th|thb)[0-9]{1,4}', parts[0])
    if not match or len(parts) != ARITY[match.group(1)] + 1:
        raise ValueError('sensor or field count')
    if any(not re.fullmatch(r'-?[0-9]{1,10}', p) or not -2147483648 <= int(p) <= 2147483647
           for p in parts[1:]):
        raise ValueError('integer format/range')
    return ' '.join(parts)


class Framer:
    def __init__(self):
        self.pending = b''
        self.discard = False
        self.rejected = 0

    def feed(self, data):
        result = []
        pieces = data.split(b'\n')
        for index, piece in enumerate(pieces):
            ended = index < len(pieces) - 1
            if not self.discard:
                if len(self.pending) + len(piece) > 512:
                    self.pending = b''
                    self.discard = True
                    self.rejected += 1
                else:
                    self.pending += piece
            if ended:
                if not self.discard:
                    try:
                        result.append(validate(self.pending))
                    except (ValueError, UnicodeError):
                        self.rejected += 1
                self.pending = b''
                self.discard = False
        return result


def atomic_json(path, value):
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def collect(host, port, output, duration=0, retry=5, idle=60):
    records = deque(maxlen=300)
    summary = {'records': 0, 'bytes': 0, 'connections': 0,
               'rejected': 0, 'partial_disconnects': 0, 'evicted': 0}
    sensors = Counter()
    latest = {}
    source_at = 0
    stop = False
    start = time.monotonic()
    deadline = start + duration if duration else float('inf')

    def halt(*unused):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, halt)
    signal.signal(signal.SIGINT, halt)

    def snapshot():
        atomic_json(output, {
            'source_read_at': source_at, 'source_format': 'plugin',
            'timestamp_basis': 'receiver_utc; source TCP lines have no timestamps',
            'source': {'host': host, 'port': port}, 'lines': list(records),
        })

    snapshot()  # A previous file is never replayed after collector restart.
    while not stop and time.monotonic() < deadline:
        frame = Framer()
        last_byte = time.monotonic()
        try:
            timeout = max(0.05, min(5, deadline - time.monotonic()))
            with socket.create_connection((host, port), timeout=timeout) as sock:
                sock.settimeout(0.5)
                summary['connections'] += 1
                print('CONNECTED: receive only', flush=True)
                while not stop and time.monotonic() < deadline:
                    try:
                        chunk = sock.recv(4096)
                    except socket.timeout:
                        if time.monotonic() - last_byte >= idle:
                            raise TimeoutError('no bytes within idle limit')
                        continue
                    if not chunk:
                        raise ConnectionError('source closed connection')
                    last_byte = time.monotonic()
                    summary['bytes'] += len(chunk)
                    lines = frame.feed(chunk)
                    if not lines:
                        continue
                    source_at = time.time()
                    stamp = datetime.fromtimestamp(source_at, timezone.utc).strftime('%Y%m%d%H%M%S')
                    for line in lines:
                        if len(records) == records.maxlen:
                            summary['evicted'] += 1
                        records.append(stamp + ' ' + line)
                        name = line.split()[0]
                        sensors[name] += 1
                        latest[name] = line
                        summary['records'] += 1
                    snapshot()
        except OSError as error:
            print('TCP unavailable: ' + str(error), file=sys.stderr, flush=True)
        finally:
            summary['rejected'] += frame.rejected
            if frame.pending or frame.discard:
                summary['partial_disconnects'] += 1
        retry_until = min(deadline, time.monotonic() + retry)
        while not stop and time.monotonic() < retry_until:
            time.sleep(max(0, min(0.1, retry_until - time.monotonic())))
    summary.update(elapsed_seconds=round(time.monotonic() - start, 2),
                   sensors=dict(sensors), latest=latest, last_received_at=source_at)
    atomic_json(output.with_suffix('.status.json'), summary)
    print(json.dumps(summary, indent=2), flush=True)
    print('FEED:', output, flush=True)
    print('Receipt timestamps only; no native logger/archive verification.', flush=True)
    return 0 if summary['records'] else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True)
    parser.add_argument('--port', type=int, default=5500)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--duration', type=float, default=90,
                        help='Seconds to receive; 0 runs until SIGINT/SIGTERM (default: 90)')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535 or not 0 <= args.duration <= 86400:
        parser.error('Invalid port or duration')
    os.umask(0o077)
    output = args.output.absolute()
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    for path in (output, output.with_suffix('.status.json')):
        if path.is_symlink() or (path.exists() and
            (not stat.S_ISREG(path.stat().st_mode) or path.stat().st_uid != os.getuid())):
            parser.error('Output must be an owned regular file, not a link')
    return collect(args.host, args.port, output, args.duration)


if __name__ == '__main__':
    sys.exit(main())
