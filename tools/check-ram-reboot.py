#!/usr/bin/python3
"""Operator-driven reboot proof. Run prepare, reboot manually, then run check.

Host root must still be a normal writable persistent filesystem. The temporary
RAM-service logging drop-in is removed only after successful proof. No reboot
is initiated by this tool, and no synthetic weather records are generated.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import sys
import time

PROOF = Path('/root/meteohub-ram-reboot-check')
CONFIG = Path('/etc/meteohub-ram.json')
HELPER = Path('/usr/local/libexec/meteohub-ram.py')
DROPIN = Path('/etc/systemd/system/meteohub-ram.service.d/90-reboot-proof.conf')
BOOTID = Path('/proc/sys/kernel/random/boot_id')


def prefix_hash(path, length):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while length:
            data = f.read(min(length, 1024 * 1024))
            if not data: raise ValueError('Archive shorter than recorded pre-reboot prefix')
            h.update(data); length -= len(data)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('prepare', 'check'))
    args = p.parse_args()
    if os.getuid(): p.error('Run as root')
    os.umask(0o077)
    cfg = json.loads(CONFIG.read_text())
    if HELPER.is_symlink() or hashlib.sha256(HELPER.read_bytes()).hexdigest() != cfg['helper_sha256']:
        raise ValueError('Installed helper differs from managed hash')
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('ram_storage', HELPER)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    s = m.Storage(cfg)
    root = m.mount_info(Path('/'))
    if not root or root['fstype'] != 'ext4' or 'rw' not in root['options'].split(','):
        raise ValueError('This test requires the original writable ext4 host root')
    with s.lock():
        status = s.status()
        if status['needs_attention']: raise ValueError('RAM status needs attention: ' + json.dumps(status))
        marker = s.runtime / '.ram-reboot-proof'
        if args.action == 'prepare':
            if any(x.exists() or x.is_symlink() for x in (PROOF, DROPIN, marker)):
                raise ValueError('Proof/drop-in/marker already exists; retain and inspect it')
            PROOF.mkdir(mode=0o700)
            archive = 'root/data/weather/' + time.strftime('%Y%m', time.gmtime()) + '/raw'
            raw = s.runtime / archive
            size = raw.stat().st_size
            if not size: raise ValueError('Empty archive')
            token = secrets.token_hex(32) + '\n'
            content = ('[Service]\nStandardOutput=append:' + str(PROOF / 'ram-service.log') +
                       '\nStandardError=append:' + str(PROOF / 'ram-service.log') + '\n')
            m.save(PROOF / 'proof.json', dict(boot_id=BOOTID.read_text(), generation=s.reference()['name'],
                   archive=archive, bytes=size, sha256=prefix_hash(raw, size), marker=token,
                   dropin_sha256=hashlib.sha256(content.encode()).hexdigest()))
            m.save(PROOF / 'status-before.json', status)
            (PROOF / 'journal-before.txt').write_text(m.run('journalctl', '-b', '--no-pager').stdout)
            # This marker must remain unsaved until ExecStop captures it during shutdown.
            with marker.open('x') as f: f.write(token)
            DROPIN.parent.mkdir(parents=True, exist_ok=True)
            with DROPIN.open('x') as f: f.write(content)
            DROPIN.chmod(0o644)
            m.run('systemctl', 'daemon-reload')
            m.run('sync', '-f', PROOF)
            print('PREPARED:', PROOF)
            print('Reboot now normally; do not run a checkpoint or stop/start test beforehand.')
        else:
            proof = m.regular_json(PROOF / 'proof.json')
            if BOOTID.read_text() == proof['boot_id']: raise ValueError('No new boot detected')
            (PROOF / 'journal-after.txt').write_text(m.run('journalctl', '-b', '--no-pager').stdout)
            ref = s.reference()
            if ref['name'] == proof['generation']: raise ValueError('No new saved generation since preparation')
            saved = []
            for line in (PROOF / 'ram-service.log').read_text().splitlines():
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if isinstance(entry, dict) and entry.get('saved') == ref: saved.append(entry)
            if not saved: raise ValueError('RAM service log does not confirm ExecStop saved this generation')
            tree = s.verify(ref)
            for label, base in (('saved generation', tree), ('restored RAM', s.runtime)):
                if (base / marker.name).read_text() != proof['marker']:
                    raise ValueError('RAM marker missing or different in ' + label)
                if prefix_hash(base / proof['archive'], proof['bytes']) != proof['sha256']:
                    raise ValueError('Pre-reboot archive prefix differs in ' + label)
            if DROPIN.is_symlink() or hashlib.sha256(DROPIN.read_bytes()).hexdigest() != proof['dropin_sha256']:
                raise ValueError('Temporary logging drop-in changed; refusing automatic removal')
            # Retain proof and logs on persistent root; remove temporary logging and RAM marker.
            DROPIN.unlink(); m.run('systemctl', 'daemon-reload'); marker.unlink()
            m.save(PROOF / 'result.json', dict(passed=True, generation=ref['name'],
                   verified_archive_bytes=proof['bytes'], checked_at=time.time(), status=status))
            print('PASS: new boot, new saved generation, RAM marker and archive prefix restored.')
            print('PASS: persistence RO; all four apps active. Temporary logging removed.')
            print('PROOF:', PROOF)
            print(json.dumps(status, indent=2))


if __name__ == '__main__':
    try: main()
    except (OSError, ValueError, RuntimeError) as e:
        raise SystemExit('STOP: ' + str(e))
