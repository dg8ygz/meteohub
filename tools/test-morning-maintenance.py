#!/usr/bin/python3
"""Installer refusal/rollback invariants, boot command guard and unit graph."""
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

TOOLS=Path(__file__).resolve().parent

def load(name):
    s=importlib.util.spec_from_file_location(name,TOOLS/(name+'.py'))
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

m=load('morning-maintenance');h=load('host-status-pi50')


class Tests(unittest.TestCase):
    def test_boot_refusal_and_exact_replacement(self):
        with tempfile.TemporaryDirectory() as td:
            cmd=Path(td)/'cmdline.txt'
            @contextlib.contextmanager
            def writable():yield
            with patch.object(m,'CMD',cmd),patch.object(m,'boot_writable',writable):
                for text in ('root=foo\n','overlayroot=disabled overlayroot=disabled\n',
                             'overlayroot=disabled\nsecond line\n'):
                    cmd.write_text(text)
                    with self.assertRaises(ValueError):m.change_boot('overlayroot=disabled','overlayroot=tmpfs:recurse=0')
                    self.assertEqual(cmd.read_text(),text)
                old='console=tty1 overlayroot=disabled root=PARTUUID=abc quiet\n'
                cmd.write_text(old)
                m.change_boot('overlayroot=disabled','overlayroot=tmpfs:recurse=0')
                self.assertEqual(cmd.read_text(),old.replace('overlayroot=disabled','overlayroot=tmpfs:recurse=0'))
                m.change_boot('overlayroot=tmpfs:recurse=0','overlayroot=disabled')
                self.assertEqual(cmd.read_text(),old)

    def test_archive_prefix_not_just_size(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'raw';p.write_bytes(b'abc\n')
            proof=dict(path=str(p),bytes=4,sha256=m.sha(p.read_bytes()))
            with p.open('ab') as f:f.write(b'new\n')
            m.prefix_check(proof)
            p.write_bytes(b'bad\nnew\n')
            with self.assertRaises(ValueError):m.prefix_check(proof)

    def test_native_directory_and_pid_links_no_fake_timestamp(self):
        with tempfile.TemporaryDirectory() as td:
            shared=Path(td);os.chown(shared,1000,1000);shared.chmod(0o700)
            with patch.object(h,'SHARED',shared):
                h.runtime_links()
                native=shared/'meteohub'
                self.assertEqual(native.stat().st_uid,1000)
                self.assertEqual(native.stat().st_mode & 0o777,0o700)
                self.assertFalse((native/'logger.dat').exists())
                (native/'logger.dat').write_text('1234567890')
                h.runtime_links()
                self.assertEqual((native/'logger.dat').read_text(),'1234567890')
                p=shared/'dropbear.pid';p.unlink();p.write_text('999')
                with self.assertRaisesRegex(ValueError,'foreign'):h.runtime_links()
                self.assertEqual(p.read_text(),'999')

    def test_native_timestamp_reports_missing_and_actual_age(self):
        with patch.object(m.Path,'read_text',side_effect=FileNotFoundError):
            self.assertFalse(m.native_status()['valid'])
        with patch.object(m.Path,'read_text',return_value='12345'),patch.object(m.time,'time',return_value=12360):
            self.assertEqual(m.native_status()['age_seconds'],15)

    def test_full_boot_graph_and_original_shutdown_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            top=Path(td);dest=top/'libexec'
            with patch.object(m,'DEST',dest),patch.object(m,'BUNDLE_FILE',Path(__file__),create=True):
                files=m.contents()
            self.assertNotIn(m.BASE,files)
            self.assertFalse(any(str(p).endswith('meteohub-ram.service') for p in files))
            units=top/'units';units.mkdir()
            for p,(data,mode) in files.items():
                if str(p).startswith('/etc/systemd/system/'):
                    target=units/p.relative_to('/etc/systemd/system')
                else:target=p
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);target.chmod(mode)
            target='meteohub-live.target'
            apps=['meteohub-web-test.socket',m.WEB,m.LOGGER,'meteohub-dashboard-index.service']
            (units/target).write_text('[Unit]\nWants='+' '.join(apps)+'\n')
            (units/apps[0]).write_text('[Unit]\nRequires=meteohub-ram.service\nAfter=meteohub-ram.service\n[Socket]\nListenStream=127.0.0.1:18998\n')
            for app in apps[1:]:
                (units/app).write_text('[Unit]\nRequires=meteohub-live-runtime.service meteohub-ram.service\nAfter=meteohub-live-runtime.service meteohub-ram.service\n[Service]\nExecStart=/usr/bin/sleep infinity\n')
            (units/'meteohub-live-runtime.service').write_text('[Service]\nType=oneshot\nRemainAfterExit=yes\nUser=1000\nRuntimeDirectory=meteohub-live-1000\nRuntimeDirectoryMode=0700\nExecStart=/usr/bin/true\n')
            (units/'meteohub-ram.service').write_text('[Unit]\nDefaultDependencies=no\nRequires=sysinit.target\nAfter=sysinit.target\nBefore='+' '.join(apps)+'\n[Service]\nType=oneshot\nRemainAfterExit=yes\nExecStart=/usr/bin/true\n')
            (units/m.CHECKPOINT).write_text('[Service]\nType=oneshot\nExecStart=/usr/bin/true\n')
            result=subprocess.run(['systemd-analyze','verify','--man=no','--generators=no',str(units/target),str(units/m.CHECKPOINT),str(units/'meteohub-checkpoint-thaw.timer')],
                                  env=dict(os.environ,SYSTEMD_UNIT_PATH=str(units)+':'),text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertNotIn('ordering cycle',result.stderr.lower())


if __name__=='__main__':unittest.main()
