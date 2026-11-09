#!/usr/bin/python3
"""Private ext4 fixture: verified identity capture and read-only failure recovery."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = load('ram', 'ram-storage.py')
s = load('stage', 'stage-identity-persistence.py')
ISOLATION = '--isolation' in sys.argv
if ISOLATION: sys.argv.remove('--isolation')


class CaptureTests(unittest.TestCase):
    def test_change_ranges_without_values(self):
        before = bytes(65536)
        after = bytearray(before)
        for offset in (0, 27836, 27837, 65535): after[offset] = 42
        self.assertEqual(s.changed_ranges(before, after), [[0, 0], [27836, 27837], [65535, 65535]])
        self.assertEqual(s.changed_ranges(before, before), [])
        with self.assertRaises(ValueError): s.changed_ranges(before, b'')

    @unittest.skipUnless(ISOLATION, 'requires --isolation as root')
    def test_real_ext4_capture_and_failure_restore_ro(self):
        self.assertEqual(os.getuid(), 0)
        with tempfile.TemporaryDirectory(prefix='meteohub-identity-stage-') as td:
            top = Path(td)
            image = top / 'fixture.img'
            with image.open('wb') as f: f.truncate(96 * 1024 * 1024)
            m.run('mkfs.ext4', '-q', '-E', 'lazy_itable_init=0,lazy_journal_init=0', image)
            loop = m.run('losetup', '--find', '--show', image).stdout.strip()
            persist = top / 'persist'; persist.mkdir()
            try:
                m.run('mount', '-o', 'ro,nosuid,nodev,noexec', loop, persist)
                cfg = dict(runtime=str(top / 'runtime'), persist=str(persist), ram=str(top / 'ram'),
                           uuid=m.mount_info(persist)['uuid'], ram_mib=64, apps=m.APPS,
                           lock=str(top / 'lock'))
                storage = m.Storage(cfg)
                source = top / 'private'; source.mkdir(mode=0o700)
                secret = source / 'meteohub.conf'; secret.write_bytes(bytes(range(256)) * 256)
                secret.chmod(0o600); os.chown(secret, 1000, 1000)
                (source / 'link').symlink_to('/home/meteohub/meteohub.conf')
                sources = {'identity-view': source, 'standalone': secret}
                with storage.lock():
                    result = s.capture(m, storage, sources, {'status.json': b'{}'})
                storage.disk()
                self.assertEqual(m.fingerprint(source), m.fingerprint(result / 'identity-view'))
                manifest = json.loads((result / 'manifest.json').read_text())
                actual = m.fingerprint(result); actual.pop('manifest.json')
                self.assertEqual(actual, manifest['files'])
                self.assertEqual(result.parent.stat().st_mode & 0o777, 0o700)
                # Inject a real copy corruption; failure must not publish or leave RW.
                original_run = m.run
                def corrupt(*args, **kwargs):
                    value = original_run(*args, **kwargs)
                    if args[0] == 'cp':
                        (Path(args[-1]) / 'meteohub.conf').write_bytes(b'corrupt')
                    return value
                with storage.lock(), patch.object(m, 'run', corrupt):
                    with self.assertRaisesRegex(ValueError, 'copy differs'):
                        s.capture(m, storage, sources, {})
                storage.disk()
                self.assertEqual(list(result.parent.glob('ready-*')), [result])
                self.assertEqual(m.fingerprint(result / 'identity-view'), m.fingerprint(source))
                cfg['uuid'] = 'wrong-uuid'
                with self.assertRaisesRegex(ValueError, 'wrong UUID'):
                    s.capture(m, storage, sources, {})
            finally:
                if m.mount_info(persist): m.run('umount', persist)
                m.run('losetup', '-d', loop)


if __name__ == '__main__': unittest.main()
