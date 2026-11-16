#!/usr/bin/python3
"""Run original Meteohub 5.1e aggregation; preserve queued requests on failure.

The containing service MUST participate in RAM stop/freeze checkpoints.
No station connection, raw archive editing or invented measurements.
"""
import datetime
import fcntl
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import time

HOME = Path('/home/meteohub')
WEATHER = Path('/data/weather')
BINARY = '/opt/meteohub-native-eval/wmr928eval'
SPANS = ('min5', 'min10', 'min30', 'hour1', 'hour6', 'day1', 'month1')
HISTORY = [('day1', '-100000', '-H'), ('hour1', '-7200', '-H'),
           ('last24h', '-86400', '-H'), ('last60m', '-3600', '-H'),
           ('last15m', '-900', '-H'), ('min15', '-84610', '-S'),
           ('min1', '-3720', '-S'), ('hour1', '-93600', '-S'),
           ('month1', '-3500000', '-H'), ('day1', '-3500000', '-S'),
           ('hour6', '-648000', '-S'), ('alltime', '19900101000000', '-H'),
           ('month1', '-34560000', '-S')]


def atomic(path, value):
    tmp = path.with_name(path.name + '.new')
    tmp.write_text(value)
    os.replace(tmp, path)


def evaluate(span, config, *args):
    subprocess.run([BINARY, '-c', span, '-w', str(WEATHER)+'/',
                    '-s', str(config), *args], check=True, timeout=120)


def history(config):
    for span, start, kind in HISTORY:
        evaluate(span, config, '-t', start, kind)
    evaluate('year1', config, '-t', datetime.datetime.now(datetime.timezone.utc).strftime('%Y')+'0101000000', '-H')


def full():
    request = HOME/'wmr928fulleval.conf'
    active = HOME/'wmr928fulleval.do.conf'
    stage = HOME/'wmr928fulleval.stage'
    if not active.exists():
        if not request.exists():
            return
        os.replace(request, active)
    try:
        atomic(stage, '1')
        evaluate('min1', active, '-n', '-x', '-t', '-2592000',
                 '-e', str(HOME/'wswin.conf'), '-E', str(HOME/'wd.conf'))
        for number, span in enumerate(SPANS, 2):
            atomic(stage, str(number))
            evaluate(span, active, '-n')
        atomic(stage, '9')
        history(active)
        # A successful process must actually have produced aggregate records.
        if not any(p.stat().st_size for p in WEATHER.glob('*-min5')):
            raise RuntimeError('No nonempty min5 aggregates; request remains pending')
        active.unlink()
        stage.unlink(missing_ok=True)
        print(json.dumps({'full_recomputation': 'completed', 'time': time.time()}), flush=True)
    except BaseException:
        # Do not overwrite a newer request submitted during this computation.
        if not request.exists() and active.exists():
            os.replace(active, request)
        stage.unlink(missing_ok=True)
        raise


def run_full():
    # Kill the whole wrapper/worker/native-program group on timeout, so a late
    # child cannot race a retry. systemd also owns all of them in one cgroup.
    command = ['/opt/meteohub-native-eval/wmr928fulleval']
    process = subprocess.Popen(command, start_new_session=True)
    try:
        code = process.wait(timeout=600)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        raise
    if code:
        raise subprocess.CalledProcessError(code, command)


def daemon():
    config = HOME/'wmr928eval.conf'
    # Rebuild derived files after a restart; a frozen snapshot may contain
    # userspace-buffered aggregate tails. Raw input is always the authority.
    if not any((HOME/name).exists() for name in
               ('wmr928fulleval.conf', 'wmr928fulleval.do.conf')):
        atomic(HOME/'wmr928fulleval.conf', config.read_text())
    with open('/run/native-eval.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        last_batch = 0.0
        while True:
            try:
                if any((HOME/name).exists() for name in
                       ('wmr928fulleval.conf', 'wmr928fulleval.do.conf')):
                    run_full()
                    last_batch = time.monotonic()
                evaluate('min1', config, '-t', '-3720', '-S')
                if time.monotonic()-last_batch >= 300:
                    for span in SPANS:
                        evaluate(span, config)
                    history(config)
                    last_batch = time.monotonic()
                atomic(Path('/data/native-eval-status.json'), json.dumps({
                    'last_success': time.time(), 'error': None}))
            except Exception as error:
                atomic(Path('/data/native-eval-status.json'), json.dumps({
                    'failed_at': time.time(), 'error': str(error)}))
                print('Native evaluation failed: '+str(error), flush=True)
            time.sleep(60)


if __name__ == '__main__':
    if sys.argv[1:] == ['full']:
        full()
    elif sys.argv[1:] == ['daemon']:
        daemon()
    else:
        raise SystemExit('usage: native-eval.py full|daemon')
