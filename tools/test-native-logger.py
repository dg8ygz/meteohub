#!/usr/bin/env python3
"""Bounded real TCP -> installed plugin -> native logger test in the private runtime.

No boot installation. New fresh raw records and an active TCP source are required for success.
"""
import argparse
import datetime
import fcntl
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

TOOLS = Path(__file__).resolve().parent


def load(name):
    spec=importlib.util.spec_from_file_location(name,TOOLS/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def config_copy(source):
    load('prepare-tcp-plugin').check_config(source)
    result=[]
    for line in source.read_text().splitlines():
        parts=line.split()
        if parts and parts[0] in ('@INETUPLOADFREQ','@INETUPLOADFREQRAPID','@LIVEUPLOADFREQ'):
            line=parts[0]+' 0'
        result.append(line)
    return '\n'.join(result)+'\n'


def archive_snapshot(directory):
    result={}
    for path in directory.glob('*/raw'):
        if path.is_symlink() or path.parent.is_symlink() or not path.is_file():
            raise ValueError('Unexpected linked/nonregular raw archive')
        result[str(path.relative_to(directory))]=[path.stat().st_ino,path.stat().st_size]
    return result


def archive_result(directory,before,started):
    result={'fresh_raw_records':0,'sensors':{},'invalid_new_lines':0,'truncated_or_replaced':[], 'files':[]}
    now=time.time()
    for path in directory.glob('*/raw'):
        if path.is_symlink() or path.parent.is_symlink():raise ValueError('Linked archive refused')
        relative=str(path.relative_to(directory));info=path.stat()
        old=before.get(relative)
        if old and (old[0]!=info.st_ino or info.st_size<old[1]):
            result['truncated_or_replaced'].append(relative);continue
        offset=old[1] if old else 0
        if info.st_size-offset>16*1024*1024:raise ValueError('Unexpected raw growth exceeds 16 MiB')
        with path.open('rb') as stream:
            stream.seek(offset)
            for line in stream:
                fields=line.decode('ascii',errors='replace').split()
                try:
                    if not line.endswith(b'\n') or len(fields)<3 or not re.fullmatch(r'\d{14}',fields[0]):raise ValueError()
                    stamp=datetime.datetime.strptime(fields[0],'%Y%m%d%H%M%S').replace(tzinfo=datetime.timezone.utc).timestamp()
                    if not re.fullmatch(r'(?:t|th|thb|wind|rain|uv|sol|data)\d+',fields[1]):raise ValueError()
                    if any(not re.fullmatch(r'-?\d+',value) for value in fields[2:]):raise ValueError()
                    if started-5<=stamp<=now+5:
                        result['fresh_raw_records']+=1
                        result['sensors'][fields[1]]=result['sensors'].get(fields[1],0)+1
                except ValueError:result['invalid_new_lines']+=1
        if info.st_size>offset:result['files'].append({'path':relative,'bytes_added':info.st_size-offset})
    return result


def logger_properties(candidate,runtime,duration,web_unit='meteohub-web-test.service'):
    props=load('probe-cgi').properties(candidate,runtime)
    props=[p for p in props if not p.startswith(('RuntimeMaxSec=','TemporaryFileSystem=','LimitFSIZE=','TimeoutStopSec='))]
    return props+['JoinsNamespaceOf='+web_unit,'RuntimeMaxSec='+str(duration)+'s','TimeoutStopSec=10s',
                  'TemporaryFileSystem=/run:rw','LimitFSIZE=32M']


def collector_properties(runtime,host,duration):
    return ['Type=exec','RuntimeMaxSec='+str(duration+30)+'s','TimeoutStopSec=10s',
            'KillMode=control-group','NoNewPrivileges=yes','CapabilityBoundingSet=',
            'PrivateDevices=yes','PrivateTmp=yes','ProtectSystem=strict','ProtectHome=read-only',
            'ProtectKernelTunables=yes','ProtectKernelModules=yes','ProtectControlGroups=yes',
            'UMask=0077','MemoryMax=96M','TasksMax=16','CPUQuota=25%','LimitCORE=0','LimitFSIZE=16M',
            'RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX','IPAddressDeny=any','IPAddressAllow='+host,
            'ReadWritePaths='+str(runtime/'root/data/tcp-feed')]


def unit_command(unit,props):
    return ['sudo','-n','systemd-run','--unit='+unit,'--uid='+str(os.getuid()),
            '--gid='+str(os.getgid()),'--expand-environment=no']+['--property='+p for p in props]


def run_test(candidate,runtime,host,port,duration):
    host=str(ipaddress.ip_address(host)) # Explicit IP avoids DNS or shell interpretation.
    load('web-test').check_paths(candidate,runtime)
    load('prepare-tcp-plugin').verify_prepared(runtime)
    weather=runtime/'root/data/weather'
    if weather.is_symlink() or not weather.is_dir():raise ValueError('Missing/linked weather directory')
    before=archive_snapshot(weather)
    web_status=subprocess.run(['systemctl','show','meteohub-web-test.service','-p','ActiveState',
                               '-p','RootDirectory','-p','User','-p','PrivateNetwork'],text=True,capture_output=True,check=True)
    web_fields=dict(line.split('=',1) for line in web_status.stdout.splitlines() if '=' in line)
    if (web_fields.get('ActiveState')!='active' or web_fields.get('RootDirectory')!=str(runtime/'root')
        or web_fields.get('User')!=str(os.getuid()) or web_fields.get('PrivateNetwork')!='yes'):
        raise ValueError('Start/open the matching isolated website first; refusing a foreign network namespace')
    # Same lock also guards feed-test. Prevent two consumers of the same cursor.
    fd=os.open(runtime/'.feed-consumer.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        subprocess.run(['sudo','-v'],check=True)
        report=Path(tempfile.mkdtemp(prefix='native-logger-test-',dir=candidate.parent))
        shutil.copytree(runtime/'root/home/meteohub',report/'home-before',symlinks=True)
        config=config_copy(runtime/'root/home/meteohub/logger.conf')
        (report/'logger.conf').write_text(config)
        (report/'archive-before.json').write_text(json.dumps(before,indent=2)+'\n')
        (report/'collector.py').write_bytes((TOOLS/'tcp-feed.py').read_bytes())
        native='meteohub-native-check-'+str(time.time_ns())
        collector=native+'-tcp'
        started=time.time();native_exit=None
        print('REPORT:',report,flush=True)
        print('Starting real TCP collector and native logger for',duration,'seconds; no autostart.',flush=True)
        # Isolation preflight does not run the native application.
        subprocess.run(['python3',str(TOOLS/'probe-cgi.py'),str(candidate),'--runtime',str(runtime),
                        '--isolation-only'],check=True)
        def journal(unit,name):
            with (report/name).open('w') as stream:
                subprocess.run(['sudo','-n','journalctl','-u',unit+'.service','--no-pager','-o','short-iso'],stdout=stream,check=False)
        try:
            command=unit_command(collector,collector_properties(runtime,host,duration))
            command+=['/usr/bin/python3',str(report/'collector.py'),'--host',host,'--port',str(port),
                      '--duration',str(duration+20),'--output',str(runtime/'root/data/tcp-feed/feed.json')]
            subprocess.run(command,check=True)
            # A private read-only config bind avoids replacing the native UI settings.
            props=logger_properties(candidate,runtime,duration)
            props+=['BindReadOnlyPaths='+str(report/'logger.conf')+':/home/meteohub/logger-check.conf']
            command=unit_command(native,props)+['--wait','--pipe']
            command+=['/usr/bin/env','-i','PATH=/usr/bin:/bin','HOME=/home/meteohub','LANG=C',
                      'LD_BIND_NOW=1','LD_LIBRARY_PATH=/home/meteohub/lib:/usr/lib/arm-linux-gnueabihf',
                      '/home/meteohub/bin/loggerd','-n','-c','/home/meteohub/logger-check.conf']
            with (report/'stdout.txt').open('w') as out,(report/'stderr.txt').open('w') as err:
                result=subprocess.run(command,stdout=out,stderr=err,timeout=duration+45,check=False)
                native_exit=result.returncode
        finally:
            # Only our two unique units; no blanket killall or source changes.
            subprocess.run(['sudo','-n','systemctl','stop',native+'.service',collector+'.service'],capture_output=True,check=False)
            journal(native,'native-journal.txt');journal(collector,'collector-journal.txt')
        status=subprocess.run(['systemctl','show',native+'.service','-p','Result','-p','ExecMainStatus',
                               '-p','ExecMainCode','-p','ActiveState'],capture_output=True,text=True,check=False)
        (report/'unit-status.txt').write_text(status.stdout)
        records=archive_result(weather,before,started)
        collector_status=runtime/'root/data/tcp-feed/feed.status.json'
        tcp=json.loads(collector_status.read_text()) if collector_status.exists() and collector_status.stat().st_mtime>=started else {}
        records['tcp_records']=tcp.get('records',0)
        records['tcp_rejected']=tcp.get('rejected',0)
        records.update(systemd_run_exit=native_exit,duration_seconds=round(time.time()-started,2),
                       logger_status=status.stdout.strip().splitlines(),boot_enabled=False)
        records['archive_observed']=records['fresh_raw_records']>0 and not records['invalid_new_lines'] and not records['truncated_or_replaced']
        (report/'result.json').write_text(json.dumps(records,indent=2)+'\n')
        print(json.dumps(records,indent=2),flush=True)
        # A cgroup timeout is expected; crashes, early exit and missing archive are not.
        ok=records['archive_observed'] and records['tcp_records']>0 and 'Result=timeout' in status.stdout.splitlines() and records['duration_seconds']>=duration
        print('PASS: new native raw records observed; bounded test ended.' if ok else
              'NOT ACCEPTED: inspect private stderr/native-journal; service status alone is insufficient.',flush=True)
        print('Collector and native logger stopped. No ongoing collection or boot installation.',flush=True)
        for unit in (native,collector):
            subprocess.run(['sudo','-n','systemctl','reset-failed',unit+'.service'],capture_output=True,check=False)
        return 0 if ok else 3


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate',type=Path);parser.add_argument('runtime',type=Path)
    parser.add_argument('--host',required=True);parser.add_argument('--port',type=int,default=5500)
    parser.add_argument('--duration',type=int,default=180)
    args=parser.parse_args()
    if os.geteuid()==0:parser.error('Run as the normal application user')
    if not 1<=args.port<=65535 or not 60<=args.duration<=600:parser.error('Invalid port or duration')
    os.umask(0o077)
    return run_test(args.candidate.resolve(strict=True),args.runtime.resolve(strict=True),args.host,args.port,args.duration)


if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError,subprocess.SubprocessError) as error:raise SystemExit('STOP: '+str(error))
