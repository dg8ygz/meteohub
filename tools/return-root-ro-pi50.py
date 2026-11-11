#!/usr/bin/python3
"""Prepare this station's existing overlay boot, or verify it after reboot."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT_UUID = '15f4c6be-1102-4331-9904-f78e78afd1fd'
BOOT_UUID = 'B2F0-82D2'
PERSIST_UUID = '6d332cf5-8a19-4fc5-bcaa-5156ab2dad54'
BOOT = Path('/boot/firmware')
CMD = BOOT / 'cmdline.txt'
HELPER = '/usr/local/libexec/meteohub-ram.py'
RUNTIME = Path('/home/meteohub/meteohub-staging/5.1e-runtime')
POINTER = Path('/root/meteohub-ro-last.json')
BOOTID = Path('/proc/sys/kernel/random/boot_id')


def run(*args):
    r = subprocess.run(args, text=True, capture_output=True, timeout=180)
    if r.returncode:
        raise RuntimeError(' '.join(args[:2])+': '+r.stderr.strip())
    return r.stdout


def mount(path, uuid=None, fstype=None, mode='ro'):
    entry = json.loads(run('findmnt', '-J', '--mountpoint', str(path), '-o', 'UUID,FSTYPE,OPTIONS'))['filesystems'][0]
    if ((uuid and entry['uuid'] != uuid) or (fstype and entry['fstype'] != fstype)
            or mode not in entry['options'].split(',')):
        raise ValueError('Unerwarteter Mount: '+str(path))


def prefix_hash(path, size):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while size:
            block = stream.read(min(size, 1024*1024))
            if not block:
                raise ValueError('Archiv kuerzer als gesicherter Praefix')
            h.update(block)
            size -= len(block)
    return h.hexdigest()


def overlay_cmdline(old):
    if re.findall(rb'overlayroot=\S+', old) != [b'overlayroot=disabled']:
        raise ValueError('Erwartet genau overlayroot=disabled')
    if len(old.splitlines()) != 1:
        raise ValueError('Boot-Kommandozeile ist nicht einzeilig')
    return old.replace(b'overlayroot=disabled', b'overlayroot=tmpfs:recurse=0')


def status():
    result = json.loads(run('python3', HELPER, 'status'))
    if result['needs_attention'] or result.get('checkpoint_interval_minutes') != 360:
        raise ValueError('RAM-Status oder Sechs-Stunden-Plan nicht bereit')
    return result


def prepare():
    mount('/', ROOT_UUID, 'ext4', 'rw')
    mount(BOOT, BOOT_UUID, 'vfat')
    mount('/srv/meteohub-persist', PERSIST_UUID, 'ext4')
    status()
    if run('timedatectl', 'show', '-p', 'NTPSynchronized', '--value').strip() != 'yes':
        raise ValueError('Zeit noch nicht synchronisiert')
    environment = run('systemctl', 'show', 'systemd-remount-fs.service', '-p', 'Environment', '--value')
    if 'LIBMOUNT_FORCE_MOUNT2=always' not in environment:
        raise ValueError('Permanenter Overlay-Remount-Workaround fehlt')
    if not Path('/lib/modules/'+os.uname().release).is_dir() or not (BOOT/'initramfs8').is_file():
        raise ValueError('Kernelmodule oder Pi-Initramfs fehlt')
    if CMD.is_symlink():
        raise ValueError('Bootdatei ist ein Symlink')
    old = CMD.read_bytes()
    new = overlay_cmdline(old)
    folder = Path(tempfile.mkdtemp(prefix='meteohub-root-ro-before-', dir='/root'))
    (folder/'cmdline.txt').write_bytes(old)
    (folder/'journal.txt').write_text(run('journalctl', '-b', '--no-pager'))
    (folder/'mounts.txt').write_text(run('findmnt'))
    (folder/'logger-unit.txt').write_text(run('systemctl', 'cat', 'meteohub-live-logger.service'))
    # Save current data explicitly before the boot change; normal shutdown also saves.
    run('systemctl', 'start', 'meteohub-ram-checkpoint.service')
    if run('systemctl', 'show', 'meteohub-ram-checkpoint.service', '-p', 'Result', '--value').strip() != 'success':
        raise ValueError('Sicherung fehlgeschlagen; Bootdatei unveraendert')
    state = status()
    import time
    raw = RUNTIME / 'root/data/weather' / time.strftime('%Y%m', time.gmtime()) / 'raw'
    size = raw.stat().st_size
    if not size:
        raise ValueError('Roharchiv leer')
    proof = {'boot_id': BOOTID.read_text(), 'backup': str(folder), 'archive': str(raw),
             'bytes': size, 'sha256': prefix_hash(raw, size), 'status': state}
    (folder/'proof.json').write_text(json.dumps(proof, indent=2)+'\n')
    POINTER.write_text(json.dumps(proof, indent=2)+'\n')
    run('sync', '-f', str(folder))
    run('mount', '-o', 'remount,rw', str(BOOT))
    try:
        if CMD.read_bytes() != old:
            raise ValueError('Bootdatei wurde zwischenzeitlich geaendert')
        try:
            with CMD.open('wb') as stream:
                stream.write(new); stream.flush(); os.fsync(stream.fileno())
            if CMD.read_bytes() != new:
                raise ValueError('Bootdatei-Ruecklesepruefung fehlgeschlagen')
            run('sync', '-f', str(BOOT))
        except BaseException:
            CMD.write_bytes(old)
            run('sync', '-f', str(BOOT))
            raise
    finally:
        run('mount', '-o', 'remount,ro', str(BOOT))
    mount(BOOT, BOOT_UUID, 'vfat')
    mount('/srv/meteohub-persist', PERSIST_UUID, 'ext4')
    print('VORBEREITET. Sicherung und Diagnose:', folder)
    print('Rueckweg: auf der Bootpartition in cmdline.txt nur overlayroot=tmpfs:recurse=0 durch overlayroot=disabled ersetzen.')
    print('Jetzt regulaer neu starten: systemctl reboot')
    print('Danach dieses Skript mit check aufrufen. Kein automatischer Reboot ausgefuehrt.')


def check():
    proof = json.loads(POINTER.read_text())
    if BOOTID.read_text() == proof['boot_id']:
        raise ValueError('Noch kein neuer Boot')
    mount('/', fstype='overlay', mode='rw')
    mount('/media/root-ro', ROOT_UUID, 'ext4')
    mount('/media/root-rw', fstype='tmpfs', mode='rw')
    mount(BOOT, BOOT_UUID, 'vfat')
    mount('/srv/meteohub-persist', PERSIST_UUID, 'ext4')
    state = status()
    if prefix_hash(Path(proof['archive']), proof['bytes']) != proof['sha256']:
        raise ValueError('Archivpraefix nicht unveraendert wiederhergestellt')
    if run('systemctl', 'show', 'systemd-remount-fs.service', '-p', 'Result', '--value').strip() != 'success':
        raise ValueError('Remount-Dienst nicht erfolgreich')
    print('PASS: neuer Boot, Root-Unterlage/Boot/Persistenz RO, Host-Overlay und RAM aktiv.')
    print('PASS: Archivpraefix erhalten; vier Anwendungen aktiv; Sechs-Stunden-Plan erhalten.')
    print(json.dumps(state, indent=2))
    print(run('systemctl', '--failed', '--no-pager'))
    print(run('systemctl', 'list-timers', '--all', '--no-pager', '--full', 'meteohub-ram-*'))
    print(run('sudo', '-H', '-u', 'meteohub', '--', 'python3',
              '/home/meteohub/src/meteohub/tools/observe-archive.py', str(RUNTIME), '--duration', '0'))
    print('Frische Daten nach diesem Boot und native Aktivierungsanzeige separat beurteilen.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'check'))
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Bitte als root ausfuehren')
    os.umask(0o077)
    try:
        prepare() if args.action == 'prepare' else check()
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        raise SystemExit('STOP: '+str(error))
