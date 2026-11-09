#!/usr/bin/env python3
"""Persistent unit tests with real systemd, synthetic receiver and real lighttpd.

No ARM binary, actual weather station or reboot is involved.
"""
import argparse
import base64
import contextlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error


def load(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

live=load('live-service')
ISOLATION='--isolation' in sys.argv
if ISOLATION:sys.argv.remove('--isolation')
LIGHTTPD=Path('/var/local/meteohub-private/lighttpd-package-review/unpacked/usr/sbin/lighttpd')
MODULES=LIGHTTPD.parent.parent/'lib/lighttpd'


class LiveTests(unittest.TestCase):
    def test_live_remove_refuses_installed_ram_storage(self):
        with tempfile.TemporaryDirectory() as td:
            config=Path(td)/'ram.json';config.write_text('{}')
            with patch.object(live,'RAM_CONFIG',config):
                with self.assertRaisesRegex(ValueError,'RAM storage installed'):
                    live.restore(Path(td),Path(td),{})

    def test_logger_waits_for_clock_without_blocking_web(self):
        with tempfile.TemporaryDirectory() as td:
            runtime=Path(td);(runtime/'live').mkdir()
            (runtime/'live/source.json').write_text('{"host":"192.0.2.1"}')
            probe=live.load('probe-cgi')
            real_load=live.load
            with patch.object(probe,'properties',return_value=[]), patch.object(
                    live,'load',side_effect=lambda n: probe if n=='probe-cgi' else real_load(n)):
                units=live.render(runtime/'candidate',runtime,1000,1000)
            logger=units[live.LOGGER].split('[Service]')[0]
            self.assertIn('Requires='+live.TIME_WAIT+'\n',logger)
            self.assertIn('After='+live.TIME_WAIT+' time-sync.target\n',logger)
            for name in (live.WEB,live.SOCKET,live.INDEX,live.RUNTIME):
                self.assertNotIn(live.TIME_WAIT,units[name])

    def test_acceptance_must_match_source_and_configuration(self):
        with tempfile.TemporaryDirectory() as td:
            top=Path(td);candidate=top/'candidate';candidate.mkdir()
            report=top/'native-direct-test-example';report.mkdir()
            (report/'logger.conf').write_text('configuration')
            result={'source':'192.0.2.1:5500','transport':'native Meteohub TCP/IP','archive_observed':True,
                    'fresh_raw_records':3,'web_private_network_restored':True,'duration_seconds':302,
                    'logger_status':['Result=timeout','ExecMainStatus=0']}
            (report/'result.json').write_text(json.dumps(result))
            self.assertEqual(live.accepted_report(candidate,'configuration','192.0.2.1',5500),str(report))
            for config,host,port in [('changed','192.0.2.1',5500),('configuration','192.0.2.2',5500),('configuration','192.0.2.1',5501)]:
                with self.assertRaises(ValueError):live.accepted_report(candidate,config,host,port)
            result['logger_status']=['Result=exit-code','ExecMainStatus=42']
            (report/'result.json').write_text(json.dumps(result))
            with self.assertRaises(ValueError):live.accepted_report(candidate,'configuration','192.0.2.1',5500)
            result['archive_observed']=False;(report/'result.json').write_text(json.dumps(result))
            with self.assertRaises(ValueError):live.accepted_report(candidate,'configuration','192.0.2.1',5500)

    def test_live_marker_blocks_bounded_receivers_even_when_stopped(self):
        with tempfile.TemporaryDirectory() as td:
            runtime=Path(td);(runtime/live.MARKER).write_text('{}')
            for name in ('test-native-direct','test-native-logger'):
                with self.assertRaisesRegex(ValueError,'Persistent installation'):
                    load(name).run_test(runtime,runtime,'192.0.2.1',5500,60)

    @unittest.skipUnless(ISOLATION,'real systemd integration requires --isolation as root')
    def test_real_persistent_services_restart_lock_http_and_removal(self):
        self.assertEqual(os.geteuid(),0)
        if not LIGHTTPD.exists():self.skipTest('local extracted lighttpd required')
        # Never share the normal web listener or a real receiver runtime.
        with socket.socket() as free:
            free.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);free.bind(('127.0.0.1',18090))
        self.assertFalse(Path('/run/meteohub-live-65534').exists())
        fixture=load('test-runtime');case=fixture.RuntimeTests();case.setUp();self.addCleanup(case.doCleanups)
        top=case.top;runtime=case.runtime;candidate=top/'candidate'
        fixture.stage.materialize(runtime,fixture.stage.prepare(case.image),65534,65534,'fixture')
        (candidate/'bin').mkdir(parents=True);(candidate/'lib').mkdir()
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(4);listener.settimeout(.2)
        port=listener.getsockname()[1];stop=threading.Event();connections=[]
        def source():
            while not stop.is_set():
                try:conn,_=listener.accept()
                except socket.timeout:continue
                except OSError:return
                connections.append(time.time())
                with conn:
                    while not stop.is_set():
                        try:conn.sendall(b'thb0 1289 100 9816\n')
                        except OSError:break
                        stop.wait(.2)
        thread=threading.Thread(target=source,daemon=True);thread.start()
        self.addCleanup(stop.set);self.addCleanup(listener.close)
        config=f'@DATAPATH /data/weather/\n@ERRORLOG /data/log/meteohub.log\n@WEATHERSTATION 0 9 4 127.0.0.1:{port} 0 300 0\n@SENSORIDMAP 0 2 0 0\n'
        stub='''#!/usr/bin/python3
import datetime,pathlib,socket,os
cfg=pathlib.Path('/home/meteohub/logger-live.conf').read_text()
endpoint=next(x.split()[4] for x in cfg.splitlines() if x.startswith('@WEATHERSTATION'))
host,port=endpoint.split(':')
with socket.create_connection((host,int(port)),timeout=5) as s:
 for line in s.makefile('r'):
  now=datetime.datetime.now(datetime.timezone.utc)
  path=pathlib.Path('/data/weather')/now.strftime('%Y%m')/'raw';path.parent.mkdir(exist_ok=True)
  with path.open('a') as out:out.write(now.strftime('%Y%m%d%H%M%S')+' thb0 1289 100 1289 9816 -1 10211\\n')
'''
        entries=[]
        for name in ('bin/loggerd','bin/meteometar','bin/meteonet','bin/meteoschedule','bin/meteohub.cgi','lib/libgcgi.so.0'):
            p=candidate/name
            text=stub if name=='bin/loggerd' else '#!/bin/sh\nprintf "Content-Type: text/plain\\r\\n\\r\\n"\ncat /run/loggerd.pid\n' if name=='bin/meteohub.cgi' else 'not executed'
            p.write_text(text);p.chmod(0o700)
            entries.append({'target':name,'candidate_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        (candidate/'manifest.json').write_text(json.dumps({'files':entries}))
        web=load('web-test');ext=load('extension-update')
        webdir=runtime/'root/opt/meteohub-web';webdir.mkdir();web.write_config(webdir)
        (webdir/'prepared.json').write_text(json.dumps({'schema':1,'uid':65534}))
        subprocess.run(['htpasswd','-ciB',str(webdir/'users.htpasswd'),'meteohub'],input='synthetic-only\n',text=True,check=True,capture_output=True)
        (webdir/'users.htpasswd').chmod(0o600)
        (runtime/'root/srv/www/cgi-bin/meteohub.cgi').symlink_to('/home/meteohub/bin/meteohub.cgi')
        ext.update(candidate,runtime,services=False)
        (runtime/'live').mkdir();(runtime/'live/logger.conf').write_text(config)
        (runtime/'live/source.json').write_text(json.dumps({'host':'127.0.0.1','port':port}))
        (runtime/'.feed-consumer.lock').touch()
        prefix='meteohub-live-check-'+str(time.time_ns())
        names={'TARGET':prefix+'.target','LOGGER':prefix+'-logger.service','RUNTIME':prefix+'-runtime.service',
               'WEB':prefix+'-web.service','SOCKET':prefix+'-web.socket','INDEX':prefix+'-index.service'}
        def own():
            for parent,_,files in os.walk(top):
                os.chown(parent,65534,65534)
                for name in files:os.chown(Path(parent)/name,65534,65534,follow_symlinks=False)
        def wait_for(test,seconds=10):
            end=time.monotonic()+seconds
            while time.monotonic()<end:
                if test():return
                time.sleep(.1)
            self.fail('condition timed out')
        def request(path,auth=False):
            req=urllib.request.Request('http://127.0.0.1:18090'+path)
            if auth:req.add_header('Authorization','Basic '+base64.b64encode(b'meteohub:synthetic-only').decode())
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
            try:response=opener.open(req,timeout=5)
            except urllib.error.HTTPError as error:response=error
            with response:return response.code,response.read()
        with contextlib.ExitStack() as stack:
            for key,value in names.items():stack.enter_context(patch.object(live,key,value))
            stack.enter_context(patch.object(live,'NAMES',tuple(names.values())))
            stack.enter_context(patch.object(os,'getuid',return_value=65534))
            stack.enter_context(patch.object(os,'getgid',return_value=65534))
            stack.enter_context(patch.object(ext,'UNIT',live.INDEX))
            real_load=ext.load
            stack.enter_context(patch.object(ext,'load',side_effect=lambda name:live if name=='live-service' else real_load(name)))
            units=live.render(candidate,runtime,65534,65534)
            units[live.WEB]=units[live.WEB].replace('/usr/sbin/lighttpd -D', '/usr/bin/env /opt/test-lighttpd -m /opt/test-modules -D')
            units[live.WEB]+='BindReadOnlyPaths='+str(LIGHTTPD)+':/opt/test-lighttpd '+str(MODULES)+':/opt/test-modules\n'
            # Short retry only in the fixture; production uses 30s.
            units[live.LOGGER]=units[live.LOGGER].replace('RestartSec=30s','RestartSec=1s')
            plan=top/'units';plan.mkdir()
            for name,text in units.items():(plan/name).write_text(text)
            backup=top/'before';backup.mkdir()
            state={'backup':str(backup),'schema':1,'uid':65534,'candidate':str(candidate),'runtime':str(runtime),'phase':'installed',
                   'source':f'127.0.0.1:{port}','units':{n:live.digest(t.encode()) for n,t in units.items()},
                   'started':time.time(),'archive_before':{}}
            live.save(runtime/live.MARKER,state);own()
            try:
                verified=subprocess.run(['systemd-analyze','verify',*[str(plan/n) for n in live.NAMES]],capture_output=True,text=True)
                self.assertEqual(verified.returncode,0,verified.stdout+verified.stderr)
                live.write_units(plan)
                live.ctl('start',live.TARGET);live.ctl('enable',live.TARGET)
                live.web_auth_check()
                raw=runtime/'root/data/weather'/time.strftime('%Y%m',time.gmtime())/'raw'
                wait_for(lambda:raw.exists() and raw.stat().st_size>0)
                self.assertEqual(request('/cgi-bin/meteohub.cgi')[0],401)
                code,body=request('/cgi-bin/meteohub.cgi',True)
                self.assertEqual(code,200);self.assertTrue(body.strip().isdigit(),body)
                initial_pid=body.strip()
                main_pid=subprocess.check_output(['systemctl','show',live.LOGGER,'-p','MainPID','--value']).strip()
                self.assertEqual(initial_pid,main_pid)
                # Stopping only the logger must remove the PID file although the
                # shared runtime and web remain available. Restart republishes it.
                live.ctl('stop',live.LOGGER)
                self.assertFalse(Path('/run/meteohub-live-65534/loggerd.pid').exists())
                self.assertEqual(live.fields(live.WEB)['ActiveState'],'active')
                live.ctl('start',live.LOGGER)
                initial_pid=request('/cgi-bin/meteohub.cgi',True)[1].strip()
                self.assertEqual(initial_pid,subprocess.check_output(['systemctl','show',live.LOGGER,'-p','MainPID','--value']).strip())
                # A different process really cannot acquire the shared receiver lock.
                attempt=subprocess.run(['flock','-n',str(runtime/'.feed-consumer.lock'),'true'])
                self.assertEqual(attempt.returncode,1)
                live.read_state(candidate,runtime)
                self.assertEqual(subprocess.run(['systemctl','is-enabled','--quiet',live.TARGET]).returncode,0)
                first=raw.stat().st_size
                live.ctl('kill','--signal=SIGKILL',live.LOGGER)
                def restarted_pid_published():
                    pid=subprocess.check_output(['systemctl','show',live.LOGGER,'-p','MainPID','--value']).strip()
                    if pid in (b'0',initial_pid): return False
                    path=Path('/run/meteohub-live-65534/loggerd.pid')
                    try: return path.read_bytes().strip()==pid
                    except FileNotFoundError: return False
                wait_for(restarted_pid_published)
                wait_for(lambda:raw.stat().st_size>first)
                self.assertNotEqual(request('/cgi-bin/meteohub.cgi',True)[1].strip(),initial_pid)
                self.assertEqual(request('/cgi-bin/meteohub.cgi',True)[1].strip(),subprocess.check_output(['systemctl','show',live.LOGGER,'-p','MainPID','--value']).strip())
                # Real extension activation must restart the installed unit, not create a transient duplicate.
                pid_before_update=request('/cgi-bin/meteohub.cgi',True)[1].strip()
                ext.update(candidate,runtime)
                own()  # Root test orchestrator; production writes as the actual application UID.
                self.assertEqual(request('/cgi-bin/meteohub.cgi',True)[1].strip(),pid_before_update)
                self.assertEqual(live.fields(live.TARGET)['ActiveState'],'active')
                self.assertEqual(live.fields(live.INDEX)['FragmentPath'],str(live.UNIT_DIR/live.INDEX))
                wait_for(lambda:json.loads((runtime/'root/data/dashboard/status.json').read_text()).get('records_added',0)>0)
                code,body=request('/cgi-bin/weather-api.cgi',True)
                self.assertEqual(code,200)
                self.assertTrue(any(m['field']=='pressure' and m['value']==981.6 for m in json.loads(body)['metrics']))
                before=raw.read_bytes()
                live.ctl('stop',live.TARGET)
                wait_for(lambda:all(live.fields(unit)['ActiveState']=='inactive'
                                    for unit in (live.LOGGER,live.WEB,live.INDEX,live.RUNTIME)))
                for unit in (live.LOGGER,live.WEB,live.INDEX):self.assertEqual(live.fields(unit)['ActiveState'],'inactive')
                self.assertEqual(subprocess.run(['flock','-n',str(runtime/'.feed-consumer.lock'),'true']).returncode,0)
                self.assertFalse(Path('/run/meteohub-live-65534').exists())
                # Starting an enabled target again models unit ordering, not an actual machine reboot.
                live.ctl('start',live.TARGET);live.web_auth_check()
                wait_for(lambda:raw.stat().st_size>len(before))
                self.assertTrue(raw.read_bytes().startswith(before))
                path=live.UNIT_DIR/live.LOGGER;original=path.read_bytes();path.write_bytes(original+b'# operator edit\n')
                with self.assertRaisesRegex(ValueError,'missing/changed'):live.read_state(candidate,runtime)
                path.write_bytes(original)
                direct=load('test-native-direct')
                def private_web(candidate,runtime):
                    props=web.web_properties(candidate,runtime)+['BindReadOnlyPaths='+str(LIGHTTPD)+':/opt/test-lighttpd '+str(MODULES)+':/opt/test-modules']
                    command=['systemd-run','--collect','--unit='+live.WEB.removesuffix('.service'),'--uid=65534','--gid=65534',
                             '--socket-property=ListenStream=127.0.0.1:18090','--socket-property=Accept=no']
                    command+=['--property='+p for p in props]
                    subprocess.run(command+['/opt/test-lighttpd','-m','/opt/test-modules','-D','-f','/opt/meteohub-web/lighttpd.conf'],check=True,capture_output=True)
                    live.web_auth_check()
                original_load=live.load
                with patch.object(direct.web,'UNIT',live.WEB.removesuffix('.service')),patch.object(web,'start',side_effect=private_web),patch.object(live,'load',side_effect=lambda n:web if n=='web-test' else ext if n=='extension-update' else direct if n=='test-native-direct' else original_load(n)):
                    live.restore(candidate,runtime,state)
                self.assertTrue(raw.read_bytes().startswith(before))
                self.assertFalse((runtime/live.MARKER).exists())
                self.assertTrue((backup/'removed-install.json').is_file())
                for name in live.NAMES:self.assertFalse((live.UNIT_DIR/name).exists())
                self.assertEqual(live.fields(live.LOGGER)['LoadState'],'not-found')
                self.assertIn('PrivateNetwork=yes',subprocess.check_output(['systemctl','show',live.WEB,'-p','PrivateNetwork'],text=True))
                self.assertEqual(request('/dashboard/')[0],401)
                self.assertEqual(request('/dashboard/',True)[0],200)
                print('PASS: real persistent services, shared volatile PID, 401/auth CGI, TCP archive, exclusive lock, crash restart, extension update, stop/start, changed-unit refusal and rollback to private web/index')
            finally:
                subprocess.run(['systemctl','disable',live.TARGET],capture_output=True)
                subprocess.run(['systemctl','stop',*live.NAMES],capture_output=True)
                for name in live.NAMES:(live.UNIT_DIR/name).unlink(missing_ok=True)
                subprocess.run(['systemctl','daemon-reload'],check=True)
                subprocess.run(['systemctl','reset-failed',*live.NAMES],capture_output=True)
                stop.set();listener.close();thread.join(2)


if __name__=='__main__':unittest.main()
