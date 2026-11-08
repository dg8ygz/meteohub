#!/usr/bin/env python3
"""Real ext4 and systemd fixtures; never uses a station, SD card or production unit.

Run as root with --isolation. Mounts live in a private mount namespace.
"""
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest


def run(*args, check=True, **kw):
    return subprocess.run(args, check=check, text=True, capture_output=True, **kw)


@unittest.skipUnless('--inside' in sys.argv, 'requires --isolation as root')
class BootstrapTest(unittest.TestCase):
    def test_real_backup_restore_and_failure_recovery(self):
        self.assertEqual(os.getuid(), 0)
        with tempfile.TemporaryDirectory(prefix='meteohub-bootstrap-test-', dir='/var/tmp') as td:
            top = Path(td)
            runtime = top / 'runtime'
            home = runtime / 'root/home/meteohub'
            data = runtime / 'root/data'
            home.mkdir(parents=True)
            (data / 'dashboard').mkdir(parents=True)
            (data / 'weather').mkdir()
            (home / 'meteohub.conf').write_bytes(b'private-test-config')
            (home / 'link').symlink_to('/home/meteohub/meteohub.conf')
            (runtime / 'live-install.json').write_text('{}')
            raw = data / 'weather/raw'
            raw.write_text('20261108235000 t2 50\n')
            raw.chmod(0o640)
            os.chown(raw, 65534, 65534)
            db = data / 'dashboard/weather.sqlite'
            # Deliberately leave committed rows in WAL, as after an abrupt process exit.
            run(sys.executable, '-c', 'import sqlite3,os,sys; c=sqlite3.connect(sys.argv[1]); '
                'c.execute("PRAGMA journal_mode=WAL"); c.execute("CREATE TABLE test(n)"); '
                'c.execute("INSERT INTO test VALUES (42)"); c.commit(); os._exit(0)', str(db))
            self.assertTrue(Path(str(db) + '-wal').exists())
            image = top / 'partition.img'
            with image.open('wb') as f:
                f.truncate(256 * 1024 * 1024)
            run('mkfs.ext4', '-q', '-E', 'lazy_itable_init=0,lazy_journal_init=0', str(image))
            loop = run('losetup', '--find', '--show', str(image)).stdout.strip()
            persist = top / 'persist'
            persist.mkdir()
            prefix = 'meteohub-bootstrap-check-' + str(time.time_ns())
            original = ('meteohub-web-test.socket', 'meteohub-web-test.service',
                        'meteohub-live-logger.service', 'meteohub-dashboard-index.service')
            names = [prefix + suffix for suffix in ('-web.socket', '-web.service', '-logger.service', '-index.service')]
            unitpaths = [Path('/run/systemd/system') / name for name in names]
            try:
                run('mount', '-o', 'ro', loop, str(persist))
                uuid = run('blkid', '-s', 'UUID', '-o', 'value', loop).stdout.strip()
                unitpaths[0].write_text('[Socket]\nListenStream=' + str(top / 'socket') + '\n')
                for p in unitpaths[1:]:
                    p.write_text('[Service]\nExecStart=/usr/bin/sleep infinity\n')
                run('systemctl', 'daemon-reload')
                run('systemctl', 'start', *names)
                script = Path(__file__).with_name('bootstrap-persist.sh').read_text()
                for old, new in zip(original, names):
                    script = script.replace(old, new)
                script = script.replace('/run/lock/meteohub-storage.lock', str(top / 'storage.lock'))
                script = script.replace('/root/meteohub-restore-check-XXXXXXXX', str(top / 'restore-XXXXXXXX'))
                runner = top / 'bootstrap.sh'
                runner.write_text(script)
                result = run('bash', str(runner), str(runtime), str(persist), uuid)
                self.assertIn('VERIFIED BACKUP:', result.stdout)
                complete = list((persist / 'snapshots').glob('initial-*'))
                self.assertEqual(len(complete), 1)
                run('sha256sum', '-c', 'SHA256SUMS', cwd=complete[0])
                restored = top / 'restored'
                restored.mkdir()
                run('tar', '--numeric-owner', '-xpf', str(complete[0] / 'runtime.tar'), '-C', str(restored))
                self.assertEqual((restored / 'root/data/weather/raw').stat().st_uid, 65534)
                self.assertEqual(os.readlink(restored / 'root/home/meteohub/link'), '/home/meteohub/meteohub.conf')
                with sqlite3.connect(restored / 'root/data/dashboard/weather.sqlite') as connection:
                    self.assertEqual(connection.execute('SELECT n FROM test').fetchall(), [(42,)])
                # Force an archive-write failure after services have stopped.
                bindir = top / 'bin'
                bindir.mkdir()
                (bindir / 'tar').write_text('#!/bin/sh\necho "injected archive-write failure" >&2\nexit 2\n')
                (bindir / 'tar').chmod(0o700)
                env = dict(os.environ, PATH=str(bindir) + ':' + os.environ['PATH'])
                failed = run('bash', str(runner), str(runtime), str(persist), uuid, check=False, env=env)
                self.assertNotEqual(failed.returncode, 0)
                self.assertNotIn('VERIFIED BACKUP:', failed.stdout)
                self.assertEqual(list((persist / 'snapshots').glob('initial-*')), complete)
                for name in names:
                    self.assertEqual(run('systemctl', 'is-active', name).stdout.strip(), 'active')
                options = run('findmnt', '-nro', 'OPTIONS', '--mountpoint', str(persist)).stdout.strip().split(',')
                self.assertIn('ro', options)
                self.assertEqual(raw.read_text(), '20261108235000 t2 50\n')
                print('PASS: real ext4 snapshot, WAL restore, ownership/link preservation, failed backup recovery; no station used')
            finally:
                run('systemctl', 'stop', *names, check=False)
                run('systemctl', 'reset-failed', *names, check=False)
                for p in unitpaths:
                    p.unlink(missing_ok=True)
                run('systemctl', 'daemon-reload')
                run('umount', str(persist), check=False)
                run('losetup', '-d', loop)


if __name__ == '__main__':
    if '--isolation' in sys.argv:
        raise SystemExit(subprocess.call(['unshare', '--mount', '--propagation', 'private',
                                         sys.executable, __file__, '--inside']))
    inside = '--inside' in sys.argv
    if inside:
        sys.argv.remove('--inside')
    unittest.main()
