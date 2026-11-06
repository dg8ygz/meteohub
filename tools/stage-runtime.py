#!/usr/bin/env python3
"""Build a private native CGI test root, not a host/application installation."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import stat

RESOLVER = (
    b'# Isolated CGI test only; no DNS service or external network is enabled.\n'
    b'nameserver 127.0.0.1\noptions timeout:1 attempts:1\n'
)


def ensure_resolver(runtime):
    runtime = runtime.resolve(strict=True)
    load_tool('probe-cgi').verify_runtime(runtime)
    target = runtime / 'root/etc/resolv.conf'
    if target.is_symlink():
        raise ValueError('Resolver symlink refused; no file changed')
    try:
        with target.open('xb') as stream:
            stream.write(RESOLVER)
        target.chmod(0o600)
    except FileExistsError:
        if target.read_bytes() != RESOLVER:
            raise ValueError('Existing resolver differs; leaving it unchanged')
        print('UNCHANGED: private test resolver already present')
        return
    print('ADDED:', target)
    print('Loopback placeholder only; host DNS and network unchanged.')


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def original_file(root, relative, limit=8 * 1024 * 1024):
    # Selected files must be regular, with no implicit traversal through links.
    path = root
    for part in Path(relative).parts:
        if part in ('.', '..'):
            raise ValueError('Invalid source path')
        path /= part
        if path.is_symlink():
            raise ValueError('Source symlink needs separate review: ' + relative)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
        raise ValueError('Unexpected file type/size: ' + relative)
    return path.read_bytes()


def prepare(root):
    copies = []
    for source, target in (
        ('home/meteohub/meteohub.conf', 'home/meteohub/meteohub.conf'),
        ('home/meteohub/meteohub-license-5.txt', 'home/meteohub/meteohub-license-5.txt'),
        ('home/meteohub/meteohub-license.txt', 'home/meteohub/meteohub-license.txt'),
        ('home/meteohub/weather-display-live-license.txt',
         'home/meteohub/weather-display-live-license.txt'),
        ('etc/network/interfaces', 'etc/network/interfaces'),
        ('etc/thttpd.conf', 'etc/thttpd.conf'),
        ('etc/ntp.conf', 'etc/ntp.conf'),
        ('etc/samba/smb.conf', 'etc/samba/smb.conf'),
    ):
        data = original_file(root, source)
        if source.endswith('/meteohub.conf') and len(data) != 65536:
            raise ValueError('Expected the inventoried 65536-byte original configuration')
        copies.append((source, target, data))
    # Only static resources; no old CGI, scripts, Flash, passwords or application symlinks.
    web = root / 'srv/www'
    if web.is_symlink() or web.parent.is_symlink() or not web.is_dir():
        raise ValueError('Unexpected original web directory')
    allowed = {'.html', '.htm', '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.txt'}
    def failed(error):
        raise error
    total = sum(len(data) for _, _, data in copies)
    for parent, dirs, files in os.walk(web, followlinks=False, onerror=failed):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.') and not (Path(parent) / d).is_symlink())
        for name in sorted(files):
            path = Path(parent) / name
            if name.startswith('.') or path.is_symlink() or path.suffix.lower() not in allowed:
                continue
            relative = str(path.relative_to(root))
            data = original_file(root, relative)
            total += len(data)
            if total > 64 * 1024 * 1024:
                raise ValueError('Unexpected resource size, more than 64 MiB')
            copies.append((relative, relative, data))
    return copies


def materialize(destination, copies, uid, gid, username):
    os.umask(0o077)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.mkdir(mode=0o700)  # Refuse existing directories, including dangling symlinks.
    root = destination / 'root'
    dirs = (
        'usr', 'etc/ssl', 'etc/network', 'etc/samba', 'home/meteohub/bin',
        'home/meteohub/lib', 'data/weather', 'data/graphs', 'data/export',
        'data/myweb', 'data/log', 'srv/www/cgi-bin', 'opt/etc/ntp', 'opt/share',
        'dev', 'proc', 'sys', 'run', 'tmp', 'var/tmp', 'root', 'mnt', 'media',
    )
    for name in dirs:
        (root / name).mkdir(parents=True, exist_ok=True)
    def write(name, data, mode=0o600):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(data)
        target.chmod(mode)
    manifest = []
    for source, target, data in copies:
        write(target, data)
        manifest.append({'source': source, 'target': target,
                         'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
    # Native Trixie programs/libraries are mounted read-only from /usr during each probe.
    for name, target in {
        'bin': 'usr/bin', 'sbin': 'usr/sbin', 'lib': 'usr/lib', 'lib64': 'usr/lib64',
        'var/run': '/run', 'opt/etc/ntp/ntp.conf': '/etc/ntp.conf',
        'opt/share/zoneinfo-posix': '/usr/share/zoneinfo',
    }.items():
        (root / name).symlink_to(target)
    write('etc/passwd', (
        'root:x:0:0:root:/root:/bin/sh\n'
        f'{username}:x:{uid}:{gid}:CGI test:/home/meteohub:/bin/sh\n').encode())
    write('etc/group', f'root:x:0:\nprobe:x:{gid}:\n'.encode())
    write('etc/nsswitch.conf', b'passwd: files\ngroup: files\nhosts: files dns\n')
    write('etc/hosts', b'127.0.0.1 localhost\n::1 localhost\n')
    write('etc/resolv.conf', RESOLVER)
    # Timezone is taken from the new host, never from the 2016 image.
    localtime = Path('/etc/localtime').resolve(strict=True)
    write('etc/localtime', localtime.read_bytes())
    if Path('/etc/timezone').is_file():
        write('etc/timezone', Path('/etc/timezone').read_bytes())
    (destination / 'runtime-manifest.json').write_text(json.dumps({
        'schema': 1, 'status': 'private CGI test root; no services installed',
        'uid': uid, 'gid': gid, 'copied_files': manifest,
        'network': 'isolated; copied legacy settings are test fixtures, not live host settings',
        'data': 'empty; no weather archive, license key or acceptance markers imported',
    }, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image_root', type=Path, nargs='?')
    parser.add_argument('candidate', type=Path, nargs='?')
    parser.add_argument('destination', type=Path, nargs='?')
    parser.add_argument('--ensure-resolver', type=Path,
                        help='Add only the missing private resolver to an existing test root')
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error('Run as the normal login user, without sudo')
    if args.ensure_resolver is not None:
        if any((args.image_root, args.candidate, args.destination)):
            parser.error('--ensure-resolver takes only the existing runtime path')
        ensure_resolver(args.ensure_resolver)
        return
    if not all((args.image_root, args.candidate, args.destination)):
        parser.error('Provide image_root, candidate and destination')
    root = args.image_root.resolve(strict=True)
    candidate = args.candidate.resolve(strict=True)
    destination = args.destination.absolute()
    if root == Path('/') or destination.exists() or destination.is_symlink():
        parser.error('Use a separate image mount and a NEW destination')
    if destination.resolve().is_relative_to(root) or destination.resolve().is_relative_to(candidate):
        parser.error('Destination must be outside image and binary candidate')
    crypto = load_tool('stage-openssl3')
    for source, _, expected, _ in crypto.FILES:
        crypto.read_original(root, source, expected)
    load_tool('probe-cgi').verify(candidate)
    copies = prepare(root)  # Read/validate everything before writing any destination.
    user = pwd.getpwuid(os.getuid())
    materialize(destination, copies, os.getuid(), os.getgid(), user.pw_name)
    print('PREPARED:', destination)
    print('Copied', len(copies), 'configuration/text/static-resource files; manifest saved privately.')
    print('Empty data directories; no activation or acceptance markers imported.')
    print('No host settings or services changed. Run the isolated probe with --runtime next.')


if __name__ == '__main__':
    main()
