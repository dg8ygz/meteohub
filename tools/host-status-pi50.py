#!/usr/bin/python3
"""Temporary native CGI host-service display, preserving ProtectProc=invisible.

The original CGI reads named PID files and scans `ps ax`, without checking
process names. Publish actual service PIDs plus a short-lived status snapshot;
the private ps adapter adds only these verified host-service entries. Nothing
here starts SSH, Samba or an NTP daemon or grants access to their /proc files.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time

WEB = 'meteohub-web-test.service'
LOGGER = 'meteohub-live-logger.service'
UNIT = 'meteohub-host-status.service'
STATE = Path('/run/meteohub-host-status')
VIEW = Path('/opt/meteohub-host-status')
SHARED = Path('/run/meteohub-live-1000')
DROPIN = Path('/run/systemd/system/meteohub-web-test.service.d/60-host-status.conf')
UNITFILE = Path('/run/systemd/system') / UNIT
REAL_PS = '/opt/meteohub-host-real-ps'
SERVICES = {'dropbear.pid': 'ssh.service', 'smbd.pid': 'smbd.service',
            'ntpd.pid': 'systemd-timesyncd.service'}
MAX_AGE = 30


def run(*args):
    return subprocess.check_output(args, text=True, timeout=20).strip()


def props(unit):
    return dict(line.split('=', 1) for line in run(
        'systemctl', 'show', unit, '--no-pager', '-p',
        'LoadState,ActiveState,MainPID,User,RootDirectory,ProtectProc').splitlines()
        if '=' in line)


def atomic(path, data, mode=0o644):
    fd, tmp = tempfile.mkstemp(prefix='.new-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            os.fchmod(stream.fileno(), mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def boot_id():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def process_start(pid):
    # comm may contain spaces and parentheses; field 22 is starttime.
    return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19])


def collect():
    rows = {}
    synced = run('timedatectl', 'show', '-p', 'NTPSynchronized', '--value') == 'yes'
    for filename, unit in SERVICES.items():
        state = props(unit)
        pid = int(state.get('MainPID', '0'))
        active = state.get('ActiveState') == 'active' and pid > 1
        start = None
        if active:
            try:
                start = process_start(pid)
                again = props(unit)
                active = (again.get('MainPID') == str(pid)
                          and again.get('ActiveState') == 'active'
                          and process_start(pid) == start)
            except (FileNotFoundError, ProcessLookupError):
                active = False
        if filename == 'ntpd.pid': active = active and synced
        rows[filename] = {'unit': unit, 'pid': pid if active else -1,
                          'start_ticks': start, 'active': active}
    return {'boot_id': boot_id(), 'monotonic': time.monotonic(),
            'ntp_synchronized': synced, 'services': rows}


def publish(directory, snapshot):
    for filename, row in snapshot['services'].items():
        atomic(directory / filename, (str(row['pid']) + '\n').encode())
    atomic(directory / 'status.json', (json.dumps(snapshot) + '\n').encode())


def approved_rows(directory, now=None, boot=None):
    """Only accept fresh, same-boot snapshots with matching current PID files."""
    try:
        data = json.loads((directory / 'status.json').read_text())
        age = (time.monotonic() if now is None else now) - data['monotonic']
        if data['boot_id'] != (boot_id() if boot is None else boot) or not 0 <= age <= MAX_AGE:
            return []
        rows = []
        for filename, unit in SERVICES.items():
            row = data['services'][filename]
            pid = row['pid']
            if (row['unit'] != unit or type(pid) is not int or pid <= 1
                    or row['active'] is not True):
                continue
            if filename == 'ntpd.pid' and data['ntp_synchronized'] is not True:
                continue
            if (directory / filename).read_text().strip() != str(pid): continue
            rows.append((pid, unit))
        return rows
    except (OSError, ValueError, TypeError, KeyError):
        return []


def ps(args):
    # All other invocations retain the genuine procps implementation.
    if args != ['ax']:
        os.execv(REAL_PS, [REAL_PS] + args)
    # Native checker ignores sscanf's return value. Omit the nonnumeric header
    # so the explicit stopped sentinel (-1) cannot compare to uninitialized data.
    result = subprocess.run([REAL_PS, 'ax', '--no-headers'], text=True, capture_output=True)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode: return result.returncode
    visible = {line.split()[0] for line in result.stdout.splitlines() if line.split()}
    for pid, unit in approved_rows(VIEW):
        if str(pid) not in visible:
            # Not a command-line disclosure; explicitly label the status bridge.
            print(f'{pid:7d} ? S 0:00 [host-status: {unit}]')
    return 0


def collector():
    st = STATE.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022:
        raise ValueError('Unsafe host-status directory')
    while True:
        try:
            publish(STATE, collect())
        except Exception:
            # Previously published entries expire in <=30s. Restart via systemd.
            (STATE / 'status.json').unlink(missing_ok=True)
            raise
        time.sleep(10)


def rollback(stage):
    manifest = json.loads((stage / 'rollback.json').read_text())
    for path, digest in manifest['files'].items():
        p = Path(path)
        if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            raise ValueError('Rollback refuses changed file: ' + path)
    for name, target in manifest['links'].items():
        p = SHARED / name
        if os.path.lexists(p) and (not p.is_symlink() or os.readlink(p) != target):
            raise ValueError('Rollback refuses changed PID file: ' + str(p))
    for path in manifest['files']: Path(path).unlink(missing_ok=True)
    run('systemctl', 'daemon-reload')
    run('systemctl', 'restart', WEB)
    subprocess.run(['systemctl', 'stop', UNIT], check=True, timeout=30)
    for name in manifest['links']: (SHARED / name).unlink(missing_ok=True)
    # Keep the root-owned snapshot and installer for diagnosis until reboot.
    print('ROLLBACK OK: original web view restored; host services untouched.')


def install():
    if os.geteuid() != 0: raise ValueError('Bitte als root ausfuehren.')
    if run('findmnt', '-nro', 'FSTYPE', '--mountpoint', '/') != 'overlay':
        raise ValueError('Dieser vorlaeufige Test erwartet den aktiven Host-Overlay.')
    before = props(WEB)
    if (before.get('User') != '1000' or before.get('ProtectProc') != 'invisible'
            or before.get('ActiveState') != 'active'
            or before.get('RootDirectory') != '/home/meteohub/meteohub-staging/5.1e-runtime/root'):
        raise ValueError('Unerwartete Webdienst-Konfiguration')
    logger_pid = props(LOGGER)['MainPID']
    if int(logger_pid) <= 1: raise ValueError('Logger nicht aktiv')
    visible_run = Path('/proc') / before['MainPID'] / 'root/run'
    if not os.path.samestat(SHARED.stat(), visible_run.stat()):
        raise ValueError('Webdienst verwendet nicht das erwartete gemeinsame /run')
    names = [STATE, DROPIN, UNITFILE] + [SHARED / f for f in SERVICES]
    if any(os.path.lexists(p) for p in names):
        raise ValueError('Zieldatei existiert bereits; nichts ueberschrieben.')
    binds = run('systemctl', 'show', WEB, '-p', 'BindReadOnlyPaths', '--value')
    if any(':/usr/bin/ps' in word or ':/bin/ps' in word for word in binds.split()):
        raise ValueError('Webdienst hat bereits einen eigenen ps-Bind-Mount')
    if props(UNIT).get('LoadState') != 'not-found':
        raise ValueError('Statusdienst existiert bereits')
    for target in (str(VIEW), REAL_PS):
        if os.path.lexists(Path('/proc') / before['MainPID'] / ('root' + target)):
            raise ValueError('Privates Bind-Ziel existiert bereits: ' + target)
    initial = collect()
    if not initial['services']['dropbear.pid']['active'] or not initial['ntp_synchronized']:
        raise ValueError('SSH oder Zeitsynchronisation nicht bereit')
    stage = Path(tempfile.mkdtemp(prefix='meteohub-host-status-test-', dir='/usr/local/libexec'))
    stage.chmod(0o755)
    script = stage / 'adapter.py'
    atomic(script, Path(__file__).read_bytes(), 0o755)
    # Capture the unmodified host ps BEFORE introducing any private bind.
    real_ps = stage / 'real-ps'
    shutil.copyfile('/usr/bin/ps', real_ps); real_ps.chmod(0o755)
    STATE.mkdir(mode=0o755)
    STATE.chmod(0o755)
    publish(STATE, initial)
    links = {name: str(VIEW / name) for name in SERVICES}
    dropin = ('[Service]\n'
              f'BindReadOnlyPaths={script}:/usr/bin/ps\n'
              f'BindReadOnlyPaths={real_ps}:{REAL_PS}\n'
              f'BindReadOnlyPaths={STATE}:{VIEW}\n')
    unit = ('[Unit]\nDescription=Meteohub host service status for native CGI\n'
            '[Service]\nType=simple\nUser=root\nUMask=0022\n'
            f'ExecStart=/usr/bin/python3 {script} collect\n'
            'Restart=on-failure\nRestartSec=5\nNoNewPrivileges=yes\n'
            'ProtectSystem=strict\nProtectHome=yes\nPrivateTmp=yes\n'
            'CapabilityBoundingSet=\nRestrictAddressFamilies=AF_UNIX\n'
            f'ReadWritePaths={STATE}\n')
    contents = {str(DROPIN): dropin.encode(), str(UNITFILE): unit.encode()}
    manifest = {'files': {p: hashlib.sha256(b).hexdigest() for p, b in contents.items()},
                'links': links}
    atomic(stage / 'rollback.json', json.dumps(manifest).encode(), 0o600)
    print('TEMPORAER BIS REBOOT. Rueckbau: python3', script, 'rollback', flush=True)
    try:
        for name, target in links.items(): (SHARED / name).symlink_to(target)
        for path, payload in contents.items():
            p = Path(path); p.parent.mkdir(parents=True, exist_ok=True); atomic(p, payload)
        run('systemctl', 'daemon-reload')
        run('systemctl', 'start', UNIT)
        deadline = time.monotonic() + 8
        while json.loads((STATE / 'status.json').read_text())['monotonic'] <= initial['monotonic']:
            if time.monotonic() >= deadline:
                raise ValueError('Statusdienst liefert keinen neuen Zustand')
            time.sleep(0.1)
        if props(UNIT)['ActiveState'] != 'active':
            raise ValueError('Statusdienst nicht aktiv')
        run('systemctl', 'restart', WEB)
        after = props(WEB)
        if after['ActiveState'] != 'active' or after['ProtectProc'] != 'invisible':
            raise ValueError('Webdienst/Prozessabschirmung nicht bestaetigt')
        # Inspect with the CGI's uid, root and mount view, not as unrestricted root.
        probe = '''import json,subprocess,pathlib
rows=json.loads(pathlib.Path('/opt/meteohub-host-status/status.json').read_text())
out=subprocess.check_output(['/bin/ps','ax'],text=True)
pids={line.split()[0] for line in out.splitlines() if line.split()}
for name,r in rows['services'].items():
 p=pathlib.Path('/var/run')/name
 assert p.read_text().strip()==str(r['pid']),name
 assert (str(r['pid']) in pids)==r['active'],name
 print(name+': '+('running' if r['active'] else 'stopped'))
'''
        print(run('nsenter', '--target', after['MainPID'], '--mount', '--root',
                  '--wdns=/', '--setgid=1000', '--setuid=1000', '--',
                  '/usr/bin/python3', '-c', probe))
        if props(LOGGER)['MainPID'] != logger_pid:
            raise ValueError('Logger-PID hat sich parallel geaendert; bitte pruefen')
        print('PASS: echte Host-PIDs, NTP synchronisiert, ProtectProc=invisible erhalten.')
        print('Nur Webdienst neu gestartet; bitte native Systemseite neu laden.')
    except Exception:
        try:
            rollback(stage)
        except Exception as error:
            print('Automatischer Rueckbau fehlgeschlagen:', error, file=sys.stderr)
            print('Rueckbau erneut mit: python3', script, 'rollback', file=sys.stderr)
        raise


def runtime_links():
    """Recreate compatibility paths after RuntimeDirectory is recreated at boot.

    Native logger.dat is written only by the vendor logger. Never touch it or
    substitute an archive timestamp. Only create its missing parent directory.
    """
    st = SHARED.lstat()
    if (not stat.S_ISDIR(st.st_mode) or st.st_uid != 1000
            or stat.S_IMODE(st.st_mode) != 0o700):
        raise ValueError('Unexpected shared runtime directory')
    native = SHARED / 'meteohub'
    if not os.path.lexists(native):
        native.mkdir(mode=0o700)
        if os.geteuid() == 0: os.chown(native, 1000, 1000)
    info = native.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 1000 or info.st_mode & 0o022:
        raise ValueError('Unsafe native runtime directory')
    for filename in SERVICES:
        path = SHARED / filename
        target = str(VIEW / filename)
        if os.path.lexists(path):
            if not path.is_symlink() or os.readlink(path) != target:
                raise ValueError('Refusing foreign status PID file: '+str(path))
        else: path.symlink_to(target)


def main():
    if Path(sys.argv[0]).name == 'ps': return ps(sys.argv[1:])
    action = sys.argv[1] if len(sys.argv) == 2 else ''
    if action == 'collect': collector()
    elif action == 'links': runtime_links()
    elif action == 'once': publish(STATE, collect())
    elif action in ('install', 'rollback'):
        fd = os.open('/run/lock/meteohub-storage.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if action == 'install': install()
            else: rollback(Path(__file__).resolve().parent)
        finally:
            os.close(fd)
    else: raise ValueError('Aufruf: host-status-pi50.py install')
    return 0


if __name__ == '__main__':
    try: sys.exit(main())
    except Exception as error:
        print('STOP:', error, file=sys.stderr)
        sys.exit(1)
