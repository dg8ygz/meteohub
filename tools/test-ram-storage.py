#!/usr/bin/python3
"""Real, separately named ext4/overlay/tmpfs/systemd fixtures; no real receiver.

Run as root with --isolation. Uses only temporary mountpoints and test units;
systemd must see the mounts, so unlike bootstrap tests this is not in unshare.
"""
import importlib.util
import contextlib
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import shutil
import time
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('ram_storage', Path(__file__).with_name('ram-storage.py'))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
ISOLATION = '--isolation' in sys.argv
if ISOLATION: sys.argv.remove('--isolation')


@contextlib.contextmanager
def fixture_directory():
    top = Path(tempfile.mkdtemp(prefix='meteohub-ram-check-', dir='/var/tmp'))
    try:
        yield str(top)
    finally:
        mounted = m.run('findmnt', '-rn', '-o', 'TARGET').stdout.splitlines()
        if any(path == str(top) or path.startswith(str(top) + '/') for path in mounted):
            print('Fixture retained because mounts remain:', top, file=sys.stderr)
        else:
            shutil.rmtree(top)


class ManifestTests(unittest.TestCase):
    def test_paths_and_links(self):
        with tempfile.TemporaryDirectory() as td:
            top = Path(td)
            (top / 'link').symlink_to('/does/not/exist')
            self.assertEqual(m.fingerprint(top)['link']['target'], '/does/not/exist')
            for path in ('/', str(top / 'link'), '/tmp/a,b', '/tmp/../etc'):
                with self.assertRaises(ValueError): m.safe_path(path)


@unittest.skipUnless(ISOLATION, 'requires --isolation as root')
class LifecycleTests(unittest.TestCase):
    def test_real_overlay_checkpoints_shutdown_restore_and_failures(self):
        self.assertEqual(os.getuid(), 0)
        with fixture_directory() as td:
            top = Path(td)
            runtime = top / 'runtime'; home = runtime / 'root/home/meteohub'; data = runtime / 'root/data'
            home.mkdir(parents=True); (data / 'dashboard').mkdir(parents=True)
            (data / 'weather/202601').mkdir(parents=True); (data / 'weather/202611').mkdir()
            (home / 'meteohub.conf').write_bytes(b'test-settings')
            (home / 'absolute-link').symlink_to('/home/meteohub/meteohub.conf')
            (runtime / 'live-install.json').write_text('{}')
            raw = data / 'weather/202611/raw'; raw.write_text('old\n')
            (data / 'weather/202601/raw').write_bytes(b'historical\n' * 10000)
            db = data / 'dashboard/weather.sqlite'
            m.run(sys.executable, '-c', 'import sqlite3,os,sys; c=sqlite3.connect(sys.argv[1]); '
                  'c.execute("PRAGMA journal_mode=WAL"); c.execute("CREATE TABLE test(n)"); '
                  'c.execute("INSERT INTO test VALUES (42)"); c.commit(); os._exit(0)', db)
            image = top / 'disk.img'
            with image.open('wb') as f: f.truncate(1024 * 1024 * 1024)
            m.run('mkfs.ext4', '-q', '-E', 'lazy_itable_init=0,lazy_journal_init=0', image)
            loop = m.run('losetup', '--find', '--show', image).stdout.strip()
            persist = top / 'persist'; persist.mkdir()
            prefix = 'meteohub-ram-test-' + str(time.time_ns())
            apps = [prefix + suffix for suffix in ('-web.socket', '-web.service', '-logger.service', '-index.service')]
            target = prefix + '.target'
            config = top / 'config.json'
            cfg = dict(runtime=str(runtime), persist=str(persist), ram=str(top / 'ram'),
                       uuid='', ram_mib=64, apps=apps, target=target, prefix=prefix,
                       lock=str(top / 'storage.lock'))
            paths = []
            s = None
            try:
                m.run('mount', '-o', 'ro', loop, persist)
                cfg['uuid'] = m.run('blkid', '-s', 'UUID', '-o', 'value', loop).stdout.strip()
                s = m.Storage(cfg)
                def unit(name, text):
                    path = Path('/run/systemd/system') / name
                    path.write_text(text); paths.append(path)
                unit(target, '[Unit]\nDescription=Private RAM storage test\nWants=' + ' '.join(apps) + '\n')
                unit(apps[0], '[Socket]\nListenStream=' + str(top / 'socket') + '\n')
                for name in apps[1:]: unit(name, '[Service]\nExecStart=/usr/bin/sleep infinity\n')
                m.run('systemctl', 'daemon-reload'); m.run('systemctl', 'start', *apps)
                with s.lock(), s.paused(): seed = s.capture()
                helper = top / 'ram-helper.py'
                helper.write_bytes(Path(__file__).with_name('ram-storage.py').read_bytes())
                cfg['helper'] = str(helper)
                cfg['helper_sha256'] = hashlib.sha256(helper.read_bytes()).hexdigest()
                control_start = len(paths)
                for name, text in m.render(config, helper, cfg).items():
                    unit(name, text)
                # Apply the same Before/After/Requires ordering as the production installer.
                for name in apps:
                    p = Path('/run/systemd/system') / (name + '.d') / 'ram.conf'
                    p.parent.mkdir()
                    p.write_text('[Unit]\nRequires=' + prefix + '.service\nAfter=' + prefix + '.service\n')
                    paths.append(p)
                cfg['installed_files'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths[control_start:]}
                m.save(config, cfg)
                m.run('systemctl', 'stop', *apps)
                m.run('systemctl', 'daemon-reload')
                m.run('systemctl', 'start', *apps)
                self.assertEqual(m.mount_info(runtime)['fstype'], 'overlay')
                self.assertEqual(s.status()['ram_limit_bytes'], 64 * 1024 * 1024)
                self.assertFalse((Path(s.live_state()['upper']) / 'root/data/weather/202601/raw').exists())
                self.assertEqual(raw.read_text(), 'old\n')
                with raw.open('a') as f: f.write('new\n')
                with contextlib.closing(sqlite3.connect(db)) as c:
                    c.execute('INSERT INTO test VALUES(43)'); c.commit()
                ref = s.checkpoint()
                self.assertEqual(s.reference(), ref)
                self.assertEqual(s.live_state()['ref'], ref)
                self.assertEqual(raw.read_text(), 'old\nnew\n')
                self.assertFalse((Path(s.live_state()['upper']) / 'root/data/weather/202611/raw').exists())
                with contextlib.closing(sqlite3.connect(db)) as c:
                    self.assertEqual(c.execute('SELECT n FROM test').fetchall(), [(42,), (43,)])
                # Failure after quiescing must resume apps, retain data/current and restore RO.
                real_run = m.run
                def failed_copy(*args, **kw):
                    if args[0] == 'cp': raise RuntimeError('injected persistence write failure')
                    return real_run(*args, **kw)
                with patch.object(m, 'run', side_effect=failed_copy):
                    with self.assertRaisesRegex(RuntimeError, 'injected'): s.checkpoint()
                self.assertEqual(s.reference(), ref)
                self.assertTrue(all(s.active(n) == 'active' for n in apps))
                self.assertIn('ro', m.mount_info(persist)['options'].split(','))
                self.assertEqual(raw.read_text(), 'old\nnew\n')
                with self.assertRaises(ValueError): s.verify(dict(ref, digest='0' * 64))
                with patch.dict(s.cfg, uuid='wrong'):
                    with self.assertRaises(ValueError): s.restore()
                # Exhaust the bounded upper: checkpoint/rebase still has its control state outside it.
                fill = data / 'fill-test'
                with fill.open('wb') as f:
                    try:
                        for _ in range(100): f.write(b'x' * 1024 * 1024)
                        f.flush()
                    except OSError as error:
                        self.assertEqual(error.errno, 28)
                self.assertTrue(s.status()['needs_attention'])
                s.checkpoint()
                self.assertLess(s.status()['ram_used_bytes'], 1024 * 1024)
                fill.unlink()
                # Stop the storage unit; systemd must stop dependent apps before its checkpoint.
                with raw.open('a') as f: f.write('shutdown\n')
                m.run('systemctl', 'stop', prefix + '.service')
                self.assertIsNone(m.mount_info(runtime))
                self.assertIsNone(m.mount_info(s.ram))
                self.assertEqual(raw.read_text(), 'old\n')  # original underlying SD tree unchanged
                m.run('systemctl', 'start', *apps)
                self.assertEqual(raw.read_text(), 'old\nnew\nshutdown\n')
                self.assertFalse(fill.exists())
                self.assertTrue(all(s.active(n) == 'active' for n in apps))
                # Simulated loss of unsaved RAM: restore must use the last sealed generation.
                m.run('systemctl', 'stop', *apps)
                with raw.open('a') as f: f.write('unsaved\n')
                m.run('umount', runtime); m.run('umount', s.ram)
                s.restore()
                self.assertEqual(raw.read_text(), 'old\nnew\nshutdown\n')
                m.run('systemctl', 'start', *apps)
                # A bad generation at boot must prevent app start, not fall back to stale SD data.
                m.run('systemctl', 'stop', prefix + '.service')
                valid = s.reference()
                with s.writable(): m.save(s.current, dict(valid, digest='0' * 64))
                failed = m.run('systemctl', 'start', *apps, check=False)
                self.assertNotEqual(failed.returncode, 0)
                self.assertIsNone(m.mount_info(runtime))
                self.assertNotEqual(s.active(apps[2]), 'active')
                self.assertEqual(raw.read_text(), 'old\n')
                with s.writable(): m.save(s.current, valid)
                m.run('systemctl', 'reset-failed', prefix + '.service')
                m.run('systemctl', 'start', *apps)
                # Exercise complete removal including copying final data back to the original host filesystem.
                real_mkdtemp = tempfile.mkdtemp
                def fixture_backup(*args, **kw):
                    if kw.get('dir') == '/root': kw['dir'] = str(top)
                    return real_mkdtemp(*args, **kw)
                with patch.object(m.tempfile, 'mkdtemp', side_effect=fixture_backup):
                    m.uninstall(s, config)
                self.assertIsNone(m.mount_info(runtime))
                self.assertEqual(raw.read_text(), 'old\nnew\nshutdown\n')
                self.assertFalse(config.exists())
                self.assertTrue(all(s.active(n) == 'active' for n in apps))
                print('PASS: actual overlay/tmpfs, checkpoint/rebase, WAL restore, full RAM recovery, failed SD write, shutdown ordering, loss of unsaved RAM and rollback to normal runtime')
            finally:
                # Service is stopped while its helper/config still exist.
                m.run('systemctl', 'stop', target, *apps, prefix + '.service', check=False)
                m.run('systemctl', 'reset-failed', target, *apps, prefix + '.service', check=False)
                for p in reversed(paths):
                    p.unlink(missing_ok=True)
                    if p.parent.name.endswith('.d') and p.parent.exists(): p.parent.rmdir()
                m.run('systemctl', 'daemon-reload')
                if m.mount_info(runtime): m.run('umount', runtime)
                if s and m.mount_info(s.ram): m.run('umount', s.ram)
                if m.mount_info(persist): m.run('umount', persist)
                m.run('losetup', '-d', loop)


if __name__ == '__main__': unittest.main()
