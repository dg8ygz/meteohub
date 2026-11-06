#!/usr/bin/env python3
"""Read Meteohub image metadata without executing its programs or following links."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys


def inspect_runtime(root):
    """Report path metadata only; never follow even a parent-directory symlink."""
    errors = 0

    def describe(relative):
        nonlocal errors
        path = root
        try:
            for component in Path(relative).parts:
                path /= component
                info = path.lstat()
                if stat.S_ISLNK(info.st_mode):
                    print(f"SYMLINK {path.relative_to(root)} -> {os.readlink(path)}"
                          f" [not followed; requested {relative}]")
                    return None
            kind = ('DIRECTORY' if stat.S_ISDIR(info.st_mode) else
                    'FILE' if stat.S_ISREG(info.st_mode) else 'SPECIAL')
            print(f"{kind} {relative}: mode={stat.S_IMODE(info.st_mode):04o}"
                  f" bytes={info.st_size}")
            return path
        except FileNotFoundError:
            print(f"MISSING {relative} [first absent: {path.relative_to(root)}]")
        except OSError as error:
            errors += 1
            print(f"ERROR {relative}: {error}")
        return None

    for name in (
        'etc/network/interfaces', 'etc/thttpd.conf', 'opt/etc/ntp/ntp.conf',
        'etc/samba/smb.conf', 'opt/share/zoneinfo-posix', 'usr/share/zoneinfo',
        'home/meteohub/meteohub.conf', 'data', 'root/data',
        'srv/www', 'srv/www/cgi-bin', 'var/run',
    ):
        describe(name)
    home = describe('home/meteohub')
    if home is not None and home.is_dir():
        try:
            names = sorted(p.name for p in home.iterdir())
            found = [name for name in names if 'license' in name.lower()
                     or name.endswith('.lic')]
            if not found:
                print('MISSING license-related filenames in home/meteohub')
            for name in found:
                describe('home/meteohub/' + name)
        except OSError as error:
            errors += 1
            print(f"ERROR license filename listing: {error}")
    print(f"RESULT: runtime path inventory; {errors} read errors;"
          " no file contents read or programs executed")
    return int(errors != 0)


def inspect(root):
    errors = 0
    binaries = 0
    for relative in ("home/meteohub", "srv/www"):
        base = root / relative
        if not base.is_dir() or not base.resolve().is_relative_to(root):
            print(f"ERROR: missing or external directory: {relative}")
            errors += 1
            continue
        print(f"\nDIRECTORY {relative}")

        def walk_error(error):
            nonlocal errors
            errors += 1
            print(f"ERROR: directory traversal: {error}")

        files = 0
        total = 0
        for parent, dirs, names in os.walk(base, followlinks=False, onerror=walk_error):
            dirs.sort()
            for name in sorted(set(dirs + names)):
                path = Path(parent) / name
                label = str(path.relative_to(root))
                try:
                    info = path.lstat()
                    if stat.S_ISLNK(info.st_mode):
                        print(f"SYMLINK {label} -> {os.readlink(path)}")
                        continue
                    if not stat.S_ISREG(info.st_mode):
                        continue
                    files += 1
                    total += info.st_size
                    with path.open("rb") as source:
                        if source.read(4) != b"\x7fELF":
                            continue
                        source.seek(0)
                        digest = hashlib.file_digest(source, "sha256").hexdigest()
                    result = subprocess.run(
                        ["readelf", "-W", "-h", "-l", "-d", "--", str(path)],
                        capture_output=True, text=True, timeout=20,
                        env={**os.environ, "LC_ALL": "C"},
                    )
                    if result.returncode:
                        raise RuntimeError(f"readelf exit {result.returncode}: {result.stderr.strip()}")
                    output = result.stdout
                    def field(name):
                        found = re.search(r"^\s*" + re.escape(name) + r":\s*(.+)$", output, re.M)
                        return found.group(1) if found else "not reported"
                    interpreter = re.findall(r"Requesting program interpreter:\s*([^\]]+)", output)
                    needed = re.findall(r"\(NEEDED\).*?\[([^\]]+)\]", output)
                    search = re.findall(r"\((?:RPATH|RUNPATH)\).*?\[([^\]]+)\]", output)
                    print(f"ELF {label}: {field('Class')}; {field('Machine')}")
                    print(f"  interpreter={','.join(interpreter) or 'none'} needed={','.join(needed) or 'none'}")
                    if search:
                        print(f"  library-search-path={search}")
                    print(f"  sha256={digest}")
                    binaries += 1
                except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
                    errors += 1
                    print(f"ERROR {label}: {error}")
        print(f"FILES {relative}: {files} regular files, {total} bytes")
    print(f"\nRESULT: {binaries} ELF files; {errors} errors; no image programs executed")
    return 1 if errors or not binaries else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image_root", type=Path, help="Root of the read-only mounted image")
    parser.add_argument("--runtime-files", action="store_true",
                        help="Only report configuration/resource path metadata, not contents")
    args = parser.parse_args()
    root = args.image_root.resolve(strict=True)
    if root == Path("/") or not root.is_dir():
        parser.error("Use a separate mounted image directory, not the running root filesystem")
    if args.runtime_files:
        return inspect_runtime(root)
    if not shutil.which("readelf"):
        parser.error("readelf is missing; install binutils")
    return inspect(root)


if __name__ == "__main__":
    sys.exit(main())
