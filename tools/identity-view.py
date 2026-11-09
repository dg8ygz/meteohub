#!/usr/bin/python3
"""Temporary application-only identity view; web only, separate configuration.

Run as root on the target overlay host. Never changes host identifiers or
license instructions/keys. Existing logger and its configuration stay intact.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

EMBEDDED_IDENTITY = None
RUNTIME = Path('/home/meteohub/meteohub-staging/5.1e-runtime')
WEB = 'meteohub-web-test.service'
LOGGER = 'meteohub-live-logger.service'
DROPINS = Path('/run/systemd/system') / (WEB + '.d')
ADAPTER = Path('/usr/local/libexec/meteohub-ifconfig-compat.py')
ADAPTER_SHA = '96c9141c154e406977a2a3b4f8a74c6258f4c554435d7cd665fbd128b79b824f'


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def prop(unit, name):
    return run('systemctl', 'show', unit, '-p', name, '--value')


def validate(identity):
    patterns = {'hardware': r'[A-Za-z0-9_-]{1,32}', 'revision': r'[0-9a-fA-F]{4,16}',
                'cpu_serial': r'[0-9a-fA-F]{16}', 'sd_serial': r'0x[0-9a-fA-F]{8}',
                'sd_name': r'[A-Za-z0-9_-]{1,16}', 'sd_date': r'(0[1-9]|1[0-2])/[0-9]{4}',
                'mac': r'(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}'}
    if not isinstance(identity, dict) or set(identity) != set(patterns):
        raise ValueError('Incomplete or unknown identity fields')
    for key, pattern in patterns.items():
        if not isinstance(identity[key], str) or not re.fullmatch(pattern, identity[key]):
            raise ValueError('Invalid identity field: ' + key)
    if int(identity['mac'][:2], 16) & 1:
        raise ValueError('Multicast MAC refused')


def cpu_view(original, identity):
    lines = [line for line in original.splitlines()
             if line.split(':', 1)[0].strip() not in ('Hardware', 'Revision', 'Serial')]
    for key, value in [('Hardware', identity['hardware']), ('Revision', identity['revision']),
                       ('Serial', identity['cpu_serial'])]:
        lines.append(key + '\t: ' + value)
    return '\n'.join(lines) + '\n'


def adapter_view(original, identity):
    if hashlib.sha256(original).hexdigest() != ADAPTER_SHA:
        raise ValueError('Unknown base display adapter; no changes made')
    text = original.decode()
    old = "mac = row['address']"
    if text.count(old) != 1:
        raise ValueError('Unexpected adapter source')
    return text.replace(old, 'mac = ' + repr(identity['mac'].lower()) +
                        " if name == 'eth0' else row['address']")


def atomic(path, data, mode=0o644):
    fd, name = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def check_source(identity):
    return '''import pathlib,subprocess
p=pathlib.Path
identity=IDENTITY
text=p('/proc/cpuinfo').read_text()
for k,v in [('Hardware',identity['hardware']),('Revision',identity['revision']),('Serial',identity['cpu_serial'])]:
 assert k+'\\t: '+v in text
for k in ['serial','name','date']:
 assert p('/sys/block/mmcblk0/device/'+k).read_text().strip()==identity['sd_'+k]
r=subprocess.run(['/sbin/ifconfig','eth0'],check=True,text=True,capture_output=True)
assert 'HWaddr '+identity['mac'].lower() in r.stdout
assert 'inet addr:' in r.stdout
print('PASS: isolated identity and current IP available under actual web service restrictions')
'''.replace('IDENTITY', repr(identity))


def view_lines(state):
    home = state / 'home'
    lines = ['[Service]', 'BindPaths=' + str(home) + ':/home/meteohub',
             'BindReadOnlyPaths=' + str(state / 'cpuinfo') + ':/proc/cpuinfo']
    for key in ('serial', 'name', 'date'):
        lines.append('BindReadOnlyPaths=' + str(state / ('sd-' + key)) + ':/sys/block/mmcblk0/device/' + key)
    lines += ['BindReadOnlyPaths=' + str(state / 'check.py') + ':/opt/meteohub-identity-check.py',
              'ExecStartPre=/usr/bin/python3 /opt/meteohub-identity-check.py']
    return lines


def apply(identity):
    validate(identity)
    if os.geteuid() != 0: raise ValueError('Run as root on the target Pi')
    if run('findmnt', '-nro', 'FSTYPE', '--mountpoint', '/') != 'overlay':
        raise ValueError('This temporary installer requires the active RAM root overlay')
    if run('findmnt', '-nro', 'UUID', '--mountpoint', '/media/root-ro') != '15f4c6be-1102-4331-9904-f78e78afd1fd':
        raise ValueError('Unexpected target root filesystem')
    if prop(WEB, 'RootDirectory') != str(RUNTIME / 'root'):
        raise ValueError('Unexpected web RootDirectory')
    if prop(WEB, 'ActiveState') != 'active' or prop(LOGGER, 'ActiveState') != 'active':
        raise ValueError('Expected running web and logger')
    if 'AF_NETLINK' not in prop(WEB, 'RestrictAddressFamilies').split():
        raise ValueError('Web service still blocks the adapter netlink query')
    if prop(WEB, 'ExecStartPre'):
        raise ValueError('Unexpected existing web start preflight')
    pid_before = prop(LOGGER, 'MainPID')
    root = RUNTIME / 'root'
    uid = (root / 'home/meteohub/meteohub.conf').stat().st_uid
    gid = (root / 'home/meteohub/meteohub.conf').stat().st_gid
    if uid == 0: raise ValueError('Expected an unprivileged application owner')
    mount_conf = DROPINS / '40-ifconfig-compat.conf'
    view_conf = DROPINS / '50-identity-view.conf'
    if view_conf.exists() or view_conf.is_symlink() or mount_conf.is_symlink():
        raise ValueError('Existing identity view or unexpected mount drop-in')
    before = mount_conf.read_bytes()
    old_binding = ('BindReadOnlyPaths=' + str(ADAPTER) + ':/usr/sbin/ifconfig').encode()
    if before.splitlines().count(old_binding) != 1:
        raise ValueError('Unexpected existing adapter binding')
    original_adapter = ADAPTER.read_bytes()
    modified_adapter = adapter_view(original_adapter, identity)
    host_mac = Path('/sys/class/net/eth0/address').read_text()
    host_sd = {key: Path('/sys/block/mmcblk0/device/' + key).read_text()
               for key in ('serial', 'name', 'date')}

    state = Path(tempfile.mkdtemp(prefix='meteohub-identity-', dir='/usr/local/libexec'))
    os.chmod(state, 0o755)
    print('TEST COPY / ROLLBACK:', state, flush=True)
    (state / '40-before.conf').write_bytes(before)
    (state / '40-before.conf').chmod(0o600)
    # The checkpoint lock held by main prevents runtime rebase during this copy.
    original_config = (root / 'home/meteohub/meteohub.conf').read_bytes()
    home = state / 'home'
    shutil.copytree(root / 'home/meteohub', home, symlinks=True)
    if (root / 'home/meteohub/meteohub.conf').read_bytes() != original_config:
        raise ValueError('Configuration changed during copy; services untouched')
    for parent, dirs, files in os.walk(home, followlinks=False):
        os.chown(parent, uid, gid)
        for name in dirs + files: os.chown(Path(parent) / name, uid, gid, follow_symlinks=False)
    home.chmod(0o700)
    values = {'cpuinfo': cpu_view(Path('/proc/cpuinfo').read_text(), identity),
              'sd-serial': identity['sd_serial'] + '\n', 'sd-name': identity['sd_name'] + '\n',
              'sd-date': identity['sd_date'] + '\n', 'ifconfig': modified_adapter}
    for name, text in values.items():
        atomic(state / name, text.encode(), 0o755 if name == 'ifconfig' else 0o644)
    atomic(state / 'check.py', check_source(identity).encode())
    lines = view_lines(state)
    rollback = '#!/bin/sh\nset -eu\ncp ' + str(state / '40-before.conf') + ' ' + str(mount_conf) + '\nrm -f ' + str(view_conf) + '\nsystemctl daemon-reload\nsystemctl restart ' + WEB + '\n'
    atomic(state / 'rollback.sh', rollback.encode(), 0o700)
    try:
        atomic(view_conf, ('\n'.join(lines) + '\n').encode())
        atomic(mount_conf, before.replace(old_binding, ('BindReadOnlyPaths=' + str(state / 'ifconfig') + ':/usr/sbin/ifconfig').encode()))
        run('systemctl', 'daemon-reload')
        run('systemctl', 'restart', WEB)
        if prop(WEB, 'ActiveState') != 'active': raise ValueError('Web did not start')
        if prop(LOGGER, 'MainPID') != pid_before: raise ValueError('Logger PID changed concurrently')
        if Path('/sys/class/net/eth0/address').read_text() != host_mac: raise ValueError('Host MAC changed')
        for key, value in host_sd.items():
            if Path('/sys/block/mmcblk0/device/' + key).read_text() != value:
                raise ValueError('Host SD identity changed')
        if (root / 'home/meteohub/meteohub.conf').read_bytes() != original_config:
            raise ValueError('Original config changed concurrently')
    except BaseException:
        atomic(mount_conf, before)
        view_conf.unlink(missing_ok=True)
        run('systemctl', 'daemon-reload'); run('systemctl', 'restart', WEB)
        print('ROLLED BACK: original web view restored; evidence retained at', state, flush=True)
        raise
    print('PASS: web identity view active; original host MAC/SD and logger PID unchanged')
    print('Private web configuration:', home)
    print('Temporary until reboot. No activation code imported or generated.')
    print('Rollback: bash', state / 'rollback.sh')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--identity', type=Path)
    args = parser.parse_args()
    identity = json.loads(args.identity.read_text()) if args.identity else EMBEDDED_IDENTITY
    os.umask(0o077)
    with open('/run/lock/meteohub-storage.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        apply(identity)
