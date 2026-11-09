#!/usr/bin/python3
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

spec = importlib.util.spec_from_file_location('identity', Path(__file__).with_name('identity-view.py'))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
ID = dict(hardware='BCM2709', revision='a02082', cpu_serial='0000000012345678',
          sd_serial='0x12345678', sd_name='TEST16', sd_date='01/2017', mac='02:00:00:00:00:02')
ISOLATION = '--isolation' in sys.argv
if ISOLATION: sys.argv.remove('--isolation')


class Tests(unittest.TestCase):
    def test_fields_and_adapter_guard(self):
        m.validate(ID)
        for key in ID:
            with self.assertRaises(ValueError): m.validate(dict(ID, **{key: 'bad;command'}))
        with self.assertRaises(ValueError): m.adapter_view(b'unknown', ID)
        original = 'processor : 0\nHardware : old\nRevision : 0000\nSerial : old\n'
        text = m.cpu_view(original, ID)
        self.assertNotIn('old', text)
        self.assertIn('processor : 0', text)
        self.assertIn('Serial\t: '+ID['cpu_serial'], text)

    @unittest.skipUnless(ISOLATION and os.geteuid()==0, 'requires root --isolation')
    def test_real_service_identity_binds_and_current_ip(self):
        with tempfile.TemporaryDirectory(prefix='identity-view-test-', dir='/var/tmp') as td:
            top=Path(td); top.chmod(0o755)
            root=top/'root'; state=top/'state'; state.mkdir(mode=0o755)
            for directory in ['usr','proc','sys','opt','home/meteohub','data','run','dev','tmp']:
                (root/directory).mkdir(parents=True,exist_ok=True)
            for alias,target in [('bin','usr/bin'),('sbin','usr/sbin'),('lib','usr/lib'),('lib64','usr/lib64')]:
                (root/alias).symlink_to(target)
            home=state/'home'; home.mkdir(); home.chmod(0o700); os.chown(home,65534,65534)
            # Simulated sysfs topology includes the same device-symlink traversal.
            fake_sys=top/'sys'; (fake_sys/'devices/mmc').mkdir(parents=True)
            (fake_sys/'fs/cgroup').mkdir(parents=True)
            (fake_sys/'block/mmcblk0').mkdir(parents=True)
            (fake_sys/'block/mmcblk0/device').symlink_to('../../devices/mmc')
            for key in ['serial','name','date']: (fake_sys/'devices/mmc'/key).write_text('unchanged\n')
            (state/'cpuinfo').write_text(m.cpu_view('processor : 0\n',ID))
            for key in ['serial','name','date']: (state/('sd-'+key)).write_text(ID['sd_'+key]+'\n')
            adapter=Path(__file__).with_name('ifconfig-compat.py').read_bytes()
            (state/'ifconfig').write_text(m.adapter_view(adapter,ID)); (state/'ifconfig').chmod(0o755)
            (state/'check.py').write_text(m.check_source(ID))
            # Create eth0 only in a separate network namespace; no host changes.
            setup='ip link add eth0 type dummy && ip link set eth0 address 02:00:00:00:00:01 && ip address add 192.0.2.50/26 dev eth0 && ip link set eth0 up && echo READY && exec sleep 60'
            net=subprocess.Popen(['unshare','--net','--','/bin/sh','-c',setup],stdout=subprocess.PIPE,text=True)
            try:
                self.assertEqual(net.stdout.readline().strip(),'READY')
                name='meteohub-identity-fixture-'+str(time.time_ns())
                # Unit file exercises the exact same multi-line bind/preflight syntax.
                unit=Path('/run/systemd/system')/(name+'.service')
                base=['[Service]','Type=oneshot','User=65534','Group=65534',
                      'RootDirectory='+str(root),'MountAPIVFS=yes','ProtectSystem=strict',
                      'ProtectKernelTunables=yes','ProtectKernelModules=yes','PrivateDevices=yes',
                      'NoNewPrivileges=yes','CapabilityBoundingSet=',
                      'RestrictAddressFamilies=AF_INET AF_UNIX AF_NETLINK',
                      'NetworkNamespacePath=/proc/'+str(net.pid)+'/ns/net',
                      'BindReadOnlyPaths=/usr:/usr '+str(fake_sys)+':/sys',
                      'BindReadOnlyPaths='+str(state/'ifconfig')+':/usr/sbin/ifconfig',
                      'ExecStart=/sbin/ifconfig eth0']
                unit.write_text('\n'.join(base+m.view_lines(state)[1:])+'\n')
                try:
                    subprocess.run(['systemctl','daemon-reload'],check=True)
                    result=subprocess.run(['systemctl','start',name],text=True,capture_output=True,timeout=20)
                    log=subprocess.check_output(['journalctl','-u',name,'--no-pager','-o','cat'],text=True)
                    self.assertEqual(result.returncode,0,result.stderr+log)
                    self.assertIn('PASS: isolated identity',log)
                    self.assertIn('inet addr:192.0.2.50',log)
                    self.assertIn('HWaddr '+ID['mac'],log)
                finally:
                    subprocess.run(['systemctl','stop',name],capture_output=True)
                    subprocess.run(['systemctl','reset-failed',name],capture_output=True)
                    unit.unlink(); subprocess.run(['systemctl','daemon-reload'],check=True)
                actual=subprocess.check_output(['nsenter','-t',str(net.pid),'-n','--','ip','-j','address','show','eth0'],text=True)
                self.assertIn('02:00:00:00:00:01',actual)
                for key in ['serial','name','date']: self.assertEqual((fake_sys/'devices/mmc'/key).read_text(),'unchanged\n')
            finally:
                net.terminate(); net.wait(timeout=5); net.stdout.close()


if __name__ == '__main__': unittest.main()
