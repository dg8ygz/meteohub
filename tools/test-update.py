#!/usr/bin/env python3
"""Test update staging with a separately downloaded vendor archive and libgcgi."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('update', Path(__file__).with_name('stage-update.py'))
update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.sources = update.archive_files(ARCHIVE)
        self.base = self.root/'base'
        entries = []
        for name, data in list(self.sources.items()) + [('libgcgi.so.0', LIBRARY.read_bytes())]:
            target = ('lib/' if name.startswith('libgcgi') else 'bin/') + name
            path = self.base/target
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            entries.append({'target': target, 'candidate_sha256': hashlib.sha256(data).hexdigest()})
        (self.base/'manifest.json').write_text(json.dumps({'files': entries}))

    def test_real_update_preserves_sources_and_instructions(self):
        before = {str(p.relative_to(self.base)): p.read_bytes() for p in self.base.rglob('*') if p.is_file()}
        dest = self.root/'5.1e'
        update.stage(ARCHIVE, self.base, dest)
        manifest = json.loads((dest/'manifest.json').read_text())
        self.assertEqual(manifest['application_version'], '5.1e')
        self.assertEqual(len(manifest['files']), 6)
        self.assertEqual({str(p.relative_to(self.base)): p.read_bytes() for p in self.base.rglob('*') if p.is_file()}, before)
        crypto = update.load_tool('stage-openssl3')
        for name, original in self.sources.items():
            output = (dest/'bin'/name).read_bytes()
            elf = crypto.arm_elf(original)
            for section in elf.iter_sections():
                if section['sh_flags'] & 4:
                    start, size = section['sh_offset'], section['sh_size']
                    self.assertEqual(original[start:start+size], output[start:start+size])
            needed = [t.needed for t in crypto.arm_elf(output).get_section_by_name('.dynamic').iter_tags() if t.entry.d_tag == 'DT_NEEDED']
            self.assertNotIn('libcrypto.so.1.0.0', needed)
            self.assertNotIn('libssl.so.1.0.0', needed)
        self.assertFalse((dest/'now').exists())
        self.assertFalse((dest/'id_rsa').exists())
        self.assertFalse((dest/'bin/bash').exists())

    def test_existing_and_nested_destination_refused(self):
        for dest in (self.base, self.base/'new'):
            with self.assertRaises(ValueError): update.stage(ARCHIVE, self.base, dest)
        dest = self.root/'link';dest.symlink_to(self.root/'absent')
        with self.assertRaises(ValueError): update.stage(ARCHIVE, self.base, dest)

    def test_corrupt_archive_and_links_refused_before_output(self):
        damaged = self.root/'bad.upd'
        data = bytearray(ARCHIVE.read_bytes());data[-1] ^= 1;damaged.write_bytes(data)
        dest = self.root/'output'
        with self.assertRaisesRegex(ValueError, 'SHA256'): update.stage(damaged, self.base, dest)
        self.assertFalse(dest.exists())
        link = self.root/'link.upd';link.symlink_to(ARCHIVE)
        with self.assertRaises(ValueError): update.archive_files(link)

    def test_unreviewed_library_refused(self):
        p = self.base/'lib/libgcgi.so.0';p.write_bytes(b'wrong')
        manifest = json.loads((self.base/'manifest.json').read_text())
        manifest['files'][-1]['candidate_sha256'] = hashlib.sha256(b'wrong').hexdigest()
        (self.base/'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'SHA256'): update.stage(ARCHIVE, self.base, self.root/'out')
        self.assertFalse((self.root/'out').exists())

    def test_archive_paths_duplicates_and_selected_symlinks_refused(self):
        for names, linked in ((['../escape'], False), (['/escape'], False),
                              (['rpi/loggerd'], True), (['unused', 'unused'], False)):
            with self.subTest(names=names, linked=linked):
                stream = io.BytesIO()
                with tarfile.open(fileobj=stream, mode='w:gz') as t:
                    for name in names:
                        member = tarfile.TarInfo(name)
                        if linked:
                            member.type = tarfile.SYMTYPE;member.linkname = '/etc/passwd'
                        t.addfile(member)
                data = stream.getvalue();p = self.root/'crafted.upd';p.write_bytes(data)
                with mock.patch.object(update, 'ARCHIVE_SHA256', hashlib.sha256(data).hexdigest()), mock.patch.object(update, 'ARCHIVE_SIZE', len(data)):
                    with self.assertRaises(ValueError): update.archive_files(p)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit('Usage: python3 tools/test-update.py UPDATE_FILE BASE_LIBGCGI')
    ARCHIVE = Path(sys.argv[1]).resolve(strict=True)
    LIBRARY = Path(sys.argv[2]).resolve(strict=True)
    del sys.argv[1:]
    unittest.main()
