#!/usr/bin/env python3
"""Run the prepared CGI once in a transient systemd sandbox, without a webserver."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time


class PageText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.parts.append(data.strip())


def properties(candidate, runtime=None):
    result = [
        'Type=exec', 'RuntimeMaxSec=30s', 'TimeoutStopSec=3s',
        'KillMode=control-group', 'MemoryMax=128M', 'TasksMax=32',
        'CPUQuota=50%', 'LimitCORE=0', 'LimitFSIZE=2M', 'UMask=0077',
        'NoNewPrivileges=yes', 'CapabilityBoundingSet=',
        'PrivateNetwork=yes', 'PrivateDevices=yes', 'PrivateTmp=yes',
        'ProtectSystem=strict', 'ProtectHome=tmpfs',
        'ProtectKernelTunables=yes', 'ProtectKernelModules=yes',
        'ProtectKernelLogs=yes', 'ProtectControlGroups=yes',
        'ProtectProc=invisible', 'ProcSubset=pid',
        'RestrictSUIDSGID=yes', 'RestrictNamespaces=yes',
        'InaccessiblePaths=-/mnt -/media -/srv',
        'TemporaryFileSystem=/run:ro',
        'BindReadOnlyPaths=' + str(candidate) + ':/home/meteohub',
        'WorkingDirectory=/home/meteohub',
    ]
    if runtime is not None:
        result = [value for value in result if value.split('=', 1)[0] not in
                  ('ProtectHome', 'InaccessiblePaths', 'BindReadOnlyPaths', 'ProcSubset')]
        result += [
            'RootDirectory=' + str(runtime / 'root'), 'MountAPIVFS=yes',
            'ReadWritePaths=+/home/meteohub +/data',
            'BindReadOnlyPaths=/usr:/usr -/etc/ssl:/etc/ssl '
            + str(candidate / 'bin') + ':/home/meteohub/bin '
            + str(candidate / 'lib') + ':/home/meteohub/lib',
        ]
    return result


def verify_runtime(runtime):
    manifest = json.loads((runtime / 'runtime-manifest.json').read_text())
    if manifest.get('schema') != 1 or manifest.get('uid') != os.getuid():
        raise ValueError('Runtime must be created by this login user')
    for name in ('root', 'root/usr', 'root/etc', 'root/etc/ssl', 'root/home',
                 'root/home/meteohub', 'root/home/meteohub/bin',
                 'root/home/meteohub/lib', 'root/data'):
        path = runtime / name
        if path.is_symlink() or not path.is_dir():
            raise ValueError('Unexpected runtime mount directory: ' + name)
    config = runtime / 'root/home/meteohub/meteohub.conf'
    if config.is_symlink() or not config.is_file():
        raise ValueError('Unexpected runtime application configuration')


def verify(candidate):
    manifest = json.loads((candidate / 'manifest.json').read_text())
    expected = {'bin/loggerd', 'bin/meteometar', 'bin/meteonet',
                'bin/meteoschedule', 'bin/meteohub.cgi', 'lib/libgcgi.so.0'}
    entries = manifest['files']
    if len(entries) != len(expected) or {item['target'] for item in entries} != expected:
        raise ValueError('Unexpected candidate manifest file list')
    for item in entries:
        path = candidate / item['target']
        if path.is_symlink() or not path.resolve().is_relative_to(candidate):
            raise ValueError('Candidate link outside the private directory')
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['candidate_sha256']:
            raise ValueError('Candidate hash mismatch: ' + item['target'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--runtime', type=Path, help='Private test root from stage-runtime.py')
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error('Run as the normal login user; sudo is used only for systemd-run')
    candidate = args.candidate.resolve(strict=True)
    runtime = args.runtime.resolve(strict=True) if args.runtime else None
    # systemd path-list syntax has separators/expansions; do not interpolate them.
    if any(c.isspace() or c in ':\\%"\'' for c in str(candidate) + str(runtime or '')):
        parser.error('Use a candidate path without whitespace or systemd special characters')
    verify(candidate)
    if runtime is not None:
        verify_runtime(runtime)
    subprocess.run(['sudo', '-v'], check=True)
    os.umask(0o077)
    report = Path(tempfile.mkdtemp(prefix='cgi-probe-', dir=candidate.parent))
    if runtime is not None:
        # Preserve the mutable application config before each GET probe.
        (report / 'meteohub.conf.before').write_bytes(
            (runtime / 'root/home/meteohub/meteohub.conf').read_bytes())
    unit = 'meteohub-cgi-probe-' + str(time.time_ns())
    command = [
        'sudo', '-n', 'systemd-run', '--wait', '--pipe', '--collect',
        '--unit=' + unit, '--uid=' + str(os.getuid()), '--gid=' + str(os.getgid()),
        '--expand-environment=no',
    ]
    for value in properties(candidate, runtime):
        command += ['--property=' + value]
    command += [
        '/usr/bin/env', '-i', 'PATH=/usr/bin:/bin', 'HOME=/home/meteohub',
        'LANG=C', 'LD_BIND_NOW=1',
        'LD_LIBRARY_PATH=/home/meteohub/lib:/usr/lib/arm-linux-gnueabihf',
        'GATEWAY_INTERFACE=CGI/1.1', 'SERVER_PROTOCOL=HTTP/1.1',
        'SERVER_NAME=localhost', 'SERVER_PORT=80', 'REMOTE_ADDR=127.0.0.1',
        'REQUEST_METHOD=GET', 'QUERY_STRING=page=0',
        'SCRIPT_NAME=/cgi-bin/meteohub.cgi', 'DOCUMENT_ROOT=/srv/www',
    ]
    print('REPORT:', report, flush=True)
    print('One CGI request, no network/USB access, no actual home access; 30s limit.', flush=True)
    # Exercise the same isolation before allowing the proprietary executable.
    check = '''import errno, os, socket
assert os.geteuid() != 0
assert os.getcwd() == "/home/meteohub"
assert sorted(os.listdir("/home")) == ["meteohub"]
assert not os.path.exists("/run/systemd/private")
assert not os.path.exists("/run/dbus/system_bus_socket")
assert not any(n.startswith(("ttyUSB", "video")) for n in os.listdir("/dev"))
try: fd = os.open("bin/loggerd", os.O_WRONLY | os.O_APPEND)
except OSError as e: assert e.errno == errno.EROFS, e
else:
    os.close(fd)
    raise AssertionError("candidate writable")
s = socket.socket(); s.settimeout(1)
try: s.connect(("192.0.2.1", 80))
except OSError as e: assert e.errno in (errno.ENETUNREACH, errno.EHOSTUNREACH), e
else: raise AssertionError("outbound route exists")
print("PASS: unprivileged; private home/run; read-only candidate; no USB or outbound route")
'''
    if runtime is not None:
        check += '''import tempfile
for folder in ("/home/meteohub", "/data"):
    fd, name = tempfile.mkstemp(prefix="isolation-check-", dir=folder)
    os.write(fd, b"private write test")
    os.close(fd)
    os.unlink(name)
try: fd = os.open("/etc/network/interfaces", os.O_WRONLY | os.O_APPEND)
except OSError as e: assert e.errno == errno.EROFS, e
else:
    os.close(fd)
    raise AssertionError("network fixture writable")
assert os.path.isfile("/opt/etc/ntp/ntp.conf")
assert os.path.isdir("/opt/share/zoneinfo-posix")
assert os.path.isfile("/home/meteohub/meteohub-license-5.txt")
assert os.path.isfile("/etc/resolv.conf")
routes = open("/proc/net/route").read().splitlines()
assert routes and routes[0].startswith("Iface")
assert len(routes) == 1, "unexpected routes in isolated test namespace"
print("PASS: private config/data writable; system fixtures read-only; resources present")
print("PASS: resolver file present; isolated routing table readable and empty")
'''
    preflight = [('--unit=' + unit + '-check') if arg == '--unit=' + unit else arg
                 for arg in command]
    with (report / 'isolation.txt').open('wb') as stream:
        checked = subprocess.run(preflight + ['/usr/bin/python3', '-c', check],
                                 stdin=subprocess.DEVNULL, stdout=stream, stderr=stream,
                                 timeout=50)
    print((report / 'isolation.txt').read_text(errors='replace')[:6000], flush=True)
    if checked.returncode:
        print('STOP: isolation check failed; CGI NOT started.')
        return checked.returncode
    command += ['/home/meteohub/bin/meteohub.cgi']
    with (report / 'response.txt').open('wb') as stdout, (report / 'stderr.txt').open('wb') as stderr:
        try:
            result = subprocess.run(command, stdin=subprocess.DEVNULL,
                                    stdout=stdout, stderr=stderr, timeout=50)
            code = result.returncode
        except subprocess.TimeoutExpired:
            subprocess.run(['sudo', '-n', 'systemctl', 'stop', unit + '.service'],
                           stdout=stderr, stderr=stderr, timeout=10, check=False)
            code = 124
    (report / 'result.json').write_text(json.dumps({
        'unit': unit, 'systemd_run_exit': code,
        'status': 'CGI smoke test only; functionality and activation not accepted',
        'properties': properties(candidate, runtime),
    }, indent=2) + '\n')
    print('SYSTEMD_RUN_EXIT:', code)
    print('RESPONSE_BYTES:', (report / 'response.txt').stat().st_size)
    print('--- launcher / CGI stderr (first 6000 characters) ---')
    print((report / 'stderr.txt').read_text(errors='replace')[:6000])
    response = (report / 'response.txt').read_text(errors='replace')
    print('--- CGI response beginning (first 500 characters) ---')
    print(response[:500])
    page = PageText()
    page.feed(response)
    print('--- page text without script/style (first 3000 characters) ---')
    print('\n'.join(page.parts)[:3000])
    print('Full response remains private in the report directory.')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
