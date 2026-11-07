#!/usr/bin/env python3
"""Network settings and an actual denial check for the bounded native TCP test."""
import errno
import json
import os
import socket
import subprocess
import time


def policy(host=None):
    return ['PrivateNetwork=no','IPAddressDeny=any',
            'IPAddressAllow=127.0.0.0/8'+(' '+host if host else ''),
            'RestrictAddressFamilies=AF_INET AF_UNIX']


def check_filter(properties, host=None):
    """Check real cgroup IP filtering before exposing legacy code to host networking.

    Connect only to listeners created on this machine, never to the source.
    First allow that same endpoint in a control run. Refusal is not accepted
    as proof of filtering; cgroup packet drops may report a timeout.
    """
    rows=json.loads(subprocess.check_output(['ip','-j','-4','address','show','scope','global'],text=True))
    addresses=[a['local'] for row in rows for a in row.get('addr_info',[]) if a.get('family')=='inet' and a['local']!=host]
    if not addresses:raise ValueError('Need a local non-loopback IPv4 different from the source for the network-filter check')
    address=addresses[0]
    with socket.socket() as allowed, socket.socket() as denied:
        allowed.bind(('127.0.0.1',0));allowed.listen(1)
        denied.bind((address,0));denied.listen(1)
        script='''import errno,os,socket,sys
assert os.geteuid()!=0
with socket.create_connection(('127.0.0.1',int(sys.argv[1])),timeout=3):pass
if sys.argv[4]=='allow':
 with socket.create_connection((sys.argv[2],int(sys.argv[3])),timeout=3):pass
 print('PASS: non-loopback control endpoint reachable with explicit allow')
 raise SystemExit(0)
try:
 s=socket.create_connection((sys.argv[2],int(sys.argv[3])),timeout=3)
except OSError as e:
 assert isinstance(e,TimeoutError) or e.errno in (errno.EPERM,errno.EACCES), repr(e)
else:
 s.close();raise SystemExit('IP FILTER NOT ENFORCED')
print('PASS: real loopback connection allowed; local non-loopback connection denied by kernel')
'''
        props=[p for p in properties if not p.startswith(('RuntimeMaxSec=','JoinsNamespaceOf=','PrivateNetwork=','IPAddressDeny=','IPAddressAllow=','RestrictAddressFamilies='))]
        props+=policy(host)+['RuntimeMaxSec=15s']
        for mode in ('allow','deny'):
            command=['sudo','-n','systemd-run','--wait','--pipe','--collect',
                     '--unit=meteohub-network-check-'+str(time.time_ns()),
                     '--uid='+str(os.getuid()),'--gid='+str(os.getgid()),'--expand-environment=no']
            command+=['--property='+p+(' '+address if mode=='allow' and p.startswith('IPAddressAllow=') else '') for p in props]
            command+=['/usr/bin/python3','-c',script,str(allowed.getsockname()[1]),address,str(denied.getsockname()[1]),mode]
            subprocess.run(command,check=True,timeout=25)
