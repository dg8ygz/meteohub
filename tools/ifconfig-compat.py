#!/usr/bin/python3
"""Read-only legacy ifconfig display for Meteohub; private bind mount only.

Uses the current network namespace and real iproute2 JSON data. Does not
configure interfaces, invent identifiers, or replace the host's ifconfig.
Only listing, -a, and an explicit interface/IPv4 label are supported.
"""
import ipaddress
import json
import re
import subprocess
import sys


def selection(args):
    if args == []: return None, False
    if args == ['-a']: return None, True
    if len(args) == 1 and re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.:@-]{0,63}', args[0]):
        return args[0], True
    raise ValueError('Only read-only interface queries are supported')


def render(rows, requested=None, all_interfaces=False):
    blocks = []
    for row in rows:
        name = row['ifname']
        flags = row['flags']
        addresses = row.get('addr_info', [])
        labels = list(dict.fromkeys([name] + [a['label'] for a in addresses
                                             if a.get('family') == 'inet' and a.get('label')]))
        for label in labels:
            if requested is not None and requested != label: continue
            if not all_interfaces and 'UP' not in flags: continue
            kind = row['link_type']
            encap = {'ether': 'Ethernet', 'loopback': 'Local Loopback'}.get(kind, kind)
            header = f'{label:<10}Link encap:{encap}'
            if kind == 'ether':
                mac = row['address']
                if not re.fullmatch(r'(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}', mac):
                    raise ValueError('Invalid Ethernet address in ip output')
                header += '  HWaddr ' + mac
            lines = [header]
            # Classic ifconfig exposes one IPv4 address per interface/label.
            v4 = next((a for a in addresses if a.get('family') == 'inet'
                       and a.get('label', name) == label), None)
            if v4:
                local = str(ipaddress.IPv4Address(v4['local']))
                mask = ipaddress.IPv4Network((local, int(v4['prefixlen'])), strict=False).netmask
                line = '          inet addr:' + local
                if v4.get('broadcast'): line += '  Bcast:' + str(ipaddress.IPv4Address(v4['broadcast']))
                if v4.get('peer'): line += '  P-t-P:' + str(ipaddress.IPv4Interface(v4['peer']).ip)
                lines.append(line + '  Mask:' + str(mask))
            if label == name:
                for a in addresses:
                    if a.get('family') != 'inet6': continue
                    address = ipaddress.IPv6Interface(f"{a['local']}/{a['prefixlen']}")
                    scope = {'link': 'Link', 'host': 'Host', 'global': 'Global'}.get(a.get('scope'), a.get('scope', ''))
                    lines.append(f'          inet6 addr: {address}  Scope:{scope}')
            old_flags = [f for f in flags if f in ('UP', 'BROADCAST', 'LOOPBACK', 'POINTOPOINT', 'MULTICAST', 'NOARP', 'PROMISC')]
            if 'LOWER_UP' in flags and 'UP' in flags: old_flags.append('RUNNING')
            lines.append('          ' + ' '.join(old_flags) + '  MTU:' + str(int(row['mtu'])))
            blocks.append('\n'.join(lines))
    if requested is not None and not blocks:
        raise ValueError('Interface or address label not found: ' + requested)
    return '\n\n'.join(blocks) + ('\n' if blocks else '')


def main(args):
    requested, all_interfaces = selection(args)
    # No caller argument is passed to ip; there is no configuration command path.
    result = subprocess.run(['/usr/sbin/ip', '-j', 'address', 'show'],
                            capture_output=True, text=True, check=True, timeout=5)
    rows = json.loads(result.stdout)
    if not isinstance(rows, list): raise ValueError('Invalid ip JSON output')
    output = render(rows, requested, all_interfaces)
    sys.stdout.write(output)


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print('meteohub ifconfig display: ' + str(error), file=sys.stderr)
        sys.exit(1)
