#!/usr/bin/env python3
"""Install/update the private dashboard + SVG extension, independently of native binaries."""
import argparse
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

REPO = Path(__file__).resolve().parents[1]
PREFIX = '/opt/meteohub-dashboard'
UNIT = 'meteohub-dashboard-index.service'
FILES = ('index_weather.py', 'weather_data.py', 'weather_svg.py', 'weather-api.cgi',
         'weather-image.cgi', 'index.html', 'weather.js', 'weather.css')
LINKS = {'srv/www/dashboard': PREFIX + '/current/www/dashboard',
         'srv/www/cgi-bin/weather-api.cgi': PREFIX + '/current/weather-api.cgi',
         'srv/www/cgi-bin/weather-image.cgi': PREFIX + '/current/weather-image.cgi'}


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def digest(data):
    return hashlib.sha256(data).hexdigest()


def destination(name):
    return 'www/dashboard/' + name if name in ('index.html', 'weather.js', 'weather.css') else name


def atomic(path, data, mode=0o600):
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.chmod(name, mode); os.replace(name, path)
    finally:
        if os.path.exists(name):os.unlink(name)


def pointer(path, target):
    # Replacement is atomic; never follow an existing pointer.
    temporary = path.with_name('.' + path.name + '-' + str(time.time_ns()))
    temporary.symlink_to(target)
    try:os.replace(temporary, path)
    finally:temporary.unlink(missing_ok=True)


def ordinary(path, directory=False):
    if path.is_symlink() or not (path.is_dir() if directory else path.is_file()):
        raise ValueError('Missing or linked extension path: ' + str(path))


def release_check(base, name):
    if not re.fullmatch(r'[0-9a-f]{64}', name):raise ValueError('Invalid release identifier')
    release = base / 'releases' / name
    ordinary(release, True); ordinary(release / 'manifest.json')
    manifest = json.loads((release / 'manifest.json').read_text())
    if set(manifest) != {destination(n) for n in FILES}:raise ValueError('Unexpected release contents')
    if digest(json.dumps(manifest, sort_keys=True).encode()) != name:raise ValueError('Release identifier mismatch')
    for relative, expected in manifest.items():
        path = release / relative
        for parent in path.parents:
            if parent == release:break
            ordinary(parent, True)
        ordinary(path)
        if digest(path.read_bytes()) != expected:raise ValueError('Modified extension file: ' + relative)
    return release


def current(base):
    link = base / 'current'
    if not link.is_symlink():raise ValueError('Missing extension release pointer')
    target = os.readlink(link)
    if not re.fullmatch(r'releases/[0-9a-f]{64}', target):raise ValueError('Unexpected release pointer')
    release_check(base, target.split('/')[1])
    return target.split('/')[1]


def verify_installed(runtime):
    base = runtime / 'root' / PREFIX.lstrip('/')
    ordinary(base, True); ordinary(base / 'releases', True)
    name = current(base)
    for relative, target in LINKS.items():
        link = runtime / 'root' / relative
        if not link.is_symlink() or os.readlink(link) != target:
            raise ValueError('Unexpected extension URL mapping: ' + relative)
    return name


def inspect(runtime):
    web = load('web-test')
    root = runtime / 'root'
    for relative in ('opt', 'opt/meteohub-web', 'srv/www', 'srv/www/cgi-bin', 'data'):
        ordinary(root / relative, True)
    launcher = root / 'opt/meteohub-web/cgi-launcher'
    ordinary(launcher)
    if launcher.read_text() not in (web.LAUNCHER, web.EXTENSION_LAUNCHER):
        raise ValueError('Unknown CGI launcher; refusing to overwrite')
    config = root / 'opt/meteohub-web/lighttpd.conf'
    ordinary(config)
    if config.read_text() != web.CONFIG:raise ValueError('Unknown web configuration')
    base = root / PREFIX.lstrip('/')
    old = None
    if base.exists() or base.is_symlink():
        old = verify_installed(runtime)
        if launcher.read_text() != web.EXTENSION_LAUNCHER:raise ValueError('Extension launcher mismatch')
    else:
        for relative in LINKS:
            link = root / relative
            if link.exists() or link.is_symlink():raise ValueError('URL already occupied: ' + relative)
        if launcher.read_text() != web.LAUNCHER:raise ValueError('Extension metadata missing')
    state = root / 'data/dashboard'
    if state.exists() or state.is_symlink():
        ordinary(state, True)
        for path in state.iterdir():
            if path.is_symlink():raise ValueError('Linked index file refused')
    return base, old


def stage_release(base, source):
    payload = {destination(n): (source / n).read_bytes() for n in FILES}
    manifest = {n: digest(data) for n, data in payload.items()}
    name = digest(json.dumps(manifest, sort_keys=True).encode())
    release = base / 'releases' / name
    if release.exists() or release.is_symlink():release_check(base, name);return name
    temp = Path(tempfile.mkdtemp(prefix='.release-', dir=base / 'releases'))
    try:
        for relative, data in payload.items():
            path = temp / relative; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data); path.chmod(0o600)
        (temp / 'manifest.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
        temp.rename(release)
    finally:
        if temp.exists():shutil.rmtree(temp)
    release_check(base, name)
    return name


def activate(runtime, name):
    web = load('web-test')
    base = runtime / 'root' / PREFIX.lstrip('/')
    release_check(base, name)
    pointer(base / 'current', 'releases/' + name)
    for relative, target in LINKS.items():
        link = runtime / 'root' / relative
        if not link.is_symlink():link.symlink_to(target)
    atomic(runtime / 'root/opt/meteohub-web/cgi-launcher', web.EXTENSION_LAUNCHER.encode(), 0o700)


def deactivate_first(runtime):
    for relative in LINKS:
        (runtime / 'root' / relative).unlink(missing_ok=True)
    atomic(runtime / 'root/opt/meteohub-web/cgi-launcher', load('web-test').LAUNCHER.encode(), 0o700)
    # Keep failed releases for diagnosis, but outside the installed extension path.
    base = runtime / 'root' / PREFIX.lstrip('/')
    if base.exists():base.rename(runtime / ('extension-failed-' + str(time.time_ns())))


def service_state(runtime):
    result = subprocess.run(['systemctl', 'show', UNIT, '-p', 'LoadState', '-p', 'RootDirectory',
                             '-p', 'User', '-p', 'ExecStart'], text=True, capture_output=True, check=False)
    fields = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    if fields.get('LoadState', 'not-found') == 'not-found':return False
    if (fields.get('RootDirectory') != str(runtime / 'root') or
        fields.get('User') != str(os.getuid()) or
        PREFIX + '/current/index_weather.py' not in fields.get('ExecStart', '')):
        raise ValueError('Indexer unit belongs to another runtime/user; not stopping it')
    return True


def stop_service(runtime):
    if service_state(runtime):
        subprocess.run(['sudo', '-n', 'systemctl', 'stop', UNIT], check=True)
        subprocess.run(['sudo', '-n', 'systemctl', 'reset-failed', UNIT], capture_output=True, check=False)


def index_command(candidate, runtime, once=False):
    props = load('web-test').web_properties(candidate, runtime)
    props = [p for p in props if not p.startswith(('ReadWritePaths=', 'LimitFSIZE='))]
    props += ['ReadWritePaths=+/data/dashboard', 'LimitFSIZE=256M']
    if once:props += ['RuntimeMaxSec=30s']
    command = ['sudo', '-n', 'systemd-run', '--collect', '--expand-environment=no',
               '--uid=' + str(os.getuid()), '--gid=' + str(os.getgid())]
    command += ['--property=' + p for p in props]
    command += ['--wait', '--pipe'] if once else ['--unit=' + UNIT]
    command += ['/usr/bin/env', 'PYTHONDONTWRITEBYTECODE=1',
                'METEO_DASHBOARD_STATE=/data/dashboard', 'METEO_DASHBOARD_ARCHIVE=/data/weather',
                'METEO_DASHBOARD_LIVE=/data/tcp-feed/state/provenance.jsonl',
                '/usr/bin/python3', PREFIX + '/current/index_weather.py']
    if once:command += ['--once']
    return command


def start_index(candidate, runtime):
    subprocess.run(index_command(candidate, runtime, True), check=True, timeout=45)
    status = json.loads((runtime / 'root/data/dashboard/status.json').read_text())
    if status.get('error') or time.time() - status.get('last_success', 0) > 60:
        raise ValueError('Derived index could not be refreshed')
    if (runtime / 'live-install.json').exists():
        load('live-service').read_state(candidate, runtime)
        subprocess.run(['sudo', '-n', 'systemctl', 'start', UNIT], check=True)
    else:
        subprocess.run(index_command(candidate, runtime), check=True)
    result = subprocess.run(['systemctl', 'is-active', UNIT], text=True, capture_output=True)
    if result.returncode:raise ValueError('Indexer did not remain active')


def update(candidate, runtime, rollback=False, services=True, source=None):
    """services=False is reserved for isolated tests, not exposed by CLI."""
    if services:
        load('web-test').check_paths(candidate, runtime)
        subprocess.run(['sudo', '-v'], check=True)
        service_state(runtime)  # Check ownership before changing files.
        if (runtime / 'live-install.json').exists():
            live=load('live-service');live.read_state(candidate,runtime)
            if live.fields(live.TARGET).get('ActiveState')!='active':
                raise ValueError('Live target stopped; resume it before updating the extension')
    base, old = inspect(runtime)
    if rollback:
        if old is None:raise ValueError('No installed extension to roll back')
        previous = base / 'previous'
        if not previous.is_symlink() or not re.fullmatch(r'releases/[0-9a-f]{64}', os.readlink(previous)):
            raise ValueError('No previous extension release available')
        name = os.readlink(previous).split('/')[1];release_check(base, name)
    else:
        if old is None:
            base.mkdir(mode=0o700);(base / 'releases').mkdir(mode=0o700)
        try:name = stage_release(base, source or REPO / 'dashboard')
        except Exception:
            if old is None:deactivate_first(runtime)
            raise
    (runtime / 'root/data/dashboard').mkdir(mode=0o700, exist_ok=True)
    try:
        if services:stop_service(runtime)
        activate(runtime, name)
        if services:start_index(candidate, runtime)
        if old and old != name:pointer(base / 'previous', 'releases/' + old)
    except Exception:
        if services:stop_service(runtime)
        if old:
            activate(runtime, old)
            if services:start_index(candidate, runtime)
        else:deactivate_first(runtime)
        raise
    print('EXTENSION:', name)
    print('Dashboard: /dashboard/; SVG: /cgi-bin/weather-image.cgi (existing web authentication)')
    print('Derived index only; no native logger or TCP collector started. No webserver restart.')
    if (runtime / 'live-install.json').exists():
        print('Persistent indexer resumed; existing live boot configuration retained.')
    else:
        print('Indexer is transient: rerun extension-update after a reboot. No autostart installed.')
    return name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', type=Path);parser.add_argument('runtime', type=Path)
    parser.add_argument('--rollback', action='store_true')
    args = parser.parse_args()
    if os.geteuid() == 0:parser.error('Run as the normal login user')
    os.umask(0o077)
    candidate = args.candidate.resolve(strict=True);runtime = args.runtime.resolve(strict=True)
    fd = os.open(runtime / '.extension-update.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        update(candidate, runtime, args.rollback)


if __name__ == '__main__':
    try:main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit('STOP: ' + str(error))
