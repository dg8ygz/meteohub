#!/usr/bin/env python3
"""Prepare the pinned vendor 5.1e core update in a NEW private candidate.

No archive scripts are executed, no complete archive is extracted, and no host
or running receiver is modified. Native validation is a separate step.
"""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import tarfile

ARCHIVE_SHA256 = '725bf80186fe2e426e0caad80d6b5994c013fe7f918506fbfb62f5aef2826ad4'
ARCHIVE_SIZE = 18584769
GCGI_SHA256 = 'b8c22c56b978e7a66e050a1c0ff4aaf74dce95d79661a535b767e0cd80042ec6'
CORE = {
    'loggerd': 'acc728deb3759fc45cce54cca0e6a5d40fe3f98ea8580d2e5296181ce29a0efb',
    'meteometar': '0594afc52864e9109ed351d0c48a0c4a15ba124578b2a53ffb17a281ba642030',
    'meteonet': 'a2597dc8a3e6bcb70ac3b2ac6bb3dfef446688d5d226f453d02088f5fc3c9293',
    'meteoschedule': '38033efa587c37fe332479392943d19dcdf011b832ad0cad9f5d9890743722c9',
    'meteohub.cgi': '88d3bea39a66756c258ad52e11b2f12da2fc50a74def88b09ab7e0f2b9c5d1a6',
}


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    return tool


def archive_files(archive):
    # Read the same bounded bytes that were hashed; never extractall or follow links.
    if archive.is_symlink() or not archive.is_file() or archive.stat().st_size != ARCHIVE_SIZE:
        raise ValueError('Unexpected update file type/size')
    data = archive.read_bytes()
    if hashlib.sha256(data).hexdigest() != ARCHIVE_SHA256:
        raise ValueError('Update SHA256 mismatch')
    selected = {}
    seen = set()
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as package:
        for member in package:
            path = PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or member.name in seen:
                raise ValueError('Unsafe or duplicate archive member')
            seen.add(member.name)
            if member.name not in {'rpi/' + name for name in CORE}:
                continue
            if not member.isfile() or member.size > 16 * 1024 * 1024:
                raise ValueError('Selected update member is not a bounded regular file')
            content = package.extractfile(member).read()
            name = path.name
            if hashlib.sha256(content).hexdigest() != CORE[name]:
                raise ValueError('Update component hash mismatch: ' + name)
            selected[name] = content
    if set(selected) != set(CORE):
        raise ValueError('Missing Raspberry Pi core update files')
    return selected


def stage(archive, base, destination):
    archive = archive.absolute()
    base = base.resolve(strict=True)
    destination = destination.absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError('Destination already exists; previous candidates are preserved')
    if destination.resolve().is_relative_to(base):
        raise ValueError('Destination must be outside the existing candidate')
    load_tool('probe-cgi').verify(base)
    crypto = load_tool('stage-openssl3')
    library = crypto.read_original(base, 'lib/libgcgi.so.0', GCGI_SHA256)
    sources = archive_files(archive)
    prepared = []
    for name, source in sources.items():
        crypto.arm_elf(source)
        if name == 'loggerd':
            output, imports, edits = source, [], []
        else:
            output, imports, edits = crypto.adapt(source)
        prepared.append(('bin/' + name, output, {
            'source': 'update-v5.1e.upd:rpi/' + name,
            'source_sha256': CORE[name], 'openssl_imports': imports,
            'edits': edits, 'executable_sections_unchanged': True,
        }))
    prepared.append(('lib/libgcgi.so.0', library, {
        'source': 'base-candidate:lib/libgcgi.so.0', 'source_sha256': GCGI_SHA256,
        'openssl_imports': [], 'edits': [], 'executable_sections_unchanged': True,
    }))
    os.umask(0o077)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.mkdir(mode=0o700)
    records = []
    for target, data, record in prepared:
        path = destination / target
        path.parent.mkdir(mode=0o700, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(data)
        path.chmod(0o700)
        records.append(dict(record, target=target, candidate_sha256=crypto.digest(data)))
    manifest = {
        'status': '5.1e core candidate; native loading, CGI and logger acceptance pending',
        'application_version': '5.1e', 'update_sha256': ARCHIVE_SHA256,
        'scope': 'loggerd, meteometar, meteonet, meteoschedule, meteohub.cgi; existing libgcgi',
        'not_installed': 'other update components, legacy OS packages/scripts and boot services',
        'files': records,
    }
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    load_tool('probe-cgi').verify(destination)
    print('PREPARED:', destination)
    print('VERSION: 5.1e; five ARM application binaries plus verified libgcgi')
    print('PASS: package/component hashes, ARM ELF and unchanged executable sections')
    print('Native runtime/build-number validation remains pending.')
    print('No scripts executed; no runtime, configuration, service or host files changed.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('update', type=Path)
    parser.add_argument('base_candidate', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error('Run as the normal login user, without sudo')
    try:
        stage(args.update, args.base_candidate, args.destination)
    except (OSError, ValueError, tarfile.TarError) as error:
        parser.exit(1, 'STOP: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
