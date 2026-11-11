#!/usr/bin/python3
"""Verified upgrade of the deployed checkpoint helper to a six-hour schedule."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile

OLD = '3b77c2e8c679714b7bde914225f32d7dce88eec11f1548015bc3c85f8f184725'
NEW = 'd588b4cefdba8a5dea26d9f96420651e19a29922ad9187a5b77753f51d2023ad'
HELPER = Path('/usr/local/libexec/meteohub-ram.py')


def upgraded(payload):
    digest = hashlib.sha256(payload).hexdigest()
    if digest == NEW:
        return payload
    if digest != OLD:
        raise ValueError('Unbekannter Helferstand; nichts geaendert.')
    text = payload.decode().replace('(15, 30, 60)', '(15, 30, 60, 360)')
    text = text.replace('must be 15, 30 or 60 minutes',
                        'must be 15, 30, 60 or 360 minutes')
    text = text.replace(
        '    return {\n        service:',
        "    if minutes == 360: calendar = '*-*-* 00,06,12,18:00:00 UTC'\n"
        '    return {\n        service:')
    result = text.encode()
    if hashlib.sha256(result).hexdigest() != NEW:
        raise ValueError('Ergebnis stimmt nicht mit dem getesteten Helfer ueberein.')
    return result


def main():
    if os.geteuid() != 0:
        raise ValueError('Bitte als root ausfuehren.')
    os.umask(0o077)
    root = subprocess.check_output(
        ['findmnt', '-nro', 'FSTYPE,OPTIONS', '--mountpoint', '/'], text=True).split()
    if len(root) != 2 or root[0] != 'ext4' or 'rw' not in root[1].split(','):
        raise ValueError('Beschreibbarer ext4-Wartungsboot erforderlich; keine Bootaenderung vorgenommen.')
    if HELPER.is_symlink() or not HELPER.is_file():
        raise ValueError('Installierter Helfer fehlt oder ist ein Symlink.')
    payload = upgraded(HELPER.read_bytes())
    stage = Path(tempfile.mkdtemp(prefix='meteohub-6h-', dir='/root'))
    script = stage / 'ram-storage.py'
    script.write_bytes(payload)
    print('Gepruefter Helfer:', script, flush=True)
    # The existing installer verifies owned files, creates its rollback backup,
    # updates ownership hashes and the health threshold, and reloads the timer.
    subprocess.run([sys.executable, str(script), 'configure-checkpoints',
                    '--minutes', '360'], check=True)
    print('OK: alle 6 Stunden (00/06/12/18 UTC); Altersgrenze 23400 Sekunden.', flush=True)
    print('Ein nachgeholter Sicherungslauf kann die Anwendungen kurz pausieren.', flush=True)
    subprocess.run(['systemctl', 'list-timers', '--all', '--no-pager', '--full',
                    'meteohub-ram-*'], check=True)
    subprocess.run([sys.executable, str(HELPER), 'status'], check=True)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print('STOP:', error, file=sys.stderr)
        sys.exit(1)
