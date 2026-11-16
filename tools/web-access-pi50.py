#!/usr/bin/env python3
"""Locally toggle a subnet-restricted LAN proxy for the private Meteohub web UI."""
import argparse
import fcntl
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HOST = '44.149.114.50'
LAN = '44.149.114.0/26'
PORT = 18090
BOOT_UUID = 'B2F0-82D2'
NAME = 'meteohub-web-lan'
TABLE = 'meteohub_web_lan'
MARK = 'meteohub-web-access-v1'
UNITS = Path('/run/systemd/system')
INSTALLED = Path('/boot/firmware/meteohub-web-access.py')
PROXY = '/usr/lib/systemd/systemd-socket-proxyd'
NFT = '/usr/sbin/nft'


def run(args, *, text=None, check=True):
    return subprocess.run(args, input=text, text=True, capture_output=True,
                          check=check, timeout=45)


def systemctl(*args, check=True):
    return run(['systemctl', *args], check=check).stdout.strip()


def http_status(host):
    conn = http.client.HTTPConnection(host, PORT, timeout=5)
    try:
        conn.request('GET', '/')
        reply = conn.getresponse()
        return reply.status, reply.getheader('WWW-Authenticate', '')
    finally:
        conn.close()


def nft_table():
    data = json.loads(run([NFT, '-j', 'list', 'ruleset']).stdout)
    for item in data['nftables']:
        table = item.get('table', {})
        if table.get('name') == TABLE and table.get('family') == 'inet':
            if table.get('comment') != MARK:
                raise RuntimeError('Fremde Firewall-Tabelle gleichen Namens; nicht veraendert.')
            return True
    return False


def verify_owned_units():
    for ext in ('socket', 'service'):
        name = NAME + '.' + ext
        for parent in (Path('/etc/systemd/system'), Path('/usr/lib/systemd/system')):
            if (parent / name).exists() or (parent / name).is_symlink():
                raise RuntimeError('Unerwartete permanente Unit: ' + str(parent / name))
        path = UNITS / name
        if path.is_symlink() or (path.exists() and not path.read_text().startswith('# ' + MARK + '\n')):
            raise RuntimeError('Fremde Unit: ' + str(path))
        for parent in (UNITS, Path('/etc/systemd/system'), Path('/usr/lib/systemd/system')):
            if (parent / (name + '.d')).exists():
                raise RuntimeError('Unerwartete Drop-ins: ' + str(parent / (name + '.d')))


def stop_proxy():
    for ext in ('socket', 'service'):
        unit = NAME + '.' + ext
        load = systemctl('show', unit, '-p', 'LoadState', '--value', check=False)
        if load not in ('', 'not-found'):
            systemctl('stop', unit)
        state = systemctl('is-active', unit, check=False)
        if state in ('active', 'activating', 'deactivating'):
            raise RuntimeError('Proxy noch aktiv; Firewall bleibt bestehen.')


def close_lan():
    verify_owned_units()
    # Never remove the guard while the LAN listener or existing connections live.
    stop_proxy()
    if nft_table():
        run([NFT, 'delete', 'table', 'inet', TABLE])
    for ext in ('socket', 'service'):
        (UNITS / (NAME + '.' + ext)).unlink(missing_ok=True)
    systemctl('daemon-reload')
    print('LOCAL: LAN-Zugang geschlossen. Weboberflaeche bleibt unter 127.0.0.1:18090 erreichbar.')


def open_lan():
    verify_owned_units()
    existing = nft_table()
    interfaces = json.loads(run(['ip', '-j', '-4', 'address', 'show', 'dev', 'eth0']).stdout)
    if not any(a.get('local') == HOST and a.get('prefixlen') == 26
               for i in interfaces for a in i.get('addr_info', [])):
        raise RuntimeError('eth0 muss 44.149.114.50/26 besitzen; keine Freigabe erfolgt.')
    if not os.access(PROXY, os.X_OK):
        raise RuntimeError('systemd-socket-proxyd fehlt.')
    code, challenge = http_status('127.0.0.1')
    if code != 401 or 'Basic ' not in challenge:
        raise RuntimeError('Passwortschutz des lokalen Webdienstes nicht bestaetigt (HTTP %s).' % code)
    guard = (('delete table inet ' + TABLE + '\n') if existing else '') + '''table inet %s {
 comment "%s"
 chain input {
  type filter hook input priority -5; policy accept;
  ip daddr %s tcp dport %s ip saddr != %s counter drop
 }
}
''' % (TABLE, MARK, HOST, PORT, LAN)
    run([NFT, '-c', '-f', '-'], text=guard)
    socket = '''# %s
[Unit]
Description=Meteohub LAN web access (temporary local switch)
[Socket]
ListenStream=%s:%s
Accept=no
NoDelay=yes
IPAddressDeny=any
IPAddressAllow=%s
''' % (MARK, HOST, PORT, LAN)
    service = '''# %s
[Unit]
Description=Meteohub LAN to loopback HTTP proxy
Requires=%s.socket
After=%s.socket
[Service]
Type=notify
ExecStart=%s --connections-max=16 127.0.0.1:%s
DynamicUser=yes
NoNewPrivileges=yes
CapabilityBoundingSet=
PrivateTmp=yes
PrivateDevices=yes
ProtectSystem=strict
ProtectHome=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictSUIDSGID=yes
RestrictAddressFamilies=AF_INET AF_UNIX
IPAddressDeny=any
IPAddressAllow=127.0.0.0/8 %s
MemoryMax=32M
TasksMax=16
Restart=on-failure
RestartSec=2s
''' % (MARK, NAME, NAME, PROXY, PORT, LAN)
    stop_proxy()
    try:
        # Install the network guard before creating a LAN listener.
        run([NFT, '-f', '-'], text=guard)
        for ext, data in (('socket', socket), ('service', service)):
            path = UNITS / (NAME + '.' + ext)
            path.write_text(data)
            path.chmod(0o644)
        systemctl('daemon-reload')
        systemctl('start', NAME + '.socket')
        if http_status(HOST)[0] != 401:
            raise RuntimeError('LAN-Passwortabfrage fehlgeschlagen.')
    except BaseException:
        close_lan()
        raise
    print('LAN: http://%s:%s/ fuer %s freigegeben; vorhandenes Webpasswort bleibt erforderlich.' % (HOST, PORT, LAN))
    print('Gilt bis local oder Neustart. Logger und bestehender Webdienst wurden nicht neu gestartet.')


def install():
    uuid = run(['findmnt', '-nro', 'UUID', '--mountpoint', '/boot/firmware']).stdout.strip()
    if uuid != BOOT_UUID:
        raise RuntimeError('Unerwartete Bootpartition; Installation abgebrochen.')
    source = Path(__file__).resolve().read_bytes()
    if INSTALLED.exists():
        if INSTALLED.read_bytes() == source:
            print('Schalter bereits dauerhaft unter ' + str(INSTALLED) + ' vorhanden.')
            return
        raise RuntimeError('Andere Version vorhanden; nicht ueberschrieben: ' + str(INSTALLED))
    options = run(['findmnt', '-nro', 'OPTIONS', '--mountpoint', '/boot/firmware']).stdout.strip().split(',')
    was_ro = 'ro' in options
    temp = None
    try:
        if was_ro:
            run(['mount', '-o', 'remount,rw', '/boot/firmware'])
        fd, temp = tempfile.mkstemp(prefix='.meteohub-web-access-', dir=INSTALLED.parent)
        with os.fdopen(fd, 'wb') as f:
            f.write(source)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, INSTALLED)
        temp = None
        run(['sync', '-f', str(INSTALLED)])
    finally:
        if temp:
            Path(temp).unlink(missing_ok=True)
        if was_ro:
            run(['mount', '-o', 'remount,ro', '/boot/firmware'])
    if INSTALLED.read_bytes() != source:
        raise RuntimeError('Installierte Datei stimmt nicht ueberein.')
    print('Schalter dauerhaft installiert: ' + str(INSTALLED))
    print('Bootparameter unveraendert. Nach jedem Neustart gilt weiterhin nur localhost.')


def status():
    state = systemctl('is-active', NAME + '.socket', check=False)
    guarded = nft_table()
    print('LAN-Socket: ' + state)
    print('Eigene LAN-Firewallregel: ' + ('vorhanden' if guarded else 'nicht vorhanden'))
    print('LAN-Adresse: http://%s:%s/; erlaubtes Netz: %s' % (HOST, PORT, LAN))
    print('Localhost HTTP: ' + str(http_status('127.0.0.1')[0]))
    print('Schalter dauerhaft installiert: ' + str(INSTALLED.exists()))
    if state == 'active' and not guarded:
        raise RuntimeError('LAN-Socket aktiv, aber Firewallregel fehlt; bitte local ausfuehren.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('install', 'lan', 'local', 'status'))
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise RuntimeError('Bitte lokal mit sudo/root ausfuehren.')
    os.umask(0o077)
    with open('/run/lock/meteohub-web-access.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        {'install': install, 'lan': open_lan, 'local': close_lan, 'status': status}[args.action]()


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print('STOP: ' + (exc.stderr or exc.stdout or str(exc)).strip(), file=sys.stderr)
        sys.exit(1)
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        print('STOP: ' + str(exc), file=sys.stderr)
        sys.exit(1)
