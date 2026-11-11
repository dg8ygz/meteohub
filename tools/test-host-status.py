#!/usr/bin/python3
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

SOURCE = Path(__file__).with_name('host-status-pi50.py').resolve()
spec = importlib.util.spec_from_file_location('host_status', SOURCE)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
ISOLATION = '--isolation' in sys.argv
if ISOLATION: sys.argv.remove('--isolation')


def snapshot(pid, now=100):
    return {'boot_id': m.boot_id(), 'monotonic': now, 'ntp_synchronized': True,
            'services': {name: {'unit': unit, 'pid': pid if name != 'smbd.pid' else -1,
                                'active': name != 'smbd.pid', 'start_ticks': 42}
                         for name, unit in m.SERVICES.items()}}


class Tests(unittest.TestCase):
    def test_expiry_restart_and_invalid_data(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            s = snapshot(123)
            m.publish(p, s)
            self.assertEqual(m.approved_rows(p, now=120),
                             [(123, 'ssh.service'), (123, 'systemd-timesyncd.service')])
            self.assertEqual(m.approved_rows(p, now=131), [])
            self.assertEqual(m.approved_rows(p, now=99), [])
            self.assertEqual(m.approved_rows(p, now=120, boot='other-boot'), [])
            # PID file changes first during a restart: stale snapshot cannot claim it.
            (p / 'dropbear.pid').write_text('124\n')
            self.assertEqual(m.approved_rows(p, now=120), [(123, 'systemd-timesyncd.service')])
            m.publish(p, snapshot(124))
            self.assertEqual(m.approved_rows(p, now=120)[0][0], 124)
            (p / 'status.json').write_text('{broken')
            self.assertEqual(m.approved_rows(p, now=120), [])

    def test_ntp_not_synchronized_and_unit_race(self):
        def properties(unit):
            return {'MainPID': '123', 'ActiveState': 'active'}
        with patch.object(m, 'props', side_effect=properties), \
                patch.object(m, 'process_start', return_value=42), \
                patch.object(m, 'run', return_value='no'):
            s = m.collect()
            self.assertTrue(s['services']['dropbear.pid']['active'])
            self.assertEqual(s['services']['ntpd.pid']['pid'], -1)
        # A process exit/PID change while collecting must not become a live status.
        with patch.object(m, 'props', side_effect=properties), \
                patch.object(m, 'process_start', side_effect=FileNotFoundError), \
                patch.object(m, 'run', return_value='yes'):
            s = m.collect()
            self.assertTrue(all(row['pid'] == -1 for row in s['services'].values()))

    @unittest.skipUnless(ISOLATION and os.geteuid() == 0, 'requires root --isolation')
    def test_collector_under_real_service_restrictions(self):
        with tempfile.TemporaryDirectory(prefix='meteohub-collect-fixture-', dir='/run') as td:
            top = Path(td); top.chmod(0o755)
            source = top/'adapter.py'; source.write_bytes(SOURCE.read_bytes())
            state = top/'state'; state.mkdir()
            code = '''import importlib.util,pathlib,sys
spec=importlib.util.spec_from_file_location('bridge',sys.argv[1])
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
s=m.collect(); m.publish(pathlib.Path(sys.argv[2]),s)
print('PASS: host systemd and timedate queries within collector restrictions')
'''
            cmd = ['systemd-run', '--wait', '--pipe', '--collect',
                   '--unit=meteohub-collect-fixture-'+str(time.time_ns()),
                   '-p', 'User=root', '-p', 'NoNewPrivileges=yes',
                   '-p', 'ProtectSystem=strict', '-p', 'ProtectHome=yes',
                   '-p', 'PrivateTmp=yes', '-p', 'CapabilityBoundingSet=',
                   '-p', 'RestrictAddressFamilies=AF_UNIX', '-p', 'ReadWritePaths='+str(state),
                   '/usr/bin/python3', '-c', code, str(source), str(state)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            print(result.stdout.strip())
            s = json.loads((state/'status.json').read_text())
            self.assertEqual(s['boot_id'], m.boot_id())
            for row in s['services'].values():
                if row['active']:
                    self.assertEqual(m.process_start(row['pid']), row['start_ticks'])

    @unittest.skipUnless(ISOLATION and os.geteuid() == 0, 'requires root --isolation')
    def test_real_private_ps_view_and_stale_snapshot(self):
        # Root processes should remain hidden, except the explicitly bridged PID.
        process = subprocess.Popen(['sleep', '90'])
        unrelated = subprocess.Popen(['sleep', '90'])
        try:
            with tempfile.TemporaryDirectory(prefix='meteohub-status-fixture-', dir='/var/tmp') as td:
                top = Path(td); top.chmod(0o755)
                state = top / 'state'; state.mkdir(mode=0o755)
                root = top / 'root'
                for name in ('usr', 'proc', 'sys', 'dev', 'run', 'opt', 'tmp'):
                    (root/name).mkdir(parents=True, exist_ok=True)
                for name, target in [('bin', 'usr/bin'), ('sbin', 'usr/sbin'),
                                     ('lib', 'usr/lib'), ('lib64', 'usr/lib64')]:
                    (root/name).symlink_to(target)
                adapter = top / 'adapter'; adapter.write_bytes(SOURCE.read_bytes()); adapter.chmod(0o755)
                real = top / 'real-ps'; real.write_bytes(Path('/usr/bin/ps').read_bytes()); real.chmod(0o755)
                for name in m.SERVICES:
                    (root/'run'/name).symlink_to(str(m.VIEW/name))
                (root/'var').mkdir(); (root/'var/run').symlink_to('/run')
                s = snapshot(process.pid, time.monotonic())
                m.publish(state, s)
                program = r'''import os,pathlib,subprocess,sys
pid,other,expected=sys.argv[1:]
def pids(command):
 out=subprocess.check_output(command,text=True)
 return {line.split()[0] for line in out.splitlines() if line.split()}
native=pids(['/opt/meteohub-host-real-ps','ax'])
assert pid not in native and other not in native,native
view=pids(['/bin/ps','ax'])
assert (pid in view)==(expected=='fresh'),view
assert other not in view,view
assert not pathlib.Path('/proc/'+pid).exists()
assert pathlib.Path('/var/run/dropbear.pid').read_text().strip()==pid
assert pathlib.Path('/var/run/smbd.pid').read_text().strip()=='-1'
# Other ps options remain real procps; the adapter must not recurse.
assert str(os.getpid()) in pids(['/bin/ps','-eo','pid='])
print('PASS: '+expected+'; genuine PID bridge, hidden unrelated processes, native ps delegation')
'''
                for expected in ('fresh', 'stale'):
                    if expected == 'stale':
                        s['monotonic'] = time.monotonic() - 31
                        m.publish(state, s)
                    cmd = ['systemd-run', '--wait', '--pipe', '--collect',
                           '--unit=meteohub-status-fixture-'+str(time.time_ns()),
                           '-p', 'User=65534', '-p', 'Group=65534',
                           '-p', 'RootDirectory='+str(root), '-p', 'MountAPIVFS=yes',
                           '-p', 'ProtectProc=invisible', '-p', 'ProcSubset=all',
                           '-p', 'ProtectSystem=strict', '-p', 'NoNewPrivileges=yes',
                           '-p', 'CapabilityBoundingSet=', '-p', 'PrivateDevices=yes',
                           '-p', 'BindPaths='+str(root/'run')+':/run',
                           '-p', 'BindReadOnlyPaths=/usr:/usr',
                           '-p', f'BindReadOnlyPaths={adapter}:/usr/bin/ps {real}:{m.REAL_PS} {state}:{m.VIEW}',
                           '/usr/bin/python3', '-c', program, str(process.pid), str(unrelated.pid), expected]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                    print(result.stdout.strip())
                self.assertIsNone(process.poll())
                self.assertIsNone(unrelated.poll())
        finally:
            process.terminate(); process.wait()
            unrelated.terminate(); unrelated.wait()


if __name__ == '__main__': unittest.main()
