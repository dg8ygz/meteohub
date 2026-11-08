#!/usr/bin/env python3
"""Test private runtime preparation; optional real systemd isolation test as root."""
import ast
import errno
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stage = load('stage-runtime')
probe = load('probe-cgi')
ISOLATION = '--isolation' in sys.argv
if ISOLATION:
    sys.argv.remove('--isolation')


def preflight_text(runtime=True):
    """Exercise the exact script passed to systemd by the public probe."""
    tree = ast.parse(Path(__file__).with_name('probe-cgi.py').read_text())
    checks = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == 'check' for t in node.targets
        ):
            checks.insert(0, node.value.value)
        if (runtime and isinstance(node, ast.AugAssign)
                and isinstance(node.target, ast.Name) and node.target.id == 'check'):
            checks.append(node.value.value)
    return '\n'.join(checks)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='meteohub-runtime-test-', dir='/var/tmp')
        self.addCleanup(self.temp.cleanup)
        self.top = Path(self.temp.name)
        self.image = self.top / 'image'
        self.image.mkdir()
        selected = (
            'home/meteohub/meteohub.conf', 'home/meteohub/meteohub-license-5.txt',
            'home/meteohub/meteohub-license.txt', 'home/meteohub/weather-display-live-license.txt',
            'etc/network/interfaces', 'etc/thttpd.conf', 'etc/ntp.conf',
            'etc/samba/smb.conf', 'srv/www/cgi-bin/admin.html',
        )
        for name in selected:
            path = self.image / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'\0' * 65536 if name.endswith('meteohub.conf') else b'test fixture\n')
        (self.image / 'srv/www/cgi-bin/.htpasswd').write_text('not to be copied')
        (self.image / 'srv/www/cgi-bin/old.cgi').write_text('not to be copied')
        (self.image / 'srv/www/link.html').symlink_to('/etc/passwd')
        (self.image / 'home/meteohub/meteohub-5.lic').write_text('not to be copied')
        self.runtime = self.top / 'runtime'

    def test_selected_resources_and_existing_destination(self):
        plan = stage.prepare(self.image)
        self.assertEqual(len(plan), 9)
        stage.materialize(self.runtime, plan, os.getuid(), os.getgid(), 'probe')
        root = self.runtime / 'root'
        for name in ('srv/www/cgi-bin/.htpasswd', 'srv/www/cgi-bin/old.cgi',
                     'srv/www/link.html', 'home/meteohub/meteohub-5.lic'):
            self.assertFalse((root / name).exists())
        self.assertEqual((root / 'home/meteohub/meteohub.conf').stat().st_size, 65536)
        self.assertEqual(list((root / 'data/weather').iterdir()), [])
        with self.assertRaises(FileExistsError):
            stage.materialize(self.runtime, plan, os.getuid(), os.getgid(), 'probe')

    def test_source_link_and_wrong_config_size(self):
        ntp = self.image / 'etc/ntp.conf'
        ntp.unlink()
        ntp.symlink_to('/etc/passwd')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            stage.prepare(self.image)
        ntp.unlink()
        ntp.write_text('fixture')
        (self.image / 'home/meteohub/meteohub.conf').write_bytes(b'wrong')
        with self.assertRaisesRegex(ValueError, '65536'):
            stage.prepare(self.image)
        self.assertFalse(self.runtime.exists())

    def test_resolver_completion_is_narrow_and_preserves_existing(self):
        stage.materialize(self.runtime, stage.prepare(self.image), os.getuid(), os.getgid(), 'probe')
        config = self.runtime / 'root/home/meteohub/meteohub.conf'
        before = config.read_bytes()
        resolver = self.runtime / 'root/etc/resolv.conf'
        self.assertEqual(resolver.read_bytes(), stage.RESOLVER)
        resolver.unlink()  # Simulate a previously prepared runtime.
        stage.ensure_resolver(self.runtime)
        self.assertEqual(resolver.read_bytes(), stage.RESOLVER)
        stage.ensure_resolver(self.runtime)
        resolver.write_text('custom resolver')
        with self.assertRaisesRegex(ValueError, 'differs'):
            stage.ensure_resolver(self.runtime)
        self.assertEqual(resolver.read_text(), 'custom resolver')
        resolver.unlink()
        resolver.symlink_to('/etc/resolv.conf')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            stage.ensure_resolver(self.runtime)
        self.assertEqual(config.read_bytes(), before)

    @unittest.skipUnless(ISOLATION, 'enable --isolation for actual systemd test')
    def test_real_isolation(self):
        if os.geteuid() != 0:
            self.skipTest('system-level test needs root; production probe uses sudo itself')
        stage.materialize(self.runtime, stage.prepare(self.image), 65534, 65534, 'nobody')
        candidate = self.top / 'candidate'
        (candidate / 'bin').mkdir(parents=True)
        (candidate / 'lib').mkdir()
        (candidate / 'bin/loggerd').write_text('not executed')
        for parent, _, files in os.walk(self.top):
            os.chown(parent, 65534, 65534)
            for name in files:
                os.chown(Path(parent) / name, 65534, 65534, follow_symlinks=False)
        # Run the exact preflight used by the user-facing probe with real systemd.
        command = ['systemd-run', '--wait', '--pipe', '--collect', '--uid=65534',
                   '--gid=65534', '--expand-environment=no']
        command += ['--property=' + p for p in probe.properties(candidate, self.runtime)]
        command += ['/usr/bin/env', '-i', 'PATH=/usr/bin:/bin', 'HOME=/home/meteohub',
                    'LANG=C', 'LD_BIND_NOW=1',
                    'LD_LIBRARY_PATH=/home/meteohub/lib:/usr/lib/arm-linux-gnueabihf']
        result = subprocess.run(command + ['/usr/bin/python3', '-c', preflight_text()],
                                capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('private config/data writable', result.stdout)
        self.assertEqual((candidate / 'bin/loggerd').read_text(), 'not executed')
        print(result.stdout, end='')

    @unittest.skipUnless(ISOLATION, 'enable --isolation for actual systemd test')
    def test_running_elf_requires_readonly_mounts(self):
        if os.geteuid() != 0:
            self.skipTest('system-level test needs root')
        stage.materialize(self.runtime, stage.prepare(self.image), 65534, 65534, 'nobody')
        candidate = self.top / 'candidate'
        (candidate / 'bin').mkdir(parents=True)
        (candidate / 'lib').mkdir()
        binary = candidate / 'bin/loggerd'
        shutil.copyfile(shutil.which('sleep'), binary)
        binary.chmod(0o700)
        before = binary.read_bytes()
        self.assertEqual(before[:4], b'\x7fELF', 'real ELF required to exercise ETXTBSY')
        for parent, _, files in os.walk(self.top):
            os.chown(parent, 65534, 65534)
            for name in files:
                os.chown(Path(parent) / name, 65534, 65534, follow_symlinks=False)
        child = subprocess.Popen([str(binary), '120'], user=65534, group=65534, extra_groups=[])
        try:
            self.assertIsNone(child.poll())
            # Reproduce the misleading errno on a genuinely writable filesystem.
            self.assertFalse(os.statvfs(binary).f_flag & os.ST_RDONLY)
            with self.assertRaises(OSError) as caught:
                fd = os.open(binary, os.O_WRONLY | os.O_APPEND)
                os.close(fd)
            self.assertEqual(caught.exception.errno, errno.ETXTBSY)
            for runtime in (None, self.runtime):
                for writable in (None, 'bin', 'lib'):
                    with self.subTest(runtime=runtime is not None, writable=writable):
                        props = probe.properties(candidate, runtime)
                        if writable:
                            # Deliberately weaken one bind mount, retaining all
                            # other isolation properties and the executing ELF.
                            source = str(candidate / writable)
                            target = '/home/meteohub/' + writable
                            if runtime:
                                props = [p.replace(' ' + source + ':' + target, '')
                                         if p.startswith('BindReadOnlyPaths=') else p for p in props]
                            props += ['BindPaths=' + source + ':' + target,
                                      'ReadWritePaths=' + target]
                        command = ['systemd-run', '--wait', '--pipe', '--collect',
                                   '--uid=65534', '--gid=65534', '--expand-environment=no']
                        command += ['--property=' + p for p in props]
                        result = subprocess.run(command + ['/usr/bin/python3', '-c',
                            preflight_text(runtime is not None)], capture_output=True, text=True, timeout=45)
                        output = result.stdout + result.stderr
                        if writable:
                            self.assertNotEqual(result.returncode, 0, output)
                            self.assertIn('candidate mount writable: ' + writable, output)
                        else:
                            self.assertEqual(result.returncode, 0, output)
                            self.assertIn('read-only candidate', output)
                        self.assertIsNone(child.poll(), output)
                        self.assertEqual(binary.read_bytes(), before)
        finally:
            child.terminate()
            try: child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill(); child.wait(timeout=5)
        print('PASS: executing ELF accepted only with read-only mounts; writable bin/lib rejected in both probe modes')


if __name__ == '__main__':
    unittest.main()
