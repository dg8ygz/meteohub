#!/usr/bin/python3
"""Optional bounded freezer checkpoint; the original shutdown/rebase stays intact.

Runs only as root. Copies the quiescent on-filesystem state (including SQLite
WAL); does not flush userspace logger buffers or claim to persist them. A saved
reference may legitimately differ from the still-mounted active reference.
"""
import argparse
import contextlib
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import time

BASE = Path('/usr/local/libexec/meteohub-ram.py')
CONFIG = Path('/etc/meteohub-ram.json')
MARKER = Path('/run/meteohub-quiet-checkpoint.json')
WATCHDOG = 'meteohub-checkpoint-thaw.timer'
MAX_SECONDS = 25


def load_base(path=None):
    path = path or BASE
    spec = importlib.util.spec_from_file_location('ram_base', path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def ctl(*args):
    return subprocess.check_output(['systemctl', *args], text=True, timeout=12).strip()


def state(unit):
    return dict(s.split('=', 1) for s in ctl('show', unit, '--no-pager', '-p',
                'ActiveState,MainPID,FreezerState').splitlines() if '=' in s)


def boot_id():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def marker_read():
    if not MARKER.exists(): return None
    st = MARKER.lstat()
    if MARKER.is_symlink() or st.st_uid != 0 or st.st_mode & 0o077:
        raise ValueError('Unsafe freeze marker')
    data = json.loads(MARKER.read_text())
    if data['boot_id'] != boot_id(): raise ValueError('Foreign boot freeze marker')
    for unit in data['units']:
        if not unit.startswith('meteohub-') or not unit.endswith('.service') or '/' in unit:
            raise ValueError('Invalid freeze unit')
    return data


@contextlib.contextmanager
def marker_lock():
    fd = os.open(str(MARKER)+'.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally: os.close(fd)


def thaw(abort=True, cleanup=False):
    with marker_lock():
        _thaw(abort, cleanup)


def _thaw(abort, cleanup):
    data = marker_read()
    if data is None: return
    # Leave an abort flag for the publisher. A late callback can never bless a
    # snapshot after the independent timer has resumed the writers.
    if abort:
        data['aborted'] = True
        load_base().save(MARKER, data)
    failures = []
    for unit in reversed(data['units']):
        try: ctl('thaw', unit)
        except (subprocess.SubprocessError, OSError) as e: failures.append(str(e))
    if failures: raise RuntimeError('Thaw failed: ' + '; '.join(failures))
    if cleanup: MARKER.unlink(missing_ok=True)


class Quiet:
    def __init__(self, base, storage):
        self.base, self.s = base, storage

    def validate(self, before):
        data = marker_read()
        if not data or data.get('aborted') or time.monotonic()-data['started'] >= MAX_SECONDS:
            raise RuntimeError('Freeze deadline expired; snapshot not published')
        for name, old in before.items():
            now = state(name)
            if (now.get('ActiveState') != 'active' or now.get('FreezerState') != 'frozen'
                    or now.get('MainPID') != old['MainPID']):
                raise RuntimeError('Writer changed or thawed: ' + name)

    @contextlib.contextmanager
    def frozen(self):
        if MARKER.exists(): raise ValueError('Previous freeze marker requires inspection/cleanup')
        names = [n for n in self.s.apps if n.endswith('.service')]
        before = {n: state(n) for n in names}
        if any(s.get('ActiveState') != 'active' or s.get('FreezerState') != 'running'
               or int(s.get('MainPID', '0')) <= 1 for s in before.values()):
            raise ValueError('All writers must be active and unfrozen')
        data = dict(boot_id=boot_id(), started=time.monotonic(), units=[], aborted=False)
        self.base.save(MARKER, data)
        try:
            ctl('restart', WATCHDOG)
            for name in names:
                # Register before freeze so a crash in systemctl still has cleanup.
                with marker_lock():
                    data = marker_read()
                    if data.get('aborted') or time.monotonic()-data['started'] >= MAX_SECONDS:
                        raise RuntimeError('Freeze deadline expired')
                    data['units'].append(name); self.base.save(MARKER, data)
                    ctl('freeze', name)
            self.validate(before)
            yield before
        finally:
            # Do not delete the marker unless every thaw succeeded.
            thaw(abort=False)
            ctl('stop', WATCHDOG)
            MARKER.unlink(missing_ok=True)

    def checkpoint(self):
        s, b = self.s, self.base
        # Rebase only under memory pressure. The original helper takes its own
        # lock; call that path after releasing our preliminary lock.
        with s.lock():
            s.live_state()
            if any(s.active(n) != 'active' for n in s.apps):
                raise ValueError('All applications must be active')
            v = os.statvfs(s.ram)
            pressure = (v.f_blocks-v.f_bfree) >= v.f_blocks * .60
            if not pressure:
                existing = set(s.generations.iterdir())
                with self.frozen() as before:
                    original_save = b.save
                    def guarded_save(path, data):
                        if Path(path) == s.current:
                            with marker_lock():
                                self.validate(before)
                                return original_save(path, data)
                        return original_save(path, data)
                    b.save = guarded_save
                    try:
                        ref = s.capture()
                        self.validate(before)
                    except BaseException:
                        # The storage lock excludes concurrent checkpoints. Only
                        # remove pending copies created by this attempt, never refs.
                        with s.writable():
                            for path in set(s.generations.iterdir()) - existing:
                                if path.name.startswith('.pending-') and path.is_dir() and not path.is_symlink():
                                    shutil.rmtree(path)
                        raise
                    finally: b.save = original_save
                # The lower currently used by the running logger is retained.
                s.prune()
                after = {n: state(n) for n in before}
                if any(after[n]['MainPID'] != before[n]['MainPID']
                       or after[n].get('FreezerState') != 'running' for n in before):
                    raise RuntimeError('Post-checkpoint writer/PID verification failed')
                return {'saved': ref, 'mode': 'freeze', 'logger_pid_unchanged': True,
                        'userspace_buffers_flushed': False}
        print('RAM >=60%: using original stop/copy/rebase with reconnect.', flush=True)
        return {'saved': s.checkpoint(), 'mode': 'stop-rebase-memory-pressure'}


def main():
    global BASE, CONFIG, MARKER, WATCHDOG
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=BASE)
    parser.add_argument('--config', type=Path, default=CONFIG)
    parser.add_argument('--marker', type=Path, default=MARKER)
    parser.add_argument('--watchdog', default=WATCHDOG)
    parser.add_argument('action', choices=['checkpoint', 'thaw', 'cleanup'])
    args = parser.parse_args()
    if os.geteuid() != 0: parser.error('root required')
    os.umask(0o077)
    BASE, CONFIG, MARKER, WATCHDOG = args.base, args.config, args.marker, args.watchdog
    if args.action in ('thaw', 'cleanup'): thaw(cleanup=args.action == 'cleanup'); return
    base = load_base()
    cfg = base.regular_json(CONFIG)
    print(json.dumps(Quiet(base, base.Storage(cfg)).checkpoint()), flush=True)


if __name__ == '__main__':
    def interrupted(signum, frame): raise InterruptedError('Checkpoint interrupted')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try: main()
    except Exception as error:
        print('STOP:', error, file=sys.stderr); sys.exit(1)
