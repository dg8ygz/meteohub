#!/usr/bin/python3
"""Preserve the activated temporary web view before a maintenance reboot.

No service restart, config import, boot change or activation value on stdout.
Uses the installed RAM helper's lock, UUID check and RO restoration.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import sys
import tempfile
import time

sys.dont_write_bytecode = True
HELPER = Path('/usr/local/libexec/meteohub-ram.py')
CONFIG = Path('/etc/meteohub-ram.json')
WEB = 'meteohub-web-test.service'
LOGGER = 'meteohub-live-logger.service'


def regular(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > 16 * 1024 * 1024:
        raise ValueError('Unexpected file: ' + str(path))
    return path.read_bytes()


def changed_ranges(before, after):
    if len(before) != 65536 or len(after) != 65536:
        raise ValueError('Expected two 64-KiB application configurations')
    result = []
    for i, (old, new) in enumerate(zip(before, after)):
        if old == new: continue
        if result and result[-1][1] == i - 1: result[-1][1] = i
        else: result.append([i, i])
    return result


def capture(m, storage, sources, evidence):
    """Caller holds storage lock. Only publish after complete content verification."""
    if any(not re.fullmatch(r'[a-z0-9-]+', name) for name in sources):
        raise ValueError('Unexpected snapshot label')
    fingerprints = {name: m.fingerprint(path) for name, path in sources.items()}
    size = sum(v.get('size', 0) for fp in fingerprints.values() for v in fp.values())
    if size > 64 * 1024 * 1024: raise ValueError('Unexpectedly large identity snapshot')
    storage.disk()
    if shutil.disk_usage(storage.persist).free < size + 32 * 1024 * 1024:
        raise ValueError('Insufficient persistence space')
    with storage.writable():
        base = storage.persist / 'identity-migration'
        if base.is_symlink(): raise ValueError('Linked migration directory refused')
        base.mkdir(mode=0o700, exist_ok=True)
        if base.stat().st_uid != 0 or stat.S_IMODE(base.stat().st_mode) != 0o700:
            raise ValueError('Migration directory must be root-owned and mode 0700')
        pending = Path(tempfile.mkdtemp(prefix='.pending-', dir=base))
        for name, source in sources.items():
            m.run('cp', '-a', '--', source, pending / name)
            if m.fingerprint(pending / name) != fingerprints[name] or m.fingerprint(source) != fingerprints[name]:
                raise ValueError('Source changed during capture or copy differs: ' + name)
        if any(m.fingerprint(source) != fingerprints[name] for name, source in sources.items()):
            raise ValueError('Source changed before snapshot completion; retry capture')
        for name, data in evidence.items():
            if not re.fullmatch(r'[a-z0-9.-]+', name): raise ValueError('Invalid evidence name')
            (pending / name).write_bytes(data)
            (pending / name).chmod(0o600)
        manifest = {'schema': 1, 'created': time.time(), 'runtime': str(storage.runtime),
                    'uuid': storage.cfg['uuid'], 'files': m.fingerprint(pending)}
        m.save(pending / 'manifest.json', manifest)
        saved = json.loads(regular(pending / 'manifest.json'))
        # Manifest does not include itself. No file is excluded from verification otherwise.
        actual = m.fingerprint(pending); actual.pop('manifest.json')
        if actual != saved['files']: raise ValueError('Snapshot readback mismatch')
        complete = base / ('ready-' + pending.name.removeprefix('.pending-'))
        pending.rename(complete)
        m.run('sync', '-f', storage.persist)
    storage.disk()
    return complete


def main():
    if os.geteuid() != 0: raise ValueError('Run as root on the Pi')
    os.umask(0o077)
    cfg = json.loads(regular(CONFIG))
    if CONFIG.stat().st_uid != 0 or CONFIG.stat().st_mode & 0o022:
        raise ValueError('Unsafe RAM configuration ownership')
    if hashlib.sha256(regular(HELPER)).hexdigest() != cfg['helper_sha256']:
        raise ValueError('Installed RAM helper differs from its recorded hash')
    spec = importlib.util.spec_from_file_location('ram_storage', HELPER)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    storage = m.Storage(cfg)
    runtime = Path('/home/meteohub/meteohub-staging/5.1e-runtime')
    if storage.runtime != runtime or cfg['uuid'] != '6d332cf5-8a19-4fc5-bcaa-5156ab2dad54':
        raise ValueError('Unexpected runtime or persistence UUID')
    root = m.mount_info(Path('/'))
    if not root or root['fstype'] != 'overlay':
        raise ValueError('Expected the active host RAM overlay')
    web_dropins = Path('/run/systemd/system') / (WEB + '.d')
    view = regular(web_dropins / '50-identity-view.conf').decode()
    matches = re.findall(r'^BindPaths=(/usr/local/libexec/meteohub-identity-[a-z0-9_]+/home):/home/meteohub$', view, re.M)
    if len(matches) != 1: raise ValueError('Expected one known private web home binding')
    private_home = m.safe_path(matches[0]); state = private_home.parent
    if not state.is_dir(): raise ValueError('Missing private identity state')
    live_home = runtime / 'root/home/meteohub'
    base_adapter = Path('/usr/local/libexec/meteohub-ifconfig-compat.py')
    if hashlib.sha256(regular(base_adapter)).hexdigest() != '96c9141c154e406977a2a3b4f8a74c6258f4c554435d7cd665fbd128b79b824f':
        raise ValueError('Unexpected original display adapter')
    sources = {'identity-view': state, 'live-home-before': live_home,
               'web-dropins': web_dropins,
               'logger-dropins': Path('/run/systemd/system') / (LOGGER + '.d'),
               'base-adapter': base_adapter, 'ram-config': CONFIG,
               'live-install': runtime / 'live-install.json',
               'cmdline': Path('/boot/firmware/cmdline.txt'),
               'fstab': Path('/etc/fstab'), 'staging-tool': Path(__file__).resolve()}
    with storage.lock():
        storage.live_state()
        if any(storage.active(app) != 'active' for app in storage.apps):
            raise ValueError('Expected all four applications active')
        pid = m.run('systemctl', 'show', LOGGER, '-p', 'MainPID', '--value').stdout.strip()
        if not pid.isdigit() or int(pid) <= 1: raise ValueError('Expected running logger PID')
        diff = changed_ranges(regular(live_home / 'meteohub.conf'), regular(private_home / 'meteohub.conf'))
        metadata = {'private_home': str(private_home), 'logger_pid': pid,
                    'configuration_changed_bytes': sum(end-start+1 for start,end in diff),
                    'configuration_changed_ranges': diff,
                    'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                    'note': 'Private activation data captured; no import or boot change performed'}
        evidence = {'status.json': json.dumps(metadata, indent=2).encode(),
                    'ram-status.json': json.dumps(storage.status(), indent=2).encode(),
                    'units.txt': m.run('systemctl', 'cat', WEB, LOGGER, 'meteohub-ram.service',
                                      'meteohub-ram-checkpoint.service', 'meteohub-live.target').stdout.encode(),
                    'journal.txt': m.run('journalctl', '-b', '--no-pager', '-n', '250', '-u', WEB,
                                         '-u', LOGGER, '-u', 'meteohub-ram.service',
                                         '-u', 'meteohub-ram-checkpoint.service').stdout.encode()}
        target = capture(m, storage, sources, evidence)
        if pid != m.run('systemctl', 'show', LOGGER, '-p', 'MainPID', '--value').stdout.strip():
            raise ValueError('Logger changed independently during capture; snapshot retained at ' + str(target))
    print('VERIFIED PERSISTENT COPY:', target)
    print(json.dumps({'configuration_changed_bytes': metadata['configuration_changed_bytes'],
                      'configuration_changed_ranges': diff, 'persistence_read_only': True,
                      'logger_pid_unchanged': True, 'services_restarted': False,
                      'boot_settings_changed': False}, indent=2))
    print('Activation values are only in the private snapshot, not in this output.')
    print('Do not reboot yet; the permanent installation has not been applied.')


if __name__ == '__main__':
    def interrupted(signum, frame): raise InterruptedError('Interrupted; restoring read-only mount')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try: main()
    except (OSError, ValueError, RuntimeError) as error:
        print('STOP:', error, file=sys.stderr); raise SystemExit(1)
