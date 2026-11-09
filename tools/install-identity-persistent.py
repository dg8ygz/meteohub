#!/usr/bin/python3
"""Persist an operator-activated private view on the known Pi in maintenance mode.

prepare: verify the saved view, preserve this tool/diagnosis, disable host overlay
for the next boot. install: share the activated configuration between the native
web and logger and install tested identity/PID compatibility files. No reboot.
"""
import argparse
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

sys.dont_write_bytecode = True
RUNTIME = Path('/home/meteohub/meteohub-staging/5.1e-runtime')
ROOT_UUID = '15f4c6be-1102-4331-9904-f78e78afd1fd'
PERSIST_UUID = '6d332cf5-8a19-4fc5-bcaa-5156ab2dad54'
BOOT_UUID = 'B2F0-82D2'
WEB = 'meteohub-web-test.service'
LOGGER = 'meteohub-live-logger.service'
IDENTITY = Path('/usr/local/libexec/meteohub-native-identity')
UNIT_DIR = Path('/etc/systemd/system')
HELPER = Path('/usr/local/libexec/meteohub-ram.py')
CONFIG = Path('/etc/meteohub-ram.json')
FIELD = slice(27836, 27868)
PID_SHA = 'adf373c06033f642081727942e01ecddfcb6488f4e0ff8338ae903cefafffd88'
BASE_SHA = '96c9141c154e406977a2a3b4f8a74c6258f4c554435d7cd665fbd128b79b824f'


def regular(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > 16 * 1024 * 1024:
        raise ValueError('Expected bounded regular file: ' + str(path))
    return path.read_bytes()


def merge_activation(current, before, activated):
    if any(len(value) != 65536 for value in (current, before, activated)):
        raise ValueError('Expected native 64-KiB configurations')
    differences = [i for i, (a, b) in enumerate(zip(before, activated)) if a != b]
    if differences != list(range(FIELD.start, FIELD.stop)):
        raise ValueError('Saved configurations differ outside the confirmed 32-byte field')
    if not re.fullmatch(rb'[A-Za-z0-9]{32}', activated[FIELD]):
        raise ValueError('Unexpected saved activation field format')
    if current[FIELD] not in (before[FIELD], activated[FIELD]):
        raise ValueError('Current activation field changed independently')
    result = bytearray(current)
    result[FIELD] = activated[FIELD]
    return bytes(result)


def identity_unit(directory):
    lines = ['[Service]', 'RestrictAddressFamilies=',
             'RestrictAddressFamilies=AF_INET AF_UNIX AF_NETLINK',
             f'BindReadOnlyPaths={directory}/ifconfig:/usr/sbin/ifconfig',
             f'BindReadOnlyPaths={directory}/cpuinfo:/proc/cpuinfo']
    for key in ('serial', 'name', 'date'):
        lines.append(f'BindReadOnlyPaths={directory}/sd-{key}:/sys/block/mmcblk0/device/{key}')
    lines += [f'BindReadOnlyPaths={directory}/check.py:/opt/meteohub-identity-check.py',
              'ExecStartPre=/usr/bin/python3 /opt/meteohub-identity-check.py']
    return ('\n'.join(lines) + '\n').encode()


def snapshot(m, storage, path):
    path = m.safe_path(str(path))
    if path.parent != storage.persist / 'identity-migration' or not re.fullmatch(r'ready-[a-z0-9_]+', path.name):
        raise ValueError('Unexpected saved identity directory')
    manifest = json.loads(regular(path / 'manifest.json'))
    if manifest.get('schema') != 1 or manifest.get('uuid') != PERSIST_UUID or manifest.get('runtime') != str(RUNTIME):
        raise ValueError('Snapshot belongs to another installation')
    actual = m.fingerprint(path); actual.pop('manifest.json')
    if actual != manifest['files']: raise ValueError('Saved identity manifest mismatch')
    before = regular(path / 'live-home-before/meteohub.conf')
    activated = regular(path / 'identity-view/home/meteohub.conf')
    merge_activation(before, before, activated)
    if hashlib.sha256(regular(path / 'base-adapter')).hexdigest() != BASE_SHA:
        raise ValueError('Unknown saved ifconfig base adapter')
    if hashlib.sha256(regular(path / 'logger-dropins/40-logger-pid.conf')).hexdigest() != PID_SHA:
        raise ValueError('Unknown saved logger PID compatibility file')
    for name in ('cpuinfo', 'sd-serial', 'sd-name', 'sd-date', 'ifconfig', 'check.py'):
        regular(path / 'identity-view' / name)
    return before, activated


def prop(m, unit, name):
    return m.run('systemctl', 'show', unit, '-p', name, '--value').stdout.strip()


def maintenance_cmdline(original):
    if re.findall(rb'overlayroot=\S+', original) != [b'overlayroot=tmpfs:recurse=0']:
        raise ValueError('Unexpected overlay boot option')
    return original.replace(b'overlayroot=tmpfs:recurse=0', b'overlayroot=disabled')


def owned_write(m, path, data, uid=0, gid=0, mode=0o644):
    # Set complete ownership/permissions before publishing the file.
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out:
            os.fchown(out.fileno(), uid, gid); os.fchmod(out.fileno(), mode)
            out.write(data); out.flush(); os.fsync(out.fileno())
        os.replace(name, path)
        m.run('sync', '-f', path.parent)
    finally:
        Path(name).unlink(missing_ok=True)


def prepare(m, storage, saved):
    root = m.mount_info(Path('/')); lower = m.mount_info(Path('/media/root-ro'))
    boot = m.mount_info(Path('/boot/firmware'))
    if root['fstype'] != 'overlay' or not lower or lower['uuid'] != ROOT_UUID:
        raise ValueError('Expected the known read-only host overlay')
    if boot['uuid'] != BOOT_UUID or 'ro' not in boot['options'].split(','):
        raise ValueError('Expected the read-only Pi boot partition')
    cmd = Path('/boot/firmware/cmdline.txt'); original = regular(cmd)
    maintenance = maintenance_cmdline(original)
    with storage.lock():
        storage.live_state(); snapshot(m, storage, saved)
        if any(storage.active(app) != 'active' for app in storage.apps):
            raise ValueError('Expected all application services running')
        # Preserve exactly the verified installer on the separate data partition.
        with storage.writable():
            folder = Path(tempfile.mkdtemp(prefix='maintenance-', dir=storage.persist / 'identity-migration'))
            program = regular(Path(__file__).resolve())
            owned_write(m, folder / 'installer.py', program, mode=0o600)
            if regular(folder / 'installer.py') != program: raise ValueError('Installer copy differs')
            (folder / 'cmdline-before.txt').write_bytes(original)
            (folder / 'journal.txt').write_text(m.run('journalctl', '-b', '--no-pager').stdout)
            (folder / 'units.txt').write_text(m.run('systemctl', 'cat', WEB, LOGGER, 'meteohub-ram.service').stdout)
            m.save(folder / 'plan.json', {'snapshot': str(saved), 'installer_sha256': hashlib.sha256(program).hexdigest(),
                                       'boot_id_before': Path('/proc/sys/kernel/random/boot_id').read_text().strip()})
        m.run('mount', '-o', 'remount,rw', '/boot/firmware')
        try:
            m.atomic(cmd, maintenance)
            if regular(cmd) != maintenance: raise ValueError('Boot option readback mismatch')
        except BaseException:
            m.atomic(cmd, original)
            raise
        finally:
            m.run('sync', '-f', '/boot/firmware')
            m.run('mount', '-o', 'remount,ro', '/boot/firmware')
    print('MAINTENANCE PREPARED; identity snapshot verified; services were not restarted.')
    print('DIAGNOSIS AND INSTALLER:', folder)
    print('AFTER MAINTENANCE REBOOT:')
    print('python3', folder / 'installer.py', 'install', saved)
    print('The installer does not reboot or re-enable the host overlay automatically.')


def confirm_views(m, storage):
    if any(storage.active(app) != 'active' for app in storage.apps):
        raise ValueError('An application did not start')
    shared = RUNTIME / 'root/home/meteohub/meteohub.conf'
    expected = shared.stat()
    for unit in (WEB, LOGGER):
        pid = int(prop(m, unit, 'MainPID'))
        if pid <= 1: raise ValueError('Missing application PID')
        view = Path('/proc') / str(pid) / 'root'
        got = (view / 'home/meteohub/meteohub.conf').stat()
        if (got.st_dev, got.st_ino) != (expected.st_dev, expected.st_ino):
            raise ValueError('Application does not use the shared configuration: ' + unit)
        if unit == LOGGER and (view / 'run/loggerd.pid').read_text().strip() != str(pid):
            raise ValueError('Logger PID file differs from actual main PID')


def install(m, storage, saved):
    root = m.mount_info(Path('/'))
    if root['fstype'] != 'ext4' or root['uuid'] != ROOT_UUID or 'rw' not in root['options'].split(','):
        raise ValueError('Install requires the known writable ext4 maintenance root')
    if re.findall(r'overlayroot=\S+', Path('/proc/cmdline').read_text()) != ['overlayroot=disabled']:
        raise ValueError('Maintenance boot was not selected')
    if IDENTITY.exists() or IDENTITY.is_symlink(): raise ValueError('Permanent identity directory already exists')
    before, activated = snapshot(m, storage, saved)
    targets = {UNIT_DIR / (unit + '.d') / '60-native-identity.conf': identity_unit(IDENTITY)
               for unit in (WEB, LOGGER)}
    targets[UNIT_DIR / (LOGGER + '.d') / '40-logger-pid.conf'] = regular(saved / 'logger-dropins/40-logger-pid.conf')
    for unit in (WEB, LOGGER):
        if prop(m, unit, 'RootDirectory') != str(RUNTIME / 'root') or prop(m, unit, 'ExecStartPre'):
            raise ValueError('Unexpected native unit root or existing preflight: ' + unit)
        families = set(prop(m, unit, 'RestrictAddressFamilies').split())
        if families not in ({'AF_INET', 'AF_UNIX'}, {'AF_INET', 'AF_UNIX', 'AF_NETLINK'}):
            raise ValueError('Unexpected address-family policy: ' + unit)
        for line in prop(m, unit, 'BindPaths').split():
            if ':/home/meteohub:' in line or line.endswith(':/home/meteohub'):
                raise ValueError('Unexpected separate application home binding')
        if any(Path('/run/systemd/system', unit + '.d', name).exists() for name in
               ('40-ifconfig-compat.conf', '41-ifconfig-netlink.conf', '50-identity-view.conf', '40-logger-pid.conf')):
            raise ValueError('Temporary test drop-ins still present; maintenance boot required')
    if prop(m, LOGGER, 'ExecStartPost') or prop(m, LOGGER, 'ExecStopPost'):
        raise ValueError('Logger already has lifecycle hooks; review before adding PID compatibility')
    for path in targets:
        if path.exists() or path.is_symlink(): raise ValueError('Drop-in already exists: ' + str(path))
    apply_configuration(m, storage, saved, targets, before, activated)
    # Durable application snapshot includes the activated shared config. The
    # existing checkpoint briefly pauses applications again and restores them.
    try:
        storage.checkpoint()
    except BaseException:
        print('INSTALLATION ACTIVE, CHECKPOINT FAILED: keep maintenance mode; do not reboot.', file=sys.stderr)
        raise
    confirm_views(m, storage)
    print('PASS: permanent identity bindings; both services use the same configuration; actual logger PID published.')
    print('PASS: shared activation configuration checkpointed; persistence read-only.')
    print(json.dumps(storage.status(), indent=2))
    print('Maintenance root remains writable. Verify native page and fresh recording before returning to overlay boot.')


def host_identity():
    return (Path('/sys/class/net/eth0/address').read_bytes(),
            Path('/sys/block/mmcblk0/device/serial').read_bytes())


def apply_configuration(m, storage, saved, targets, before, activated, backup_parent=Path('/root')):
    host_before = host_identity()
    config = RUNTIME / 'root/home/meteohub/meteohub.conf'
    backup = Path(tempfile.mkdtemp(prefix='meteohub-identity-before-', dir=backup_parent))
    print('ROLLBACK BACKUP:', backup, flush=True)
    owned = []
    with storage.lock():
        storage.live_state()
        original = regular(config); info = config.stat()
        if info.st_uid == 0: raise ValueError('Expected unprivileged native configuration owner')
        merged = merge_activation(original, before, activated)
        shutil.copy2(config, backup / 'meteohub.conf')
        (backup / 'units-before.txt').write_text(m.run('systemctl', 'cat', WEB, LOGGER).stdout)
        changed = False
        try:
            with storage.paused():
                if regular(config) != original: raise ValueError('Configuration changed while stopping services')
                IDENTITY.mkdir(mode=0o755)
                IDENTITY.chmod(0o755)
                for name in ('cpuinfo', 'sd-serial', 'sd-name', 'sd-date', 'ifconfig', 'check.py'):
                    owned_write(m, IDENTITY / name, regular(saved / 'identity-view' / name),
                                mode=0o755 if name == 'ifconfig' else 0o644)
                for path, content in targets.items():
                    path.parent.mkdir(mode=0o755, exist_ok=True)
                    owned_write(m, path, content); owned.append(path)
                changed = True
                owned_write(m, config, merged, info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode))
                m.run('systemctl', 'daemon-reload')
            confirm_views(m, storage)
            if host_identity() != host_before:
                raise ValueError('Underlying host identity changed')
        except BaseException:
            # The paused context has released its feed lock, including failed starts.
            m.run('systemctl', 'stop', *storage.apps)
            if changed: owned_write(m, config, original, info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode))
            for path in targets: path.unlink(missing_ok=True)
            if IDENTITY.exists(): shutil.rmtree(IDENTITY)
            m.run('systemctl', 'daemon-reload')
            m.run('systemctl', 'start', *storage.apps)
            print('ROLLED BACK: shared configuration and previous services restored; backup retained.', flush=True)
            raise
        m.save(backup / 'installed.json', {'snapshot': str(saved), 'files': {
            str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in owned},
            'identity': m.fingerprint(IDENTITY), 'shared_config_sha256': hashlib.sha256(merged).hexdigest()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'install'))
    parser.add_argument('snapshot', type=Path)
    args = parser.parse_args()
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
    if storage.runtime != RUNTIME or cfg['uuid'] != PERSIST_UUID:
        raise ValueError('Unexpected target runtime or persistence partition')
    storage.disk()
    {'prepare': prepare, 'install': install}[args.action](m, storage, args.snapshot)


if __name__ == '__main__':
    def interrupted(signum, frame): raise InterruptedError('Interrupted; running cleanup')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try: main()
    except (OSError, ValueError, RuntimeError) as error:
        print('STOP:', error, file=sys.stderr); raise SystemExit(1)
