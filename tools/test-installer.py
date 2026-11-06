#!/usr/bin/env python3
"""Installer orchestration checks: no APT, mount, network or target mutation."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch, Mock

spec=importlib.util.spec_from_file_location('installer',Path(__file__).resolve().parents[1]/'install-pi.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name);self.app=installer.Installer(self.home)
        self.app.original.mkdir();self.app.work.mkdir()

    def test_download_reuse_and_bad_hash_never_overwritten(self):
        path=self.home/'archive';path.write_bytes(b'archive')
        with patch.object(installer,'run') as run:
            installer.download('https://example.invalid',path,installer.sha(path));run.assert_not_called()
            with self.assertRaisesRegex(ValueError,'checksum'):installer.download('https://example.invalid',path,'wrong')
        self.assertEqual(path.read_bytes(),b'archive')

    def test_partial_download_and_symlink_refused(self):
        target=self.home/'a.upd';target.with_suffix('.upd.part').write_bytes(b'partial')
        with self.assertRaisesRegex(ValueError,'Incomplete'):installer.download('https://example.invalid',target,'none')
        target.symlink_to(self.home/'other')
        with self.assertRaisesRegex(ValueError,'symlink'):installer.download('https://example.invalid',target,'none')

    def test_saved_loop_cannot_detach_other_image(self):
        (self.app.original/'image-loop.device').write_text('/dev/loop9\n')
        with patch.object(installer,'run',return_value=Mock(stdout='/some/other/image\n')) as run:
            with self.assertRaisesRegex(ValueError,'another image'):self.app.unmount()
            self.assertFalse(any('--detach' in call.args[0] for call in run.call_args_list))

    def test_wrong_mount_refused_without_mount_command(self):
        image=self.app.original/'mhrpi-v5.0s.img'
        with image.open('wb') as f:f.truncate(1970274304)
        (self.app.original/'image-loop.device').write_text('/dev/loop9')
        def response(args,**kw):
            if args[0]=='/usr/sbin/sfdisk':return Mock(stdout=json.dumps({'partitiontable':{'sectorsize':512,'partitions':[{}, {'start':104448,'size':3481600,'type':'83'},{}]}}))
            return Mock(returncode=0,stdout=json.dumps({'filesystems':[{'source':'/dev/foreign','fstype':'ext3','options':'ro,nodev,nosuid,noexec,noload'}]}))
        with patch.object(self.app,'loop',return_value='/dev/loop9'),patch.object(installer,'run',side_effect=response) as run:
            with self.assertRaisesRegex(ValueError,'Existing mount'):self.app.mount_image()
            self.assertFalse(any('mount' in call.args[0] for call in run.call_args_list))

    def test_existing_runtime_reused_no_restage(self):
        self.app.base.mkdir();self.app.candidate.mkdir();self.app.runtime.mkdir()
        (self.app.candidate/'manifest.json').write_text(json.dumps({'application_version':'5.1e','update_sha256':installer.UPDATE_SHA}))
        (self.app.original/'mhrpi-v5.0s.img').touch()
        probe=Mock()
        with patch.object(installer,'platform_check'),patch.object(installer,'packages'),patch.object(installer,'run'),patch.object(installer,'download'),patch.object(self.app,'mount_image'),patch.object(installer,'load',return_value=probe),patch.object(installer,'helper') as helper:
            self.app.prepare();helper.assert_not_called();probe.verify_runtime.assert_called_once_with(self.app.runtime)

    def test_running_wrong_web_runtime_is_not_replaced(self):
        (self.app.runtime/'root/opt/meteohub-web').mkdir(parents=True)
        web=Mock()
        with patch.object(installer,'load',return_value=web),patch.object(installer,'run',return_value=Mock(stdout='ActiveState=active\nRootDirectory=/other/root\nBindReadOnlyPaths=\n')):
            with self.assertRaisesRegex(ValueError,'Another test runtime'):self.app.web()
            web.start.assert_not_called();web.prepare.assert_not_called()

    def test_feed_host_must_be_explicit(self):
        with patch.object(installer,'run') as run:
            with self.assertRaisesRegex(ValueError,'source-host'):self.app.feed_test(None,5500,120)
            run.assert_not_called()


if __name__=='__main__':unittest.main()
