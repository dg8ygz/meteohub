#!/usr/bin/env python3
"""Prepare/start a loopback-only, socket-activated native Meteohub test website."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

UNIT = 'meteohub-web-test'
WEB = '/opt/meteohub-web'
CONFIG = '''server.modules = ( "mod_access", "mod_auth", "mod_authn_file", "mod_cgi" )
server.document-root = "/srv/www"
server.bind = "127.0.0.1"
server.port = 18090
server.systemd-socket-activation = "enable"
server.max-connections = 16
server.max-request-size = 1024
server.max-read-idle = 30
server.max-write-idle = 30
index-file.names = ( "index.html" )
mimetype.assign = (
  ".html" => "text/html", ".htm" => "text/html", ".css" => "text/css",
  ".js" => "application/javascript", ".png" => "image/png", ".jpg" => "image/jpeg",
  ".gif" => "image/gif", ".svg" => "image/svg+xml", ".ico" => "image/x-icon",
  ".txt" => "text/plain"
)
url.access-deny = ( "~", ".conf", ".htpasswd", ".key", ".lic" )
auth.backend = "htpasswd"
auth.backend.htpasswd.userfile = "/opt/meteohub-web/users.htpasswd"
auth.require = ( "/" => (
  "method" => "basic", "realm" => "Meteohub private test", "require" => "user=meteohub"
) )
cgi.assign = ( ".cgi" => "/opt/meteohub-web/cgi-launcher" )
'''
LAUNCHER = '''#!/bin/sh
set -eu
[ "$#" = 1 ] && [ "$1" = /srv/www/cgi-bin/meteohub.cgi ] || exit 64
if [ "${REQUEST_METHOD-}" = GET ] && [ -z "${QUERY_STRING-}" ]; then
    QUERY_STRING=page=0
    export QUERY_STRING
fi
LD_LIBRARY_PATH=/home/meteohub/lib:/usr/lib/arm-linux-gnueabihf
LD_BIND_NOW=1
export LD_LIBRARY_PATH LD_BIND_NOW
exec "$@"
'''


def probe_tool():
    spec = importlib.util.spec_from_file_location('probe', Path(__file__).with_name('probe-cgi.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def web_properties(candidate, runtime):
    values = probe_tool().properties(candidate, runtime)
    # This interactive test website runs until stopped/rebooted, unlike the 30s probe.
    return [value for value in values if not value.startswith('RuntimeMaxSec=')]


def write_config(directory):
    (directory / 'lighttpd.conf').write_text(CONFIG)
    (directory / 'cgi-launcher').write_text(LAUNCHER)
    (directory / 'cgi-launcher').chmod(0o700)


def check_paths(candidate, runtime):
    for path in (candidate, runtime):
        if any(c.isspace() or c in ':\\%"\'' for c in str(path)):
            raise ValueError('Paths must not contain whitespace or systemd special characters')
    probe = probe_tool()
    probe.verify(candidate)
    probe.verify_runtime(runtime)
    for relative in ('root/opt', 'root/srv', 'root/srv/www', 'root/srv/www/cgi-bin'):
        path = runtime / relative
        if path.is_symlink() or not path.is_dir():
            raise ValueError('Unexpected runtime directory: ' + relative)


def prepare(candidate, runtime):
    check_paths(candidate, runtime)
    target = runtime / 'root/opt/meteohub-web'
    cgi = runtime / 'root/srv/www/cgi-bin/meteohub.cgi'
    if target.exists() or target.is_symlink() or cgi.exists() or cgi.is_symlink():
        raise ValueError('Web preparation already exists; do not overwrite it')
    if not shutil.which('htpasswd'):
        raise ValueError('Install apache2-utils first')
    os.umask(0o077)
    temporary = Path(tempfile.mkdtemp(prefix='web-prepare-', dir=runtime))
    try:
        write_config(temporary)
        print('Web username: meteohub. Choose a NEW web password at the two prompts.', flush=True)
        print('Do not paste the password into chat. It is not the SSH password.', flush=True)
        subprocess.run(['htpasswd', '-cB', str(temporary / 'users.htpasswd'), 'meteohub'], check=True)
        (temporary / 'users.htpasswd').chmod(0o600)
        (temporary / 'prepared.json').write_text(json.dumps({'schema': 1, 'uid': os.getuid()}) + '\n')
        temporary.rename(target)
        cgi.symlink_to('/home/meteohub/bin/meteohub.cgi')
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    print('PREPARED: private web configuration and password hash; no listener started.')


def start(candidate, runtime):
    check_paths(candidate, runtime)
    web = runtime / 'root/opt/meteohub-web'
    if web.is_symlink() or not web.is_dir():
        raise ValueError('Run prepare first')
    for name in ('users.htpasswd', 'lighttpd.conf', 'cgi-launcher', 'prepared.json'):
        path = web / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Missing/linked web preparation file: ' + name)
    if (web / 'lighttpd.conf').read_text() != CONFIG or (web / 'cgi-launcher').read_text() != LAUNCHER:
        raise ValueError('Web configuration differs from this reviewed tool version')
    if (web / 'users.htpasswd').stat().st_mode & 0o077:
        raise ValueError('Password hash file must be private (chmod 600)')
    cgi = runtime / 'root/srv/www/cgi-bin/meteohub.cgi'
    if not cgi.is_symlink() or os.readlink(cgi) != '/home/meteohub/bin/meteohub.cgi':
        raise ValueError('Unexpected CGI mapping')
    subprocess.run(['sudo', '-v'], check=True)
    for suffix in ('.socket', '.service'):
        status = subprocess.run(['systemctl', 'show', UNIT + suffix, '-p', 'LoadState', '--value'],
                                capture_output=True, text=True, check=False)
        if status.returncode == 0 and status.stdout.strip() != 'not-found':
            raise ValueError('Test unit already loaded; inspect/stop it before starting again')
    # Test CGI isolation using the actual existing operator-owned candidate and runtime.
    isolation = subprocess.run([
        'python3', str(Path(__file__).with_name('probe-cgi.py')), str(candidate),
        '--runtime', str(runtime), '--isolation-only',
    ], check=False)
    if isolation.returncode:
        raise ValueError('Isolation check failed; website not started')
    common = ['sudo', '-n', 'systemd-run', '--uid=' + str(os.getuid()),
              '--gid=' + str(os.getgid()), '--expand-environment=no']
    props = ['--property=' + value for value in web_properties(candidate, runtime)]
    syntax = common + ['--wait', '--pipe', '--collect',
                       '--unit=' + UNIT + '-config-' + str(time.time_ns())] + props
    subprocess.run(syntax + ['/usr/sbin/lighttpd', '-tt', '-f', WEB + '/lighttpd.conf'], check=True)
    os.umask(0o077)
    backup = runtime / ('web-config-before-' + str(time.time_ns()))
    backup.mkdir(mode=0o700)
    shutil.copyfile(runtime / 'root/home/meteohub/meteohub.conf', backup / 'meteohub.conf')
    print('CONFIG BACKUP:', backup, flush=True)
    command = common + [
        '--unit=' + UNIT, '--collect',
        '--socket-property=ListenStream=127.0.0.1:18090',
        '--socket-property=Accept=no', '--socket-property=NoDelay=yes',
    ] + props + ['/usr/sbin/lighttpd', '-D', '-f', WEB + '/lighttpd.conf']
    subprocess.run(command, check=True)
    # No credentials enter this script: only an unauthenticated 401 is expected here.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        try:
            response = opener.open('http://127.0.0.1:18090/cgi-bin/meteohub.cgi', timeout=10)
        except urllib.error.HTTPError as error:
            if error.code != 401:
                raise RuntimeError('Expected HTTP 401, got ' + str(error.code)) from error
            print('PASS: unauthenticated request rejected with HTTP 401')
        else:
            response.close()
            raise RuntimeError('Unauthenticated request was not rejected')
    except Exception:
        subprocess.run(['sudo', '-n', 'systemctl', 'stop', UNIT + '.socket', UNIT + '.service'], check=False)
        raise
    print('READY: http://127.0.0.1:18090/cgi-bin/meteohub.cgi (through SSH forwarding)')
    print('Stop: sudo systemctl stop meteohub-web-test.socket meteohub-web-test.service')
    print('Transient test only: no boot enablement, no logger, no automatic license acceptance.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'start'))
    parser.add_argument('candidate', type=Path)
    parser.add_argument('runtime', type=Path)
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error('Run as the normal login user, not with sudo python3')
    candidate = args.candidate.resolve(strict=True)
    runtime = args.runtime.resolve(strict=True)
    if args.action == 'prepare':
        prepare(candidate, runtime)
    else:
        start(candidate, runtime)


if __name__ == '__main__':
    main()
