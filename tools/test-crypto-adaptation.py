#!/usr/bin/env python3
"""Regression checks using separately obtained originals, never executing them."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    'stage_openssl3', Path(__file__).with_name('stage-openssl3.py'))
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


class AdaptationTests(unittest.TestCase):
    def test_real_binaries_and_manifest(self):
        for source, _, _, change in stage.FILES:
            if not change:
                continue
            with self.subTest(source=source):
                path = ORIGINAL / source
                before = path.read_bytes()
                after, imports, edits = stage.adapt(before)
                self.assertEqual(len(before), len(after))
                covered = set()
                for edit in edits:
                    start = edit['offset']
                    old = bytes.fromhex(edit['before_hex'])
                    new = bytes.fromhex(edit['after_hex'])
                    self.assertEqual(before[start:start + len(old)], old)
                    self.assertEqual(after[start:start + len(new)], new)
                    covered.update(range(start, start + len(old)))
                changed = {i for i, (a, b) in enumerate(zip(before, after)) if a != b}
                self.assertTrue(changed)
                self.assertLessEqual(changed, covered)
                self.assertEqual(path.read_bytes(), before)
                elf = stage.arm_elf(before)
                for section in elf.iter_sections():
                    if section['sh_flags'] & 4:
                        start = section['sh_offset']
                        end = start + section['sh_size']
                        self.assertEqual(after[start:end], before[start:end])
                with self.assertRaises(ValueError):
                    stage.adapt(after)
                if imports:
                    old = imports[0].encode() + b'\0'
                    modified = before.replace(old, b'X' + old[1:])
                    with self.assertRaisesRegex(ValueError, 'Unreviewed import'):
                        stage.adapt(modified)

    def test_wrong_hash_and_source_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = (ORIGINAL / 'home/meteohub/meteonet').read_bytes()
            (root / 'binary').write_bytes(original)
            with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
                stage.read_original(root, 'binary', '0' * 64)
            (root / 'link').symlink_to('binary')
            with self.assertRaisesRegex(ValueError, 'symlink refused'):
                stage.read_original(root, 'link', stage.digest(original))

    def test_existing_output_and_source_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root / 'existing'
            existing.mkdir()
            marker = existing / 'keep'
            marker.write_text('retained')
            with self.assertRaisesRegex(ValueError, 'already exists'):
                stage.stage(ORIGINAL, existing)
            self.assertEqual(marker.read_text(), 'retained')
            with self.assertRaisesRegex(ValueError, 'inside original'):
                stage.stage(root, root / 'output')
            self.assertFalse((root / 'output').exists())


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('Usage: python3 tools/test-crypto-adaptation.py ORIGINAL_IMAGE_ROOT')
    ORIGINAL = Path(sys.argv.pop()).resolve(strict=True)
    unittest.main()
