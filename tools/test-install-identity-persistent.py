#!/usr/bin/python3
"""Real systemd fixture for shared identity/configuration installation and rollback."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(file))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


p = load('persistent_identity', 'install-identity-persistent.py')
m = load('ram', 'ram-storage.py')
v = load('identity_view', 'identity-view.py')
ISOLATION = '--isolation' in sys.argv
if ISOLATION: sys.argv.remove('--isolation')
ID = dict(hardware='BCM2709', revision='a02082', cpu_serial='0000000012345678',
          sd_serial='0x12345678', sd_name='TEST16', sd_date='01/2017', mac='02:00:00:00:00:02')


class Tests(unittest.TestCase):
    def test_maintenance_changes_only_known_boot_option(self):
        before = b'console=tty1 overlayroot=tmpfs:recurse=0 root=PARTUUID=fixture rootwait\n'
        self.assertEqual(p.maintenance_cmdline(before),
                         b'console=tty1 overlayroot=disabled root=PARTUUID=fixture rootwait\n')
        for value in (b'rootwait', b'overlayroot=tmpfs', before + b' overlayroot=disabled'):
            with self.assertRaises(ValueError): p.maintenance_cmdline(value)

    def test_merge_only_confirmed_field(self):
        before = bytes(65536); activated = bytearray(before); activated[p.FIELD] = b'A' * 32
        current = bytearray(before); current[100] = 17
        merged = p.merge_activation(current, before, activated)
        self.assertEqual(merged[100], 17)
        self.assertEqual(merged[p.FIELD], b'A' * 32)
        self.assertEqual(p.merge_activation(merged, before, activated), merged)
        changed = bytearray(activated); changed[300] = 8
        with self.assertRaises(ValueError): p.merge_activation(current, before, changed)
        current[p.FIELD] = b'B' * 32
        with self.assertRaises(ValueError): p.merge_activation(current, before, activated)
        with self.assertRaises(ValueError): p.merge_activation(b'', before, activated)

    @unittest.skipUnless(ISOLATION and os.geteuid() == 0, 'requires root --isolation')
    def test_real_services_share_configuration_and_failed_start_rolls_back(self):
        with tempfile.TemporaryDirectory(prefix='identity-permanent-test-', dir='/var/tmp') as td:
            top = Path(td); top.chmod(0o755)
            runtime = top / 'runtime'; root = runtime / 'root'
            for directory in ('usr', 'proc', 'sys', 'opt', 'home/meteohub', 'run', 'dev', 'tmp'):
                (root / directory).mkdir(parents=True, exist_ok=True)
            for alias, target in [('bin', 'usr/bin'), ('sbin', 'usr/sbin'), ('lib', 'usr/lib'), ('lib64', 'usr/lib64')]:
                (root / alias).symlink_to(target)
            home = root / 'home/meteohub'; os.chown(home, 65534, 65534)
            config = home / 'meteohub.conf'
            before = bytes(65536); activated = bytearray(before); activated[p.FIELD] = b'A' * 32
            current = bytearray(before); current[100] = 17
            config.write_bytes(current); config.chmod(0o600); os.chown(config, 65534, 65534)
            shared = top / 'shared-run'; shared.mkdir(mode=0o700); os.chown(shared, 65534, 65534)
            lock = runtime / '.feed-consumer.lock'; lock.touch(); os.chown(lock, 65534, 65534)
            fake_sys = top / 'sys'; (fake_sys / 'devices/mmc').mkdir(parents=True)
            (fake_sys / 'fs/cgroup').mkdir(parents=True)
            (fake_sys / 'block/mmcblk0').mkdir(parents=True)
            (fake_sys / 'block/mmcblk0/device').symlink_to('../../devices/mmc')
            for key in ('serial', 'name', 'date'): (fake_sys / 'devices/mmc' / key).write_text('host-unchanged\n')
            saved = top / 'saved'; source = saved / 'identity-view'; source.mkdir(parents=True)
            (source / 'cpuinfo').write_text(v.cpu_view('processor : 0\n', ID))
            for key in ('serial', 'name', 'date'): (source / ('sd-' + key)).write_text(ID['sd_' + key] + '\n')
            (source / 'ifconfig').write_text(v.adapter_view(Path(__file__).with_name('ifconfig-compat.py').read_bytes(), ID))
            setup = 'ip link add eth0 type dummy && ip link set eth0 address 02:00:00:00:00:01 && ip address add 192.0.2.50/26 dev eth0 && ip link set eth0 up && echo READY && exec sleep 120'
            net = subprocess.Popen(['unshare', '--net', '--', '/bin/sh', '-c', setup], stdout=subprocess.PIPE, text=True)
            prefix = 'meteohub-permanent-fixture-' + str(time.time_ns())
            apps = [prefix + suffix for suffix in ('-web.socket', '-web.service', '-logger.service', '-index.service')]
            units = Path('/run/systemd/system')
            cfg = dict(runtime=str(runtime), persist=str(top / 'persist'), ram=str(top / 'ram'), uuid='fixture',
                       ram_mib=64, apps=apps, lock=str(top / 'storage.lock'))
            storage = m.Storage(cfg)
            identity = top / 'installed-identity'
            try:
                self.assertEqual(net.stdout.readline().strip(), 'READY')
                (units / apps[0]).write_text('[Socket]\nListenStream=' + str(top / 'web.sock') + '\n')
                for name in apps[1:]:
                    lines = ['[Service]', 'User=65534', 'Group=65534', 'RootDirectory=' + str(root),
                             'MountAPIVFS=yes', 'ProtectSystem=strict', 'ReadWritePaths=+/home/meteohub +/run',
                             'ProtectKernelTunables=yes', 'NoNewPrivileges=yes', 'CapabilityBoundingSet=',
                             'RestrictAddressFamilies=AF_INET AF_UNIX',
                             'NetworkNamespacePath=/proc/' + str(net.pid) + '/ns/net',
                             'BindReadOnlyPaths=/usr:/usr ' + str(fake_sys) + ':/sys',
                             'BindPaths=' + str(shared) + ':/run', 'TimeoutStopSec=5s']
                    if name == apps[2]:
                        lines += ['BindPaths=' + str(lock) + ':/run/feed-consumer.lock',
                                  'ExecStart=/usr/bin/flock --nonblock --no-fork /run/feed-consumer.lock /bin/sleep infinity']
                    else: lines += ['ExecStart=/bin/sleep infinity']
                    (units / name).write_text('\n'.join(lines) + '\n')
                m.run('systemctl', 'daemon-reload'); m.run('systemctl', 'start', *apps)
                targets = {units / (name + '.d') / '60-native-identity.conf': p.identity_unit(identity) for name in (apps[1], apps[2])}
                targets[units / (apps[2] + '.d') / '40-logger-pid.conf'] = Path(__file__).with_name('logger-pid-status.conf').read_bytes()
                # This fixture exercises real services, locks, binds and rollback.
                # RAM overlay/checkpoint lifecycle is covered by test-ram-storage.
                with patch.multiple(p, RUNTIME=runtime, WEB=apps[1], LOGGER=apps[2], IDENTITY=identity), \
                     patch.object(storage, 'live_state', return_value={}), \
                     patch.object(p, 'host_identity', side_effect=lambda: (fake_sys / 'devices/mmc/serial').read_bytes()):
                    (source / 'check.py').write_text('raise SystemExit(1)\n')
                    with self.assertRaises(RuntimeError):
                        p.apply_configuration(m, storage, saved, targets, before, activated, top)
                    self.assertEqual(config.read_bytes(), current)
                    self.assertFalse(identity.exists())
                    self.assertTrue(all(not path.exists() for path in targets))
                    self.assertTrue(all(storage.active(name) == 'active' for name in apps))
                    (source / 'check.py').write_text(v.check_source(ID))
                    p.apply_configuration(m, storage, saved, targets, before, activated, top)
                    p.confirm_views(m, storage)
                    self.assertEqual(config.read_bytes(), p.merge_activation(current, before, activated))
                    self.assertEqual(config.stat().st_uid, 65534)
                    self.assertEqual(config.stat().st_mode & 0o777, 0o600)
                    self.assertFalse(any('BindPaths=' in data.decode() for path, data in targets.items() if 'identity' in path.name))
                for key in ('serial', 'name', 'date'):
                    self.assertEqual((fake_sys / 'devices/mmc' / key).read_text(), 'host-unchanged\n')
                actual = m.run('nsenter', '-t', str(net.pid), '-n', '--', 'ip', '-j', 'address', 'show', 'eth0').stdout
                self.assertIn('02:00:00:00:00:01', actual)
            finally:
                m.run('systemctl', 'stop', *apps, check=False)
                m.run('systemctl', 'reset-failed', *apps, check=False)
                for name in apps:
                    (units / name).unlink(missing_ok=True)
                    shutil.rmtree(units / (name + '.d'), ignore_errors=True)
                m.run('systemctl', 'daemon-reload')
                net.terminate(); net.wait(timeout=5); net.stdout.close()


if __name__ == '__main__': unittest.main()
