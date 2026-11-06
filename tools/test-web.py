#!/usr/bin/env python3
"""Real lighttpd/socket/isolation checks with synthetic CGI only; run as root."""
import argparse
import base64
import importlib.util
import json
from unittest.mock import patch
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lighttpd', type=Path, default=Path('/usr/sbin/lighttpd'))
    parser.add_argument('--modules', type=Path, default=Path('/usr/lib/lighttpd'))
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('This optional integration test needs root for transient systemd units')
    web = load('web-test')
    fixture = load('test-runtime')
    case = fixture.RuntimeTests('test_selected_resources_and_existing_destination')
    case.setUp()
    unit = 'meteohub-http-check-' + str(time.time_ns())
    try:
        fixture.stage.materialize(case.runtime, fixture.stage.prepare(case.image), 65534, 65534, 'nobody')
        candidate = case.top / 'candidate'
        (candidate / 'bin').mkdir(parents=True)
        (candidate / 'lib').mkdir()
        (candidate / 'bin/loggerd').write_text('not executed')
        cgi = candidate / 'bin/meteohub.cgi'
        cgi.write_text('''#!/bin/sh
printf 'Content-Type: text/plain\\r\\n\\r\\n'
printf 'QUERY=%s\\nMETHOD=%s\\n' "${QUERY_STRING-}" "${REQUEST_METHOD-}"
if [ "${REQUEST_METHOD-}" = POST ]; then cat; fi
exit 1
''')
        cgi.chmod(0o700)
        root = case.runtime / 'root'
        (root / 'srv/www/cgi-bin/meteohub.cgi').symlink_to('/home/meteohub/bin/meteohub.cgi')
        (root / 'srv/www/cgi-bin/other.cgi').write_text('SHOULD_NOT_LEAK')
        config = root / 'opt/meteohub-web'
        config.mkdir()
        web.write_config(config)
        extension = load('extension-update')
        extension.UNIT = unit + '-index.service'
        extension.update(candidate, case.runtime, services=False)
        # Refresh the derived index in the real private namespace as the web user.
        # Synthetic data only; source archives and receiver are absent.
        data_dir = root / 'data/tcp-feed/state'
        data_dir.mkdir(parents=True)
        stamp = time.strftime('%Y%m%d%H%M%S', time.gmtime())
        (data_dir / 'provenance.jsonl').write_text(json.dumps({
            'source': stamp + ' thb0 1289 100 9839',
            'source_format': 'plugin', 'pressure_only': True}) + '\n')
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            port = reservation.getsockname()[1]
        (config / 'lighttpd.conf').write_text(web.CONFIG.replace('18090', str(port)))
        password = secrets.token_urlsafe(24)
        subprocess.run(['htpasswd', '-ciB', str(config / 'users.htpasswd'), 'meteohub'],
                       input=password + '\n', text=True, capture_output=True, check=True)
        (config / 'users.htpasswd').chmod(0o600)
        for parent, _, files in os.walk(case.top):
            os.chown(parent, 65534, 65534)
            for name in files:
                os.chown(Path(parent) / name, 65534, 65534, follow_symlinks=False)
        with patch.object(extension.os, 'getuid', return_value=65534), patch.object(extension.os, 'getgid', return_value=65534):
            command = extension.index_command(candidate, case.runtime, once=True)
        subprocess.run(command, check=True, capture_output=True, timeout=45)
        with patch.object(extension.os, 'getuid', return_value=65534), patch.object(extension.os, 'getgid', return_value=65534):
            extension.start_index(candidate, case.runtime)
            assert extension.service_state(case.runtime)
            extension.stop_service(case.runtime)
            extension.start_index(candidate, case.runtime)
        index_status = json.loads((root / 'data/dashboard/status.json').read_text())
        assert not index_status.get('error'), index_status
        props = web.web_properties(candidate, case.runtime)
        props += [
            'RuntimeMaxSec=45s',
            'BindReadOnlyPaths=' + str(args.lighttpd.resolve()) + ':/opt/test-lighttpd '
            + str(args.modules.resolve()) + ':/opt/test-modules',
        ]
        common = ['systemd-run', '--uid=65534', '--gid=65534', '--collect', '--expand-environment=no']
        common += ['--property=' + value for value in props]
        binary = ['/opt/test-lighttpd', '-m', '/opt/test-modules', '-f', '/opt/meteohub-web/lighttpd.conf']
        result = subprocess.run(common + ['--wait', '--pipe'] + binary + ['-tt'],
                                text=True, capture_output=True, timeout=20)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        command = common + ['--unit=' + unit,
                            '--socket-property=ListenStream=127.0.0.1:' + str(port),
                            '--socket-property=Accept=no'] + binary + ['-D']
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=20)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        def request(path, auth=None, data=None):
            req = urllib.request.Request('http://127.0.0.1:' + str(port) + path, data=data)
            if auth is not None:
                req.add_header('Authorization', 'Basic ' + base64.b64encode(('meteohub:' + auth).encode()).decode())
            try:
                response = opener.open(req, timeout=10)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                return response.code, response.read()
        assert request('/cgi-bin/meteohub.cgi')[0] == 401
        assert request('/cgi-bin/meteohub.cgi', 'wrong-password')[0] == 401
        status, body = request('/cgi-bin/meteohub.cgi', password)
        assert status == 200 and b'QUERY=page=0' in body and b'METHOD=GET' in body, (status, body)
        status, body = request('/cgi-bin/meteohub.cgi?page=17', password)
        assert status == 200 and b'QUERY=page=17' in body, (status, body)
        status, body = request('/cgi-bin/meteohub.cgi', password, b'probe=hello')
        assert status == 200 and b'METHOD=POST' in body and b'probe=hello' in body, (status, body)
        assert request('/cgi-bin/admin.html', password) == (200, b'test fixture\n')
        for path in ('/cgi-bin/other.cgi', '/etc/resolv.conf', '/opt/meteohub-web/users.htpasswd',
                     '/%2e%2e/opt/meteohub-web/users.htpasswd'):
            status, body = request(path, password)
            assert status in (400, 403, 404, 500), (path, status)
            assert b'SHOULD_NOT_LEAK' not in body and b'meteohub:$2' not in body
        for path in ('/dashboard/', '/cgi-bin/weather-api.cgi', '/cgi-bin/weather-image.cgi'):
            assert request(path)[0] == 401, path
            status, body = request(path, password)
            assert status == 200, (path, status, body[:200])
            if path.endswith('weather-api.cgi'):
                payload = json.loads(body)
                assert any(m['field'] == 'pressure' for m in payload['metrics']), payload
                assert not any(m['sensor'] == 'thb0' and m['field'] in ('temperature','humidity') for m in payload['metrics'])
            elif path.endswith('weather-image.cgi'):
                assert b'<svg' in body and b'983,9' in body, body[:200]
            else:
                assert b'weather.js' in body
        for path in ('/dashboard/weather.js', '/dashboard/weather.css'):
            assert request(path, password)[0] == 200
        assert request('/cgi-bin/weather-image.cgi', password, b'invalid=post')[0] == 405
        print('PASS: dashboard/API/SVG authentication, real pressure-only index, assets and method restriction')
        print('PASS: 10 real HTTP cases; authentication, GET/POST, static files, CGI exit 1, private paths')
        print('PASS: inherited loopback socket served by lighttpd in the private runtime/network')
    finally:
        subprocess.run(['systemctl', 'stop', unit + '.socket', unit + '.service', unit + '-index.service'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=10)
        case.doCleanups()


if __name__ == '__main__':
    main()
