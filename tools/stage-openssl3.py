#!/usr/bin/env python3
"""Prepare private Meteohub 5.0s ELF candidates; never run or install them.

This is an experimental dependency adaptation, not a general OpenSSL ABI shim.
Original executable sections and application/license instructions stay unchanged.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct

from elftools.elf.elffile import ELFFile

ALLOWED = {
    'MD5', 'BIO_ctrl', 'BIO_f_base64', 'BIO_free', 'BIO_free_all',
    'BIO_new', 'BIO_new_mem_buf', 'BIO_push', 'BIO_read', 'BIO_s_mem',
    'BIO_set_flags', 'BIO_write', 'EVP_PKEY_free', 'EVP_PKEY_get1_RSA',
    'PEM_read_bio_PUBKEY', 'RSA_new', 'RSA_public_decrypt',
}
# Hashes from the operator's read-only manufacturer-image inventory.
# No proprietary binary contents are distributed with this tool.
FILES = [
    ('home/meteohub/loggerd', 'bin/loggerd',
     '510feb62753c39394a467083ecaf89150f0db16ee3a680b76862fff05bb27aae', False),
    ('home/meteohub/meteometar', 'bin/meteometar',
     '6adc516f559ef9413438ccaed64541514277bbf057a5a448a35a9bcb08ba38a4', True),
    ('home/meteohub/meteonet', 'bin/meteonet',
     'a8d864ccfe6c8ea339ba8df90d470f169b0973b6998ccef932b6bb1656eb22ef', True),
    ('home/meteohub/meteoschedule', 'bin/meteoschedule',
     '7bb7dfba2559fe19eaf596d1df24968ab1aee21cb1741ec0656673ec1831f5a7', True),
    ('srv/www/cgi-bin/meteohub.cgi', 'bin/meteohub.cgi',
     'ff0e1b169c1ea006f412afc7f5d0e7cf4ad13728e186328056cc9fe79746ee91', True),
    ('usr/local/lib/libgcgi.so.0.0.0', 'lib/libgcgi.so.0',
     'b8c22c56b978e7a66e050a1c0ff4aaf74dce95d79661a535b767e0cd80042ec6', False),
]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def elfhash(value):
    result = 0
    for byte in value.encode('ascii'):
        result = (result << 4) + byte
        high = result & 0xf0000000
        if high:
            result ^= high >> 24
        result &= ~high
    return result


def arm_elf(data):
    elf = ELFFile(io.BytesIO(data))
    require(elf.elfclass == 32 and elf.little_endian and
            elf['e_machine'] == 'EM_ARM', 'Expected little-endian ARM ELF32')
    return elf


def adapt(data):
    elf = arm_elf(data)
    dynstr = elf.get_section_by_name('.dynstr')
    require(dynstr is not None, 'Missing dynamic strings')
    strings = dynstr.data()
    versions = elf.get_section_by_name('.gnu.version_r')
    indexes = set()
    if versions:
        for need, auxiliaries in versions.iter_versions():
            for aux in auxiliaries:
                if aux.name.startswith('OPENSSL_'):
                    require(aux.name == 'OPENSSL_1.0.0', 'Unexpected OpenSSL version')
                    require(need.name in ('libcrypto.so.1.0.0', 'libssl.so.1.0.0'),
                            'Unexpected OpenSSL version provider')
                    indexes.add(aux['vna_other'] & 0x7fff)
    imports = []
    symbols = elf.get_section_by_name('.dynsym')
    versym = elf.get_section_by_name('.gnu.version')
    require(symbols is not None and versym is not None, 'Missing versioned symbols')
    for i, symbol in enumerate(symbols.iter_symbols()):
        index = versym.get_symbol(i)['ndx']
        if isinstance(index, int) and (index & 0x7fff) in indexes:
            require(symbol['st_shndx'] == 'SHN_UNDEF', 'Unexpected OpenSSL definition')
            require(symbol.name in ALLOWED, 'Unreviewed import: ' + symbol.name)
            imports.append(symbol.name)

    edits = []
    for before, after in (
        ('libcrypto.so.1.0.0', 'libcrypto.so.3'),
        ('libssl.so.1.0.0', 'libssl.so.3'),
        ('OPENSSL_1.0.0', 'OPENSSL_3.0.0'),
    ):
        needle = before.encode() + b'\0'
        count = strings.count(needle)
        if not count:
            continue
        require(count == 1, 'Ambiguous string: ' + before)
        index = strings.index(needle)
        require(index == 0 or strings[index - 1] == 0, 'String is not standalone')
        replacement = after.encode().ljust(len(needle), b'\0')
        require(len(replacement) == len(needle), 'Replacement would grow ELF')
        edits.append((dynstr['sh_offset'] + index, needle, replacement, before + ' -> ' + after))

    if versions:
        start = versions['sh_offset']
        end = start + versions['sh_size']
        at = start
        while at < end:
            require(at + 16 <= end, 'Truncated version record')
            version, count, _, aux_offset, next_offset = struct.unpack_from('<HHIII', data, at)
            require(version == 1, 'Unknown version record format')
            pos = at + aux_offset
            for index in range(count):
                require(start <= pos and pos + 16 <= end, 'Bad version auxiliary offset')
                value, _, _, name, following = struct.unpack_from('<IHHII', data, pos)
                require(name < len(strings), 'Bad version name offset')
                label = strings[name:].split(b'\0', 1)[0]
                if label == b'OPENSSL_1.0.0':
                    require(value == elfhash('OPENSSL_1.0.0'), 'Unexpected version hash')
                    edits.append((pos, data[pos:pos + 4],
                                  struct.pack('<I', elfhash('OPENSSL_3.0.0')),
                                  'OpenSSL version hash'))
                if index + 1 < count:
                    require(following >= 16, 'Invalid auxiliary chain')
                pos += following
            if not next_offset:
                break
            require(next_offset >= 16, 'Invalid version chain')
            at += next_offset
    require(edits, 'No old OpenSSL references to adapt')
    result = bytearray(data)
    occupied = set()
    for offset, before, after, _ in edits:
        region = set(range(offset, offset + len(before)))
        require(not region & occupied, 'Overlapping modifications')
        occupied.update(region)
        require(data[offset:offset + len(before)] == before, 'Unexpected source bytes')
        result[offset:offset + len(before)] = after
    require(len(result) == len(data), 'ELF size changed')
    for section in elf.iter_sections():
        if section['sh_flags'] & 4:  # SHF_EXECINSTR, including .plt/.init/.fini
            start = section['sh_offset']
            stop = start + section['sh_size']
            require(result[start:stop] == data[start:stop],
                    'Executable section changed: ' + section.name)
    checked = arm_elf(bytes(result))
    original_needed = [t.needed for t in elf.get_section_by_name('.dynamic').iter_tags()
                       if t.entry.d_tag == 'DT_NEEDED']
    checked_needed = [t.needed for t in checked.get_section_by_name('.dynamic').iter_tags()
                      if t.entry.d_tag == 'DT_NEEDED']
    replacements = {'libcrypto.so.1.0.0': 'libcrypto.so.3',
                    'libssl.so.1.0.0': 'libssl.so.3'}
    require(checked_needed == [replacements.get(name, name) for name in original_needed],
            'Unexpected final library dependencies')
    final_versions = checked.get_section_by_name('.gnu.version_r')
    if final_versions:
        for _, auxiliaries in final_versions.iter_versions():
            for aux in auxiliaries:
                if (aux['vna_other'] & 0x7fff) in indexes:
                    require(aux.name == 'OPENSSL_3.0.0' and
                            aux['vna_hash'] == elfhash('OPENSSL_3.0.0'),
                            'Incorrect final version metadata')
    return bytes(result), sorted(imports), [
        {'offset': off, 'before_hex': old.hex(), 'after_hex': new.hex(), 'reason': why}
        for off, old, new, why in edits
    ]


def read_original(root, relative, expected):
    path = root
    for component in Path(relative).parts:
        path /= component
        require(not path.is_symlink(), 'Source symlink refused: ' + str(path))
    require(stat.S_ISREG(path.stat().st_mode), 'Not a regular source file')
    require(path.stat().st_size <= 16 * 1024 * 1024, 'Unexpected source size')
    data = path.read_bytes()
    require(digest(data) == expected, 'Original SHA256 mismatch: ' + relative)
    arm_elf(data)
    return data


def stage(root, destination):
    root = root.resolve(strict=True)
    require(root != Path('/') and root.is_dir(), 'Use the separate image mount')
    destination = destination.absolute()
    require(not destination.exists() and not destination.is_symlink(),
            'Destination already exists; do not overwrite an earlier candidate')
    require(not destination.resolve().is_relative_to(root), 'Destination is inside original')
    prepared = []
    # Validate every source before creating any output directory.
    for source, target, expected, change in FILES:
        original = read_original(root, source, expected)
        candidate, imports, edits = adapt(original) if change else (original, [], [])
        prepared.append((target, candidate, {
            'source': source, 'target': target, 'source_sha256': expected,
            'candidate_sha256': digest(candidate), 'openssl_imports': imports,
            'edits': edits, 'executable_sections_unchanged': True,
        }))
    os.umask(0o077)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.mkdir(mode=0o700)
    for target, data, _ in prepared:
        path = destination / target
        path.parent.mkdir(mode=0o700, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(data)
        path.chmod(0o700)
    manifest = {
        'status': 'experimental candidate; runtime validation pending',
        'image_version': 'mhrpi-v5.0s',
        'files': [item for _, _, item in prepared],
    }
    with (destination / 'manifest.json').open('x') as stream:
        json.dump(manifest, stream, indent=2)
        stream.write('\n')
    print('PREPARED:', destination)
    for target, _, record in prepared:
        print(target + ': ' + str(len(record['edits'])) + ' metadata edits; code unchanged')
    print('No programs started; no system library, service, configuration or activation changed.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image_root', type=Path)
    parser.add_argument('destination', type=Path, help='New private directory outside the image/repository')
    args = parser.parse_args()
    try:
        stage(args.image_root, args.destination)
    except (OSError, ValueError) as error:
        parser.exit(1, 'STOP: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
