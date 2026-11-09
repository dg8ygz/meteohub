#!/usr/bin/python3
"""Bounded RAM overlay for a private Meteohub runtime, with verified SD generations.

Host root/boot are not changed by this tool. Requires root and a separate ext4
partition mounted read-only. All target paths belong to the local installation.
"""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
import uuid

DEFAULT_CONFIG = '/etc/meteohub-ram.json'
APPS = ['meteohub-web-test.socket', 'meteohub-web-test.service',
        'meteohub-live-logger.service', 'meteohub-dashboard-index.service']
TARGET = 'meteohub-live.target'
PREFIX = 'meteohub-ram'
HELPER = Path('/usr/local/libexec/meteohub-ram.py')
RAM_ROOT = '/run/meteohub-ram'
STORAGE_LOCK = '/run/lock/meteohub-storage.lock'
UNIT_DIR = Path('/etc/systemd/system')
TIME_WAIT = 'systemd-time-wait-sync.service'


def run(*args, check=True):
    r = subprocess.run([str(a) for a in args], text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    if check and r.returncode:
        raise RuntimeError('Command failed: ' + str(args[0]) + ': ' + r.stderr.strip())
    return r


def atomic(path, data):
    path = Path(path)
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(data); out.flush(); os.fsync(out.fileno())
        os.replace(name, path)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
    finally:
        Path(name).unlink(missing_ok=True)


def save(path, value):
    atomic(path, (json.dumps(value, sort_keys=True, indent=2) + '\n').encode())


def safe_path(value):
    if not re.fullmatch(r'/[A-Za-z0-9_./+-]+', value) or '..' in Path(value).parts:
        raise ValueError('Unsupported path: ' + value)
    path = Path(value)
    if str(path) != value or path == Path('/') or path.resolve() != path:
        raise ValueError('Linked or noncanonical path: ' + value)
    return path


def mount_info(path):
    r = run('findmnt', '-J', '-M', path, '-o', 'TARGET,SOURCE,FSTYPE,UUID,OPTIONS', check=False)
    if r.returncode == 1: return None
    if r.returncode: raise RuntimeError(r.stderr)
    rows = json.loads(r.stdout)['filesystems']
    if len(rows) != 1 or rows[0]['target'] != str(path):
        raise ValueError('Ambiguous mount')
    return rows[0]


def regular_json(path):
    info = Path(path).lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > 16 * 1024 * 1024:
        raise ValueError('Unexpected JSON file: ' + str(path))
    return json.loads(Path(path).read_text())


def fingerprint(tree):
    """Hash ordinary files; preserve link text, ownership and permissions, never follow links."""
    tree = Path(tree)
    result = {}
    def visit(path):
        info = path.lstat()
        entry = {'mode': stat.S_IMODE(info.st_mode), 'uid': info.st_uid, 'gid': info.st_gid}
        key = str(path.relative_to(tree))
        if stat.S_ISLNK(info.st_mode):
            entry.update(kind='link', target=os.readlink(path))
        elif stat.S_ISDIR(info.st_mode):
            entry.update(kind='directory')
            result[key] = entry
            for child in sorted(path.iterdir()): visit(child)
            return
        elif stat.S_ISREG(info.st_mode):
            h = hashlib.sha256()
            with path.open('rb') as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b''): h.update(chunk)
            entry.update(kind='file', size=info.st_size, sha256=h.hexdigest())
        else:
            raise ValueError('Special file refused: ' + str(path))
        result[key] = entry
    visit(tree)
    return result


def check_sqlite(path, normalize=False):
    if path.is_symlink() or not path.is_file(): raise ValueError('Missing regular dashboard database')
    uri = str(path) if normalize else path.as_uri() + '?mode=ro&immutable=1'
    with contextlib.closing(sqlite3.connect(uri, uri=not normalize)) as db:
        if normalize:
            result = db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()
            if result[0] != 0: raise ValueError('SQLite checkpoint busy')
            if db.execute('PRAGMA journal_mode=DELETE').fetchone()[0] != 'delete':
                raise ValueError('SQLite consolidation failed')
        if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise ValueError('SQLite integrity check failed')


class Storage:
    def __init__(self, cfg):
        self.cfg = cfg
        self.runtime = safe_path(cfg['runtime'])
        self.persist = safe_path(cfg['persist'])
        self.ram = safe_path(cfg['ram'])
        # Outside the bounded upper tmpfs so even a full data buffer can be rebased.
        self.statefile = self.ram.parent / (self.ram.name + '.state.json')
        self.generations = self.persist / 'ram-generations'
        self.current = self.persist / 'ram-current.json'
        self.previous = self.persist / 'ram-previous.json'
        self.apps = cfg['apps']
        self.logger = self.apps[2]
        if len(self.apps) != 4 or any(not re.fullmatch(r'[A-Za-z0-9_.-]+\.(service|socket)', n) for n in self.apps):
            raise ValueError('Invalid application units')
        if not 64 <= cfg['ram_mib'] <= 384: raise ValueError('RAM limit outside 64..384 MiB')
        for a, b in ((self.runtime, self.persist), (self.runtime, self.ram), (self.persist, self.ram)):
            if a == b or a in b.parents or b in a.parents: raise ValueError('Paths overlap')

    def disk(self, ro=True):
        m = mount_info(self.persist)
        if not m or m['uuid'] != self.cfg['uuid'] or m['fstype'] != 'ext4':
            raise ValueError('Persistence filesystem missing or wrong UUID/type')
        if ro and 'ro' not in m['options'].split(','): raise ValueError('Persistence mount unexpectedly writable')

    @contextlib.contextmanager
    def writable(self):
        self.disk()
        run('mount', '-o', 'remount,rw', self.persist)
        try: yield
        finally:
            try: run('sync', '-f', self.persist)
            finally: run('mount', '-o', 'remount,ro', self.persist)

    @contextlib.contextmanager
    def lock(self):
        with open(self.cfg['lock'], 'a') as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield

    def active(self, name):
        return run('systemctl', 'show', name, '-p', 'ActiveState', '--value').stdout.strip()

    @contextlib.contextmanager
    def paused(self, restart=True):
        states = {n: self.active(n) for n in self.apps}
        if restart and any(s != 'active' for s in states.values()):
            raise ValueError('All four application units must be active before checkpoint')
        if not restart and any(s not in ('inactive', 'failed') for s in states.values()):
            raise ValueError('Shutdown checkpoint requires applications already stopped')
        try:
            if restart: run('systemctl', 'stop', *self.apps)
            if any(self.active(n) not in ('inactive', 'failed') for n in self.apps):
                raise ValueError('Application still running')
            if run('systemctl', 'show', self.logger, '-p', 'Result', '--value').stdout.strip() != 'success':
                raise ValueError('Logger did not stop cleanly; refusing to seal snapshot')
            # Release this descriptor before restarting applications or rebasing their lock file.
            with open(self.runtime / '.feed-consumer.lock', 'a') as f:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                yield f
        finally:
            if restart and run('systemctl', 'is-system-running', check=False).stdout.strip() != 'stopping':
                run('systemctl', 'start', *[n for n, s in states.items() if s == 'active'])

    def reference(self, file=None):
        ref = regular_json(file or self.current)
        if set(ref) != {'name', 'digest'} or not re.fullmatch(r'gen-[0-9a-f]{32}', ref['name']):
            raise ValueError('Invalid generation reference')
        if not re.fullmatch(r'[0-9a-f]{64}', ref['digest']): raise ValueError('Invalid manifest digest')
        return ref

    def verify(self, ref):
        base = self.generations / ref['name']
        safe_path(str(base))
        data = (base / 'manifest.json').read_bytes()
        if hashlib.sha256(data).hexdigest() != ref['digest']: raise ValueError('Manifest digest mismatch')
        manifest = json.loads(data)
        if manifest['runtime'] != str(self.runtime) or manifest['uuid'] != self.cfg['uuid']:
            raise ValueError('Snapshot belongs to a different runtime/filesystem')
        if fingerprint(base / 'tree') != manifest['files']: raise ValueError('Snapshot contents changed')
        check_sqlite(base / 'tree/root/data/dashboard/weather.sqlite')
        return base / 'tree'

    def capture(self):
        """Caller holds service pause/lock; publish only after copy, normalization and verification."""
        self.disk()
        source = fingerprint(self.runtime)
        size = sum(e.get('size', 0) for e in source.values())
        st = os.statvfs(self.persist)
        if st.f_bavail * st.f_frsize < size + 64 * 1024 * 1024:
            raise ValueError('Insufficient persistence space; no existing generation removed')
        with self.writable():
            if self.generations.is_symlink(): raise ValueError('Linked generation directory')
            self.generations.mkdir(mode=0o700, exist_ok=True)
            pending = Path(tempfile.mkdtemp(prefix='.pending-', dir=self.generations))
            tree = pending / 'tree'; tree.mkdir()
            run('cp', '-a', '--', str(self.runtime) + '/.', tree)
            if fingerprint(tree) != source or fingerprint(self.runtime) != source:
                raise ValueError('Runtime changed while paused, or copy differs')
            check_sqlite(tree / 'root/data/dashboard/weather.sqlite', normalize=True)
            manifest = {'schema': 1, 'runtime': str(self.runtime), 'uuid': self.cfg['uuid'],
                        'created': time.time(), 'files': fingerprint(tree)}
            save(pending / 'manifest.json', manifest)
            ref = {'name': 'gen-' + uuid.uuid4().hex,
                   'digest': hashlib.sha256((pending / 'manifest.json').read_bytes()).hexdigest()}
            os.rename(pending, self.generations / ref['name'])
            run('sync', '-f', self.persist)
            self.verify(ref)
            if self.current.exists(): save(self.previous, self.reference())
            save(self.current, ref)
            run('sync', '-f', self.persist)
        return ref

    def overlay(self, ref, upper, work):
        lower = self.generations / ref['name'] / 'tree'
        run('mount', '-t', 'overlay', '-o',
            f'lowerdir={lower},upperdir={upper},workdir={work},index=off,redirect_dir=off,nodev,nosuid',
            'meteohub-ram', self.runtime)

    def live_state(self):
        self.disk()
        m = mount_info(self.runtime)
        r = mount_info(self.ram)
        if not m or m['fstype'] != 'overlay' or m['source'] != 'meteohub-ram' or not r or r['fstype'] != 'tmpfs':
            raise ValueError('Expected RAM overlay is not mounted')
        state = regular_json(self.statefile)
        for key in ('upper', 'work'):
            path = safe_path(state[key])
            if path.parent != self.ram: raise ValueError('RAM state path outside private mount')
        options = m['options'].split(',')
        lower = str(self.generations / state['ref']['name'] / 'tree')
        if any(value not in options for value in ('lowerdir=' + lower, 'upperdir=' + state['upper'], 'workdir=' + state['work'])):
            raise ValueError('Overlay options do not match recorded state')
        return state

    def restore(self):
        self.disk()
        if mount_info(self.runtime):
            self.live_state(); return
        if mount_info(self.ram): raise ValueError('Unexpected RAM mount without runtime overlay')
        ref = self.reference(); self.verify(ref)
        if self.ram.is_symlink(): raise ValueError('Linked RAM directory')
        self.ram.mkdir(mode=0o700, exist_ok=True)
        if any(self.ram.iterdir()): raise ValueError('RAM mount point is not empty')
        run('mount', '-t', 'tmpfs', '-o', f'size={self.cfg["ram_mib"]}M,mode=0700,nosuid,nodev', 'meteohub-ram', self.ram)
        try:
            upper = self.ram / 'upper'; work = self.ram / 'work'
            upper.mkdir(); work.mkdir()
            self.overlay(ref, upper, work)
            save(self.statefile, {'ref': ref, 'upper': str(upper), 'work': str(work)})
        except BaseException:
            if mount_info(self.runtime): run('umount', self.runtime)
            run('umount', self.ram)
            raise

    def rebase(self, ref):
        old = self.live_state()
        upper = self.ram / ('upper-' + uuid.uuid4().hex)
        work = self.ram / ('work-' + uuid.uuid4().hex)
        upper.mkdir(); work.mkdir()
        run('umount', self.runtime)
        try:
            self.overlay(ref, upper, work)
            save(self.statefile, {'ref': ref, 'upper': str(upper), 'work': str(work)})
        except BaseException:
            if mount_info(self.runtime): run('umount', self.runtime)
            self.overlay(old['ref'], old['upper'], old['work'])
            save(self.statefile, old)
            raise
        shutil.rmtree(old['upper']); shutil.rmtree(old['work'])

    def prune(self):
        keep = {self.reference()['name'], self.live_state()['ref']['name']}
        if self.previous.exists(): keep.add(self.reference(self.previous)['name'])
        with self.writable():
            for path in self.generations.iterdir():
                if re.fullmatch(r'gen-[0-9a-f]{32}', path.name) and path.name not in keep:
                    if path.is_symlink() or not path.is_dir(): raise ValueError('Unexpected generation entry')
                    shutil.rmtree(path)

    def checkpoint(self, shutdown=False):
        with self.lock():
            self.live_state()
            with self.paused(restart=not shutdown) as consumer:
                ref = self.capture()
                consumer.close()  # An open overlay file would keep the mount busy during rebase.
                if shutdown:
                    run('umount', self.runtime)
                    run('umount', self.ram)
                    self.statefile.unlink(missing_ok=True)
                else:
                    self.rebase(ref)
                    self.prune()
        return ref

    def status(self):
        state = self.live_state()
        v = os.statvfs(self.ram)
        used = (v.f_blocks - v.f_bfree) * v.f_frsize
        total = v.f_blocks * v.f_frsize
        ref = self.reference()
        manifest = regular_json(self.generations / ref['name'] / 'manifest.json')
        report = {'runtime': str(self.runtime), 'persistence_read_only': True,
                  'active_generation': state['ref']['name'], 'saved_generation': ref['name'],
                  'ram_used_bytes': used, 'ram_limit_bytes': total,
                  'backup_age_seconds': round(time.time() - manifest['created'], 1),
                  'apps': {n: self.active(n) for n in self.apps}}
        report['needs_attention'] = used >= total * .8 or report['backup_age_seconds'] > 26 * 3600
        return report


def render(config_path, helper, cfg):
    prefix = cfg['prefix']; service = prefix + '.service'
    command = f'/usr/bin/python3 {helper} --config {config_path} '
    return {
        service: '[Unit]\nDescription=Meteohub RAM runtime and shutdown checkpoint\nPartOf=' + cfg['target'] +
            '\nRequiresMountsFor=' + cfg['persist'] + '\nBefore=' + ' '.join(cfg['apps']) +
            '\n[Service]\nType=oneshot\nRemainAfterExit=yes\nUMask=0077\nTimeoutStartSec=15min\nTimeoutStopSec=15min\n' +
            'ExecStart=' + command + 'restore\nExecStop=' + command + 'shutdown\n',
        prefix + '-checkpoint.service': '[Unit]\nDescription=Meteohub verified RAM checkpoint\nRequires=' + service +
            '\nAfter=' + service + '\n[Service]\nType=oneshot\nUMask=0077\nTimeoutStartSec=15min\nExecStart=' + command + 'checkpoint\n',
        prefix + '-checkpoint.timer': '[Unit]\nDescription=Meteohub daily SD checkpoint\nPartOf=' + cfg['target'] +
            '\n[Timer]\nOnCalendar=*-*-* 04:15:00 Europe/Berlin\nPersistent=true\nAccuracySec=1min\n[Install]\nWantedBy=' + cfg['target'] + '\n',
        prefix + '-check.service': '[Unit]\nDescription=Meteohub RAM capacity and checkpoint age check\nRequires=' + service +
            '\nAfter=' + service + '\n[Service]\nType=oneshot\nExecStart=' + command + 'check\n',
        prefix + '-check.timer': '[Unit]\nDescription=Meteohub RAM health check\nPartOf=' + cfg['target'] +
            '\n[Timer]\nOnBootSec=5min\nOnUnitActiveSec=5min\n[Install]\nWantedBy=' + cfg['target'] + '\n',
    }


def host_preflight(s, ram_mib):
    mounts = run('findmnt', '-rn', '-o', 'TARGET').stdout.splitlines()
    if any(p.startswith(str(s.runtime) + '/') for p in mounts):
        raise ValueError('Nested runtime mounts must be reviewed before RAM installation')
    for name in APPS[1:]:
        actual = run('systemctl', 'show', name, '-p', 'RootDirectory', '--value').stdout.strip()
        if actual != str(s.runtime / 'root'): raise ValueError('Unit uses a different runtime: ' + name)
    if run('systemctl', 'show', TIME_WAIT, '-p', 'ActiveState', '--value').stdout.strip() != 'active':
        raise ValueError('Verified time gate must already be active')
    if Path('/sys/block/zram0/backing_dev').read_text().strip() != 'none':
        raise ValueError('RAM-only ZRAM required')
    if any('/dev/zram' not in line for line in run('swapon', '--noheadings', '--show=NAME').stdout.splitlines()):
        raise ValueError('Non-ZRAM swap present')
    available = next(int(line.split()[1]) * 1024 for line in Path('/proc/meminfo').read_text().splitlines()
                     if line.startswith('MemAvailable:'))
    if available < (ram_mib + 128) * 1024 * 1024:
        raise ValueError('Insufficient available RAM for requested cap plus 128 MiB headroom')


def install(args):
    config = safe_path(args.config)
    if config.exists() or config.is_symlink(): raise ValueError('RAM installation already exists; inspect status first')
    helper = HELPER
    if helper.exists() or helper.is_symlink(): raise ValueError('RAM helper path already exists')
    cfg = dict(schema=1, helper=str(helper), runtime=str(safe_path(args.runtime)), persist=str(safe_path(args.persist)),
               uuid=args.uuid, ram=RAM_ROOT, ram_mib=args.ram_mib,
               lock=STORAGE_LOCK, apps=APPS, target=TARGET, prefix=PREFIX)
    s = Storage(cfg); s.disk()
    if mount_info(s.runtime) or mount_info(s.ram): raise ValueError('RAM/runtime mount already exists')
    if s.current.exists(): s.verify(s.reference())
    if not (s.runtime / 'live-install.json').is_file(): raise ValueError('Persistent live installation required')
    host_preflight(s, args.ram_mib)
    units = render(config, helper, cfg)
    files = {UNIT_DIR / n: text for n, text in units.items()}
    dropin = '[Unit]\nRequires=' + PREFIX + '.service\nAfter=' + PREFIX + '.service\n'
    for n in APPS + [TARGET]:
        text = dropin
        if n == APPS[3]:
            text += 'Requires=' + TIME_WAIT + '\nAfter=' + TIME_WAIT + ' time-sync.target\n'
        files[UNIT_DIR / (n + '.d') / '30-ram-storage.conf'] = text
    for p in files:
        if p.exists() or p.is_symlink(): raise ValueError('Existing managed path: ' + str(p))
    with s.lock(), s.paused() as consumer:
        ref = s.capture()
        consumer.close()
        cfg['installed_files'] = {str(p): hashlib.sha256(text.encode()).hexdigest() for p, text in files.items()}
        cfg['helper_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        written = []
        try:
            helper.parent.mkdir(parents=True, exist_ok=True)
            atomic(helper, Path(__file__).read_bytes()); written.append(helper)
            save(config, cfg); written.append(config)
            for p, text in files.items():
                p.parent.mkdir(parents=True, exist_ok=True)
                atomic(p, text.encode()); p.chmod(0o644); written.append(p)
            run('systemctl', 'daemon-reload')
            # ExecStart restore does not take the parent installation lock.
            run('systemctl', 'start', PREFIX + '.service')
        except BaseException:
            if not mount_info(s.runtime) and not mount_info(s.ram):
                for p in reversed(written): p.unlink()
                run('systemctl', 'daemon-reload')
                run('systemctl', 'reset-failed', PREFIX + '.service', check=False)
            raise
    for n in (PREFIX + '-checkpoint.timer', PREFIX + '-check.timer'):
        run('systemctl', 'enable', '--now', n)
    print(json.dumps({'installed': True, 'initial_generation': ref['name'], 'root_ro_changed': False}, indent=2))
    print(json.dumps(s.status(), indent=2))


def uninstall(s, config):
    """Return newest saved runtime to writable host storage before removing RAM dependencies."""
    root = mount_info(Path('/'))
    if not root or root['fstype'] == 'overlay' or 'rw' not in root['options'].split(','):
        raise ValueError('Rollback requires normal writable host root; disable root overlay and reboot first')
    s.live_state()
    owned = {Path(p): expected for p, expected in s.cfg['installed_files'].items()}
    helper = safe_path(s.cfg['helper'])
    owned[helper] = s.cfg['helper_sha256']
    for path, expected in owned.items():
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Managed file changed; refusing removal: ' + str(path))
    prefix = s.cfg['prefix']
    timers = [prefix + '-checkpoint.timer', prefix + '-check.timer']
    backup = Path(tempfile.mkdtemp(prefix='meteohub-ram-remove-before-', dir='/root'))
    for i, path in enumerate(list(owned) + [config]):
        shutil.copy2(path, backup / str(i))
    paths = list(owned) + [config]
    save(backup / 'paths.json', [str(p) for p in paths])
    print('ROLLBACK CONFIG BACKUP:', backup, flush=True)
    # Never hold the checkpoint lock while asking systemd to run ExecStop.
    run('systemctl', 'stop', *timers, prefix + '-checkpoint.service', prefix + '-check.service')
    removed = False
    try:
        run('systemctl', 'stop', prefix + '.service')
        if mount_info(s.runtime) or mount_info(s.ram): raise ValueError('RAM mounts still present')
        if run('systemctl', 'show', prefix + '.service', '-p', 'Result', '--value').stdout.strip() != 'success':
            raise ValueError('Final shutdown backup failed')
        with s.lock():
            tree = s.verify(s.reference())
            need = sum(e.get('size', 0) for e in fingerprint(tree).values()) + 64 * 1024 * 1024
            v = os.statvfs(s.runtime.parent)
            if v.f_bavail * v.f_frsize < need: raise ValueError('Insufficient space for rollback copy')
            restored = Path(tempfile.mkdtemp(prefix='runtime-restored-', dir=s.runtime.parent))
            run('cp', '-a', '--', str(tree) + '/.', restored)
            if fingerprint(restored) != fingerprint(tree): raise ValueError('Rollback copy verification failed')
            original = s.runtime.with_name(s.runtime.name + '-before-ram-' + uuid.uuid4().hex)
            os.rename(s.runtime, original)
            try: os.rename(restored, s.runtime)
            except BaseException:
                os.rename(original, s.runtime)
                raise
            run('sync', '-f', s.runtime)
            run('systemctl', 'disable', *timers)
            for path in paths: path.unlink()
            run('systemctl', 'daemon-reload')
            removed = True
        run('systemctl', 'start', s.cfg['target'], *s.apps)
        print('REMOVED: RAM overlay; latest verified data restored to normal runtime. Old base:', original)
    except BaseException:
        if not removed:
            for i, path in enumerate(paths):
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup / str(i), path)
            run('systemctl', 'daemon-reload')
            run('systemctl', 'start', s.cfg['target'], *s.apps)
            for timer in timers: run('systemctl', 'enable', '--now', timer)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default=DEFAULT_CONFIG)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('install')
    p.add_argument('--runtime', required=True); p.add_argument('--persist', required=True)
    p.add_argument('--uuid', required=True); p.add_argument('--ram-mib', type=int, default=320)
    for name in ('restore', 'shutdown', 'checkpoint', 'status', 'check', 'remove'): sub.add_parser(name)
    args = parser.parse_args()
    if os.getuid() != 0: parser.error('Run as root')
    os.umask(0o077)
    if args.action == 'install': install(args); return 0
    config = safe_path(args.config)
    info = config.stat()
    if info.st_uid != 0 or stat.S_IMODE(info.st_mode) & 0o022: raise ValueError('Unsafe config ownership/mode')
    s = Storage(regular_json(config))
    if args.action == 'remove': uninstall(s, config)
    elif args.action == 'restore': s.restore()
    elif args.action in ('checkpoint', 'shutdown'):
        print(json.dumps({'saved': s.checkpoint(args.action == 'shutdown')}))
    elif args.action == 'check':
        try:
            with s.lock(): report = s.status()
        except BlockingIOError:
            print('SKIPPED: storage operation in progress; health not assessed this time')
            return 0
        print(json.dumps(report, indent=2))
        if report['needs_attention']: return 2
    else:
        report = s.status(); print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    def interrupted(signum, frame):
        raise InterruptedError('Interrupted; attempting mount/service cleanup')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try: raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as error:
        print('STOP:', error, file=sys.stderr)
        raise SystemExit(1)
