#!/usr/bin/env python3
"""Bounded original logger -> original Meteohub TCP test; no input plugin/collector."""
import argparse
import fcntl
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


def load(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


native=load('test-native-logger')
web=load('web-test')
network=load('direct-network')


def config_copy(path,host,port):
    host=str(ipaddress.IPv4Address(host))
    if not 1<=port<=65535:raise ValueError('Invalid source port')
    if path.is_symlink() or not path.is_file() or path.stat().st_size>262144:
        raise ValueError('Generate a regular private logger.conf first')
    lines=path.read_text().splitlines();entries=[s.split() for s in lines if s.split()]
    stations=[p for p in entries if p[0]=='@WEATHERSTATION']
    if len(stations)!=1 or stations[0][:5]!=['@WEATHERSTATION','0','9','4',host+':'+str(port)]:
        raise ValueError('Select station 0 User-defined / TCP/IP Meteohub with the requested IP:port, Save, then regenerate logger.conf')
    for key,value in (('@DATAPATH','/data/weather/'),('@ERRORLOG','/data/log/meteohub.log')):
        if [p for p in entries if p[0]==key]!=[[key,value]]:
            raise ValueError('Unexpected private archive/log path')
    result=[]
    for line in lines:
        parts=line.split()
        if parts and parts[0] in ('@INETUPLOADFREQ','@INETUPLOADFREQRAPID','@LIVEUPLOADFREQ'):
            line=parts[0]+' 0'
        result.append(line)
    return '\n'.join(result)+'\n'


def logger_properties(candidate,runtime,host,duration):
    props=native.logger_properties(candidate,runtime,duration)
    props=[p for p in props if not p.startswith(('PrivateNetwork=','JoinsNamespaceOf='))]
    return props+network.policy(host)


def web_state(runtime):
    result=subprocess.run(['systemctl','show',web.UNIT+'.service','-p','ActiveState','-p','User',
                           '-p','RootDirectory','-p','PrivateNetwork'],capture_output=True,text=True,check=True)
    fields=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
    if fields.get('ActiveState')!='active' or fields.get('User')!=str(os.getuid()) or fields.get('RootDirectory')!=str(runtime/'root'):
        raise ValueError('Open the matching private test website first; refusing another web runtime')
    if fields.get('PrivateNetwork')!='yes':
        raise ValueError('Expected the regular private-network website before the temporary direct test')


def stop_web():
    units=[]
    for suffix in ('.socket','.service'):
        unit=web.UNIT+suffix
        state=subprocess.run(['systemctl','show',unit,'-p','LoadState','--value'],capture_output=True,text=True).stdout.strip()
        if state!='not-found':units.append(unit)
    if units:subprocess.run(['sudo','-n','systemctl','stop',*units],check=True)
    for unused in range(40):
        states=[subprocess.run(['systemctl','show',web.UNIT+suffix,'-p','LoadState','--value'],capture_output=True,text=True).stdout.strip()
                for suffix in ('.socket','.service')]
        if all(state=='not-found' for state in states):return
        time.sleep(.25)
    raise ValueError('Web test units did not unload; inspect them before retrying')


def run_test(candidate,runtime,host,port,duration):
    host=str(ipaddress.IPv4Address(host))
    web.check_paths(candidate,runtime)
    config=config_copy(runtime/'root/home/meteohub/logger.conf',host,port)
    web_state(runtime)
    weather=runtime/'root/data/weather'
    if weather.is_symlink() or not weather.is_dir():raise ValueError('Missing/linked archive directory')
    fd=os.open(runtime/'.feed-consumer.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        subprocess.run(['sudo','-v'],check=True)
        report=Path(tempfile.mkdtemp(prefix='native-direct-test-',dir=candidate.parent))
        shutil.copytree(runtime/'root/home/meteohub',report/'home-before',symlinks=True)
        (report/'logger.conf').write_text(config)
        before=native.archive_snapshot(weather)
        (report/'archive-before.json').write_text(json.dumps(before,indent=2)+'\n')
        props=logger_properties(candidate,runtime,host,duration)
        print('REPORT:',report,flush=True)
        print('DIRECT: original logger connects to',host+':'+str(port),'; no JSON, input plugin or collector.',flush=True)
        # Check enforcement before allowing the original application host networking.
        network.check_filter(web.web_properties(candidate,runtime,True))
        network.check_filter(props,host)
        unit='meteohub-direct-check-'+str(time.time_ns())
        changed_web=False;started=None;exitcode=None
        try:
            changed_web=True
            stop_web()
            web.start(candidate,runtime,host_network=True)
            props+=['BindReadOnlyPaths='+str(report/'logger.conf')+':/home/meteohub/logger-check.conf']
            command=native.unit_command(unit,props)+['--wait','--pipe',
                '/usr/bin/env','-i','PATH=/usr/bin:/bin','HOME=/home/meteohub','LANG=C',
                'LD_BIND_NOW=1','LD_LIBRARY_PATH=/home/meteohub/lib:/usr/lib/arm-linux-gnueabihf',
                '/home/meteohub/bin/loggerd','-n','-c','/home/meteohub/logger-check.conf']
            print('RUNNING:',duration,'seconds. Sensors: assign THB channel 0 to thb0 and Save if not yet assigned.',flush=True)
            print('This run uses a fixed config copy; regenerate after saving for the next archive test.',flush=True)
            started=time.time()
            with (report/'stdout.txt').open('w') as out,(report/'stderr.txt').open('w') as err:
                exitcode=subprocess.run(command,stdout=out,stderr=err,timeout=duration+45).returncode
        finally:
            subprocess.run(['sudo','-n','systemctl','stop',unit+'.service'],capture_output=True,check=False)
            with (report/'native-journal.txt').open('w') as stream:
                subprocess.run(['sudo','-n','journalctl','-u',unit+'.service','--no-pager','-o','short-iso'],stdout=stream,check=False)
            if changed_web:
                try:
                    stop_web();web.start(candidate,runtime)
                except Exception:
                    print('WEB RESTORE FAILED: inspect test units; no logger restart attempted. Report:',report,flush=True)
                    raise
        status=subprocess.run(['systemctl','show',unit+'.service','-p','Result','-p','ExecMainStatus','-p','ActiveState'],capture_output=True,text=True)
        (report/'unit-status.txt').write_text(status.stdout)
        result=native.archive_result(weather,before,started)
        result.update(transport='native Meteohub TCP/IP',source=host+':'+str(port),
                      systemd_run_exit=exitcode,logger_status=status.stdout.splitlines(),
                      duration_seconds=round(time.time()-started,2),boot_enabled=False,
                      input_plugin_started=False,collector_started=False,web_private_network_restored=True)
        result['archive_observed']=result['fresh_raw_records']>0 and not result['invalid_new_lines'] and not result['truncated_or_replaced']
        result['pressure_archive_observed']=result['archive_observed'] and result['sensors'].get('thb0',0)>0
        (report/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2),flush=True)
        ok=result['archive_observed'] and 'Result=timeout' in status.stdout.splitlines() and result['duration_seconds']>=duration
        print('PASS: fresh native archive over direct TCP.' if ok else 'NOT ACCEPTED: inspect private native journal and archive.',flush=True)
        print('Native logger stopped; regular private website restored; no ongoing collection or autostart.',flush=True)
        subprocess.run(['sudo','-n','systemctl','reset-failed',unit+'.service'],capture_output=True,check=False)
        return 0 if ok else 3


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate',type=Path);parser.add_argument('runtime',type=Path)
    parser.add_argument('--host',required=True);parser.add_argument('--port',type=int,default=5500)
    parser.add_argument('--duration',type=int,default=300)
    args=parser.parse_args()
    if os.geteuid()==0:parser.error('Run as the normal application user')
    if not 1<=args.port<=65535 or not 60<=args.duration<=600:parser.error('Invalid port/duration')
    os.umask(0o077)
    return run_test(args.candidate.resolve(strict=True),args.runtime.resolve(strict=True),args.host,args.port,args.duration)


if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError,subprocess.SubprocessError) as error:raise SystemExit('STOP: '+str(error))
