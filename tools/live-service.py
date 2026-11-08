#!/usr/bin/env python3
"""Install persistent direct-TCP reception after a matching native archive test.

Only the prepared user-owned runtime is used. No original station changes.
"""
import argparse
import datetime
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

TOOLS = Path(__file__).resolve().parent
UNIT_DIR = Path('/etc/systemd/system')
TARGET = 'meteohub-live.target'
LOGGER = 'meteohub-live-logger.service'
RUNTIME = 'meteohub-live-runtime.service'
WEB = 'meteohub-web-test.service'
SOCKET = 'meteohub-web-test.socket'
INDEX = 'meteohub-dashboard-index.service'
NAMES = (TARGET, LOGGER, RUNTIME, WEB, SOCKET, INDEX)
MARKER = 'live-install.json'
TIME_WAIT = 'systemd-time-wait-sync.service'
RAM_CONFIG = Path('/etc/meteohub-ram.json')


def load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / (name + '.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def run(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, text=True, **kwargs)


def ctl(*args):
    return run(['sudo', '-n', 'systemctl', *args])


def fields(unit):
    result = run(['systemctl', 'show', unit, '-p', 'LoadState', '-p', 'ActiveState',
                  '-p', 'User', '-p', 'RootDirectory', '-p', 'FragmentPath', '-p', 'NRestarts'], capture_output=True)
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)


def save(path, value):
    load('extension-update').atomic(path, (json.dumps(value, indent=2) + '\n').encode())


def digest(data):
    return hashlib.sha256(data).hexdigest()


def lock(runtime):
    fd = os.open(runtime / '.feed-consumer.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    stream = os.fdopen(fd, 'w')
    try: fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException: stream.close(); raise
    return stream


def refuse_live(runtime):
    if (runtime / MARKER).exists() or (runtime / MARKER).is_symlink():
        raise ValueError('Persistent installation exists: use live-status/live-stop/live-remove, not a second receiver test')


def accepted_report(candidate, config, host, port):
    for report in sorted(candidate.parent.glob('native-direct-test-*'), reverse=True, key=lambda p: p.stat().st_mtime):
        result_path = report / 'result.json'; config_path = report / 'logger.conf'
        if report.is_symlink() or result_path.is_symlink() or config_path.is_symlink():continue
        try:
            result = json.loads(result_path.read_text())
            same = config_path.read_text() == config
        except (OSError, ValueError):continue
        if (same and result.get('source') == host + ':' + str(port)
            and result.get('transport') == 'native Meteohub TCP/IP'
            and result.get('archive_observed') is True and result.get('web_private_network_restored') is True
            and result.get('fresh_raw_records', 0) > 0
            and 'Result=timeout' in result.get('logger_status', [])
            and 'ExecMainStatus=0' in result.get('logger_status', [])
            and result.get('duration_seconds', 0) >= 60
            and not result.get('invalid_new_lines')
            and not result.get('truncated_or_replaced')):
            return str(report)
    raise ValueError('No successful direct native archive test matches this configuration/source; run direct-test first')


def render(candidate, runtime, uid, gid):
    """Generate units; caller supplies validated paths. No shell commands in units."""
    live = runtime / 'live'; shared = 'meteohub-live-' + str(uid)
    host = json.loads((live / 'source.json').read_text())['host']
    probe = load('probe-cgi'); network = load('direct-network')
    base = probe.properties(candidate, runtime)
    base = [p for p in base if not p.startswith(('RuntimeMaxSec=', 'TimeoutStopSec=', 'TemporaryFileSystem=', 'LimitFSIZE=', 'PrivateNetwork='))]
    common = ['User=' + str(uid), 'Group=' + str(gid), 'TimeoutStopSec=30s',
              'Restart=always', 'RestartSec=30s', 'LimitFSIZE=1G',
              'LogRateLimitIntervalSec=30s', 'LogRateLimitBurst=100']
    shared_run = ['BindPaths=/run/' + shared + ':/run']
    logger = base + common + network.policy(host) + shared_run + [
        'BindReadOnlyPaths=' + str(live / 'logger.conf') + ':/home/meteohub/logger-live.conf',
        'BindPaths=' + str(runtime / '.feed-consumer.lock') + ':/run/feed-consumer.lock']
    web = base + common + network.policy() + shared_run
    index = [p for p in base if not p.startswith('ReadWritePaths=')] + common + [
        'PrivateNetwork=yes', 'TemporaryFileSystem=/run:ro', 'ReadWritePaths=+/data/dashboard']
    def service(description, props, command, extra=''):
        return ('[Unit]\nDescription=' + description + '\nPartOf=' + TARGET +
                '\nRequires=' + RUNTIME + '\nAfter=' + RUNTIME + ' network-online.target\n' +
                'Wants=network-online.target\nStartLimitIntervalSec=0\nRequiresMountsFor=' + str(runtime) + ' ' + str(candidate) +
                '\n' + extra + '\n[Service]\n' + '\n'.join(props) + '\nExecStart=' + command + '\n')
    result = {
        TARGET: '[Unit]\nDescription=Meteohub continuous direct TCP reception\nRequires=' + RUNTIME +
                '\nAfter=network-online.target\nWants=network-online.target ' + ' '.join((LOGGER, SOCKET, WEB, INDEX)) +
                '\n\n[Install]\nWantedBy=multi-user.target\n',
        RUNTIME: '[Unit]\nDescription=Meteohub shared volatile process state\nPartOf=' + TARGET +
                 '\n\n[Service]\nType=oneshot\nRemainAfterExit=yes\nUser=' + str(uid) + '\nGroup=' + str(gid) +
                 '\nRuntimeDirectory=' + shared + '\nRuntimeDirectoryMode=0700\nExecStart=/usr/bin/true\nNoNewPrivileges=yes\n',
        LOGGER: service('Meteohub original logger (direct TCP)', logger,
            '/usr/bin/flock --nonblock --no-fork /run/feed-consumer.lock /usr/bin/env -i PATH=/usr/bin:/bin HOME=/home/meteohub LANG=C '
            'LD_BIND_NOW=1 LD_LIBRARY_PATH=/home/meteohub/lib:/usr/lib/arm-linux-gnueabihf '
            '/home/meteohub/bin/loggerd -n -c /home/meteohub/logger-live.conf',
            'Requires=' + TIME_WAIT + '\nAfter=' + TIME_WAIT + ' time-sync.target\n'),
        WEB: service('Meteohub private web interface', web,
                     '/usr/sbin/lighttpd -D -f /opt/meteohub-web/lighttpd.conf',
                     'Requires=' + SOCKET + '\nAfter=' + SOCKET + '\n'),
        SOCKET: '[Unit]\nDescription=Meteohub loopback HTTP socket\nPartOf=' + TARGET +
                '\n\n[Socket]\nListenStream=127.0.0.1:18090\nAccept=no\nNoDelay=yes\n',
        INDEX: service('Meteohub derived dashboard index', index,
            '/usr/bin/env PYTHONDONTWRITEBYTECODE=1 METEO_DASHBOARD_STATE=/data/dashboard '
            'METEO_DASHBOARD_ARCHIVE=/data/weather METEO_DASHBOARD_LIVE=/data/unused-direct-provenance.jsonl '
            '/usr/bin/python3 /opt/meteohub-dashboard/current/index_weather.py'),
    }
    assert set(result) == set(NAMES)
    return result


def read_state(candidate, runtime, partial=False):
    path = runtime / MARKER
    if path.is_symlink() or not path.is_file():raise ValueError('No regular persistent installation record')
    state = json.loads(path.read_text())
    if (state.get('schema') != 1 or state.get('uid') != os.getuid() or state.get('candidate') != str(candidate)
        or state.get('runtime') != str(runtime) or set(state.get('units', {})) != set(NAMES)):
        raise ValueError('Persistent installation record does not match this runtime/user')
    for name, expected in state['units'].items():
        path = UNIT_DIR / name
        if partial and not path.exists() and not path.is_symlink():continue
        if path.is_symlink() or not path.is_file() or digest(path.read_bytes()) != expected:
            raise ValueError('Persistent unit missing/changed; manual review required: ' + name)
    config = runtime / 'live/logger.conf'
    if state.get('config_sha256') and (config.is_symlink() or not config.is_file() or digest(config.read_bytes()) != state['config_sha256']):
        raise ValueError('Live logger configuration changed; review before proceeding')
    return state


def check_new_units(runtime):
    for name in NAMES:
        path = UNIT_DIR / name
        if path.exists() or path.is_symlink():raise ValueError('Refusing existing unit file: ' + str(path))
        item = fields(name)
        if item.get('LoadState') == 'not-found':continue
        if (name not in (WEB, SOCKET, INDEX) or not item.get('FragmentPath', '').startswith('/run/systemd/transient/')
            or (name != SOCKET and (item.get('User') != str(os.getuid()) or item.get('RootDirectory') != str(runtime / 'root')))):
            raise ValueError('Existing unit is not our matching transient test: ' + name)


def web_auth_check():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open('http://127.0.0.1:18090/cgi-bin/meteohub.cgi', timeout=10):pass
    except urllib.error.HTTPError as error:
        if error.code == 401:return
        raise
    raise ValueError('Unauthenticated web request was not rejected')


def write_units(plan):
    for name in NAMES:
        run(['sudo', '-n', 'install', '-o', 'root', '-g', 'root', '-m', '0644', plan / name, UNIT_DIR / name])
    ctl('daemon-reload')


def remove_units(state):
    # All hashes checked before touching any file; retain archives, settings and backup.
    for name in NAMES:
        path = UNIT_DIR / name
        if path.exists() and digest(path.read_bytes()) != state['units'][name]:
            raise ValueError('Refusing rollback over modified unit: ' + name)
    if (UNIT_DIR / TARGET).exists():ctl('disable', TARGET)
    present = [n for n in NAMES if fields(n).get('LoadState') != 'not-found']
    if present:ctl('stop', *present)
    for name in NAMES:
        if (UNIT_DIR / name).exists():run(['sudo', '-n', 'rm', '--', UNIT_DIR / name])
    ctl('daemon-reload')
    subprocess.run(['sudo', '-n', 'systemctl', 'reset-failed', *NAMES], capture_output=True)


def install(candidate, runtime, host, port):
    direct = load('test-native-direct'); web = load('web-test'); extension = load('extension-update')
    refuse_live(runtime);web.check_paths(candidate, runtime)
    if fields(TIME_WAIT).get('LoadState') != 'loaded':
        raise ValueError('Required clock synchronization wait unit is missing or masked: ' + TIME_WAIT)
    config = direct.config_copy(runtime / 'root/home/meteohub/logger.conf', host, port)
    if not any(s.split()[:2] == ['@SENSORIDMAP', '0'] for s in config.splitlines()):
        raise ValueError('Assign sensors and verify native recording first')
    report = accepted_report(candidate, config, host, port)
    direct.web_state(runtime);extension.verify_installed(runtime);extension.inspect(runtime)
    check_new_units(runtime)
    if (runtime / 'live').exists() or (runtime / 'live').is_symlink():raise ValueError('Existing live preparation; inspect it first')
    run(['sudo', '-v'])
    with lock(runtime):
        # Validate kernel IP restrictions with actual connections before takeover.
        direct.network.check_filter(web.web_properties(candidate, runtime, True))
        direct.network.check_filter(direct.logger_properties(candidate, runtime, host, 60), host)
        backup = Path(tempfile.mkdtemp(prefix='live-before-', dir=candidate.parent))
        shutil.copytree(runtime / 'root/home/meteohub', backup / 'home', symlinks=True)
        plan = backup / 'units';plan.mkdir()
        live = runtime / 'live';live.mkdir(mode=0o700)
        (live / 'logger.conf').write_text(config)
        save(live / 'source.json', {'host': host, 'port': port})
        units = render(candidate, runtime, os.getuid(), os.getgid())
        for name, data in units.items():(plan / name).write_text(data)
        try:run(['sudo', '-n', 'systemd-analyze', 'verify', *[plan / n for n in NAMES]])
        except BaseException:
            shutil.rmtree(live);raise
        state = {'schema': 1, 'uid': os.getuid(), 'gid': os.getgid(), 'candidate': str(candidate),
                 'runtime': str(runtime), 'backup': str(backup), 'accepted_report': report,
                 'source': host + ':' + str(port), 'phase': 'installing',
                 'config_sha256': digest(config.encode()),
                 'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                 'units': {n: digest(t.encode()) for n, t in units.items()},
                 'archive_before': direct.native.archive_snapshot(runtime / 'root/data/weather'), 'started': time.time()}
        save(runtime / MARKER, state)
        print('BACKUP:', backup, flush=True)
        print('ROLLBACK: python3 install-pi.py live-remove', flush=True)
        try:
            extension.stop_service(runtime);direct.stop_web()
            # Transient indexer must unload before a persistent file with its name is installed.
            for attempt in range(40):
                if fields(INDEX).get('LoadState') == 'not-found':break
                time.sleep(.25)
            else:raise ValueError('Transient indexer did not unload')
            write_units(plan)
        except BaseException:
            restore(candidate, runtime, state);raise
    # The durable logger takes the same lock; the installer must release it first.
    try:
        ctl('start', TARGET)
        web_auth_check()
        for name in (LOGGER, WEB, INDEX):
            if fields(name).get('ActiveState') != 'active':raise ValueError('Service not active: ' + name)
        ctl('enable', TARGET)
        state['phase'] = 'installed';save(runtime / MARKER, state)
    except BaseException:
        restore(candidate, runtime, state);raise
    print('INSTALLED: continuous direct TCP logger, loopback web and dashboard index; boot target enabled.', flush=True)
    print('Archive recording after installation, reboot and long-term acceptance remain to be checked.', flush=True)
    status(candidate, runtime)


def restore(candidate, runtime, state):
    if RAM_CONFIG.exists() or RAM_CONFIG.is_symlink():
        raise ValueError('RAM storage installed: remove it with meteohub-ram.py remove before live-remove')
    print('RESTORING: private test website; native archive retained.', flush=True)
    read_state(candidate, runtime, partial=True)
    remove_units(state)
    (runtime / MARKER).rename(Path(state['backup']) / 'removed-install.json')
    (runtime / 'live').rename(Path(state['backup']) / 'live-config')
    load('test-native-direct').stop_web()
    load('web-test').start(candidate, runtime)
    load('extension-update').start_index(candidate, runtime)
    print('RESTORED: temporary private web/index; no logger or boot target. All raw data retained.', flush=True)


def recent_records(weather):
    """Bounded tails for current status; not a complete interval/gap analysis."""
    last = {}
    paths = sorted(weather.glob('*/raw'))[-2:]
    for path in paths:
        if path.is_symlink() or path.parent.is_symlink():raise ValueError('Linked raw archive refused')
        with path.open('rb') as stream:
            size = os.fstat(stream.fileno()).st_size
            offset = max(0, size - 262144);stream.seek(offset)
            if offset:stream.readline()  # Discard possibly incomplete first line.
            data = stream.read(size - stream.tell())
        for line in data.splitlines(keepends=True):
            fields = line.decode('ascii', errors='replace').split()
            if not line.endswith(b'\n') or len(fields) < 3:continue
            try:
                if not re.fullmatch(r'(?:t|th|thb|wind|rain|uv|sol|data)\d+', fields[1]):continue
                stamp = datetime.datetime.strptime(fields[0], '%Y%m%d%H%M%S').replace(tzinfo=datetime.timezone.utc).timestamp()
                if any(not re.fullmatch(r'-?\d+', value) for value in fields[2:]):continue
            except ValueError:continue
            last[fields[1]] = max(stamp, last.get(fields[1], 0))
    now = time.time()
    return {sensor: {'utc': datetime.datetime.fromtimestamp(stamp, datetime.timezone.utc).isoformat(),
                     'age_seconds': round(now - stamp, 1)} for sensor, stamp in sorted(last.items())}


def status(candidate, runtime):
    state = read_state(candidate, runtime)
    record = {'source': state['source'], 'phase': state['phase'], 'units': {},
              'boot_enabled': subprocess.run(['systemctl', 'is-enabled', '--quiet', TARGET]).returncode == 0}
    for name in (TARGET, LOGGER, WEB, INDEX):record['units'][name] = fields(name)
    try:
        record['archive_since_install'] = load('test-native-logger').archive_result(
            runtime / 'root/data/weather', state['archive_before'], state['started'])
    except ValueError as error:record['archive_since_install'] = {'inspection_limit_or_error': str(error)}
    record['recent_sensors'] = recent_records(runtime / 'root/data/weather')
    record['boot_changed_since_install'] = Path('/proc/sys/kernel/random/boot_id').read_text().strip() != state.get('boot_id')
    try:record['index'] = json.loads((runtime / 'root/data/dashboard/status.json').read_text())
    except (OSError, ValueError):record['index'] = {'error': 'not available'}
    print(json.dumps(record, indent=2), flush=True)
    print('Point-in-time status only; inspect per-sensor intervals and gaps for long-term acceptance.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('install', 'status', 'stop', 'resume', 'remove'))
    parser.add_argument('candidate', type=Path);parser.add_argument('runtime', type=Path)
    parser.add_argument('--host');parser.add_argument('--port', type=int, default=5500)
    args = parser.parse_args()
    if os.geteuid() == 0:parser.error('Run as the normal application user')
    os.umask(0o077)
    candidate = args.candidate.resolve(strict=True);runtime = args.runtime.resolve(strict=True)
    if args.action == 'install':
        import ipaddress
        if not args.host:parser.error('Explicit source IP required')
        install(candidate, runtime, str(ipaddress.IPv4Address(args.host)), args.port)
    elif args.action == 'status':status(candidate, runtime)
    else:
        state = read_state(candidate, runtime, partial=args.action == 'remove')
        run(['sudo', '-v'])
        if args.action == 'remove':restore(candidate, runtime, state)
        elif args.action == 'stop':
            ctl('disable', TARGET);ctl('stop', TARGET)
            print('STOPPED: live target and its services; boot disabled. Configuration and archives retained.')
        else:
            load('web-test').check_paths(candidate, runtime)
            load('extension-update').verify_installed(runtime)
            ctl('start', TARGET);web_auth_check()
            for name in (LOGGER, WEB, INDEX):
                if fields(name).get('ActiveState') != 'active':raise ValueError('Service not active: ' + name)
            ctl('enable', TARGET)
            state['phase'] = 'installed';save(runtime / MARKER, state)
            print('RESUMED: live target, boot enabled. Check live-status for new records.')


if __name__ == '__main__':
    try:main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit('STOP: ' + str(error) + '\nKeep the private report/backup; do not start a second logger.')
