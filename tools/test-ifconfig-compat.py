#!/usr/bin/python3
"""Legacy query compatibility; optional real isolated network/bind mount test."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).with_name('ifconfig-compat.py').resolve()
spec = importlib.util.spec_from_file_location('ifconfig_compat', SCRIPT)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
ISOLATION = '--isolation' in sys.argv
if ISOLATION: sys.argv.remove('--isolation')


class DisplayTests(unittest.TestCase):
    @unittest.skipUnless(ISOLATION and os.geteuid() == 0, 'requires root --isolation')
    def test_service_netlink_policy(self):
        with tempfile.TemporaryDirectory(prefix='meteohub-netlink-test-') as td:
            Path(td).chmod(0o755)
            source = Path(td) / 'adapter'; source.write_bytes(SCRIPT.read_bytes()); source.chmod(0o755)
            harness = '''import subprocess,sys
adapter,expected=sys.argv[1:]
r=subprocess.run([adapter,'-a'],capture_output=True,text=True)
if expected=='denied':
 assert r.returncode != 0, r.stdout
 print('PASS: service address-family filter blocks adapter despite namespace access')
else:
 assert r.returncode == 0 and 'Local Loopback' in r.stdout, (r.stdout,r.stderr)
 r=subprocess.run(['/usr/sbin/ip','link','add','forbidden0','type','dummy'],capture_output=True,text=True)
 assert r.returncode != 0 and 'Operation not permitted' in r.stderr, (r.stdout,r.stderr)
 print('PASS: netlink read allowed; network administration denied in private test namespace')
'''
            for expected, families in [('denied', 'AF_INET AF_UNIX'), ('allowed', 'AF_INET AF_UNIX AF_NETLINK')]:
                cmd = ['systemd-run','--wait','--pipe','--collect',
                       '--unit=meteohub-netlink-test-' + str(time.time_ns()),
                       '-p','User=65534','-p','Group=65534','-p','PrivateNetwork=yes',
                       '-p','NoNewPrivileges=yes','-p','CapabilityBoundingSet=',
                       '-p','RestrictAddressFamilies=' + families,
                       sys.executable,'-c',harness,str(source),expected]
                result = subprocess.run(cmd,text=True,capture_output=True,timeout=20)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_addresses_labels_and_down_interfaces(self):
        rows = [dict(ifname='sample0', flags=['UP', 'LOWER_UP', 'BROADCAST'], mtu=1500,
                     link_type='ether', address='02:00:00:00:00:01', addr_info=[
                         dict(family='inet', local='192.0.2.50', prefixlen=26, broadcast='192.0.2.63', label='sample0'),
                         dict(family='inet', local='192.0.2.77', prefixlen=24, label='sample0:0'),
                         dict(family='inet6', local='fe80::1', prefixlen=64, scope='link')]),
                dict(ifname='down0', flags=['BROADCAST'], mtu=1500, link_type='ether',
                     address='02:00:00:00:00:02', addr_info=[])]
        text = m.render(rows, 'sample0', True)
        self.assertIn('HWaddr 02:00:00:00:00:01', text)
        self.assertIn('inet addr:192.0.2.50  Bcast:192.0.2.63  Mask:255.255.255.192', text)
        self.assertNotIn('192.0.2.77', text)
        self.assertIn('inet6 addr: fe80::1/64  Scope:Link', text)
        self.assertIn('192.0.2.77', m.render(rows, 'sample0:0', True))
        self.assertNotIn('down0', m.render(rows))
        self.assertIn('down0', m.render(rows, all_interfaces=True))
        self.assertNotIn('inet addr:', m.render(rows, 'down0', True))
        with self.assertRaises(ValueError): m.render(rows, 'absent0', True)

    def test_mutation_arguments_rejected_before_subprocess(self):
        with patch.object(m.subprocess, 'run') as run:
            for args in (['eth0','down'], ['eth0','up'], ['eth0','192.0.2.1'],
                         ['netmask','255.255.255.0'], ['-a','up'], ['--help'], ['eth0;true']):
                with self.assertRaises(ValueError): m.main(args)
            run.assert_not_called()

    @unittest.skipUnless(ISOLATION and os.geteuid() == 0, 'requires root --isolation')
    def test_real_network_and_private_bind(self):
        # New network and mount namespaces: no host link/address changes.
        with tempfile.TemporaryDirectory(prefix='meteohub-ifconfig-test-') as td:
            target = Path(td) / 'ifconfig'; target.write_text('host file remains unchanged\n')
            harness = r'''
import json, os, pathlib, subprocess, sys
script,target=sys.argv[1:]
def run(*args): return subprocess.run(args, check=True, text=True, capture_output=True)
run('ip','link','add','test0','type','dummy')
run('ip','link','set','test0','address','02:00:00:00:00:01')
run('ip','address','add','192.0.2.50/26','broadcast','192.0.2.63','dev','test0')
run('ip','link','set','test0','up')
before=json.loads(run('ip','-j','address','show').stdout)
blocked_dir=pathlib.Path(target).parent/'noexec-source'; blocked_dir.mkdir()
run('mount','-t','tmpfs','-o','noexec,nosuid,nodev,mode=755','tmpfs',str(blocked_dir))
blocked=blocked_dir/'adapter'; blocked.write_bytes(pathlib.Path(script).read_bytes()); blocked.chmod(0o755)
run('mount','--bind',str(blocked),target)
run('mount','-o','remount,bind,ro',target)
cmd=['setpriv','--reuid=65534','--regid=65534','--clear-groups',sys.executable,target]
direct=['setpriv','--reuid=65534','--regid=65534','--clear-groups',target]
assert subprocess.run(direct+['test0'],capture_output=True).returncode != 0
# Explicit interpreter hid this failure in the original test. Exercise both.
text=run(*cmd,'test0').stdout
run('umount',target)
run('mount','--bind',script,target)
run('mount','-o','remount,bind,ro',target)
assert run(*direct,'test0').stdout == text
assert 'HWaddr 02:00:00:00:00:01' in text, text
assert 'inet addr:192.0.2.50  Bcast:192.0.2.63  Mask:255.255.255.192' in text, text
assert subprocess.run(cmd+['test0','down'],capture_output=True).returncode != 0
after=json.loads(run('ip','-j','address','show').stdout)
assert before == after, (before,after)
run('umount',target)
assert pathlib.Path(target).read_text() == 'host file remains unchanged\n'
print('PASS: real netlink query as unprivileged user, private read-only bind, host file preserved')
'''
            # Make only the copied source traversable to the unprivileged fixture.
            source = Path(td) / 'adapter.py'; source.write_bytes(SCRIPT.read_bytes()); source.chmod(0o755)
            Path(td).chmod(0o755)
            result = subprocess.run(['unshare','--mount','--net','--propagation','private',
                                     sys.executable,'-c',harness,str(source),str(target)],
                                    text=True,capture_output=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(target.read_text(),'host file remains unchanged\n')


if __name__ == '__main__': unittest.main()
