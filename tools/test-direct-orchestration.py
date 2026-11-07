#!/usr/bin/env python3
"""Check native TCP configuration and real units with a synthetic logger, never ARM."""
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

ISOLATION='--isolation' in sys.argv
if ISOLATION:sys.argv.remove('--isolation')

def load(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

direct=load('test-native-direct');fixture=load('test-runtime')
CONFIG='@DATAPATH /data/weather/\n@ERRORLOG /data/log/meteohub.log\n@WEATHERSTATION 0 9 4 127.0.0.1:5500 123 300 336\n@SENSORIDMAP 0 2 0 0\n@CALIBRATE preserve\n@INETUPLOADFREQ 5\n'

class DirectTests(unittest.TestCase):
    def test_direct_configuration_rejects_wrong_source_or_plugin(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'config';p.write_text(CONFIG)
            out=direct.config_copy(p,'127.0.0.1',5500)
            self.assertIn('@INETUPLOADFREQ 0',out)
            self.assertIn('@CALIBRATE preserve',out)
            self.assertIn('@SENSORIDMAP 0 2 0 0',out)
            self.assertEqual(p.read_text(),CONFIG)
            for text in (CONFIG.replace(' 9 4 ',' 9 5 '),CONFIG.replace(':5500',':5501'),CONFIG+CONFIG,CONFIG.replace('/data/weather/','/tmp/')):
                p.write_text(text)
                with self.assertRaises(ValueError):direct.config_copy(p,'127.0.0.1',5500)
            p.unlink();p.symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):direct.config_copy(p,'127.0.0.1',5500)

    @unittest.skipUnless(ISOLATION,'optional real systemd/network integration')
    def test_original_tcp_transport_no_plugin_and_web_restore(self):
        if os.geteuid()!=0:self.skipTest('root orchestration required')
        case=fixture.RuntimeTests();case.setUp();self.addCleanup(case.doCleanups)
        with tempfile.TemporaryDirectory(prefix='meteohub-direct-test-',dir='/var/lib') as td:
            top=Path(td);runtime=top/'runtime';image=top/'image'
            shutil.copytree(case.image,image)
            fixture.stage.materialize(runtime,fixture.stage.prepare(image),65534,65534,'fixture')
            listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(30)
            self.addCleanup(listener.close)
            port=listener.getsockname()[1];received=[]
            wire=b'wind0 70 67 23\nthb0 1289 100 9839\nt2 137\n'
            def source():
                try:
                    conn,_=listener.accept()
                    with conn:
                        conn.sendall(wire);conn.settimeout(15);received.append(conn.recv(1024))
                finally:listener.close()
            thread=threading.Thread(target=source,daemon=True);thread.start()
            home=runtime/'root/home/meteohub'
            (home/'logger.conf').write_text(CONFIG.replace(':5500',':'+str(port)))
            candidate=top/'candidate';entries=[]
            # The substitute reads the native config and source socket itself.
            # No plugin.sh, feed.json or collector exists in this test runtime.
            stub='''#!/usr/bin/python3
import pathlib,socket,datetime,time
cfg=pathlib.Path('/home/meteohub/logger-check.conf').read_text()
endpoint=next(s.split()[4] for s in cfg.splitlines() if s.startswith('@WEATHERSTATION '))
host,port=endpoint.split(':')
with socket.create_connection((host,int(port))) as sock:
 stream=sock.makefile('rb')
 for n in range(3):
  line=stream.readline()
  with open('/data/wire.bytes','ab') as f:f.write(line)
  values=line.decode().strip()
  if values.startswith('thb0 '):values='thb0 1289 100 1289 9839 0 10200'
  now=datetime.datetime.now(datetime.timezone.utc)
  path=pathlib.Path('/data/weather')/now.strftime('%Y%m')/'raw';path.parent.mkdir(exist_ok=True)
  with path.open('a') as f:f.write(now.strftime('%Y%m%d%H%M%S')+' '+values+'\\n')
 time.sleep(30)
'''
            for name in ('bin/loggerd','bin/meteometar','bin/meteonet','bin/meteoschedule','bin/meteohub.cgi','lib/libgcgi.so.0'):
                p=candidate/name;p.parent.mkdir(parents=True,exist_ok=True)
                p.write_text(stub if name=='bin/loggerd' else 'not executed');p.chmod(0o700)
                entries.append({'target':name,'candidate_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
            (candidate/'manifest.json').write_text(json.dumps({'files':entries}))
            for parent,_,files in os.walk(top):
                os.chown(parent,65534,65534)
                for name in files:os.chown(Path(parent)/name,65534,65534,follow_symlinks=False)
            unit='meteohub-direct-web-fixture-'+str(time.time_ns());modes=[]
            unit_command=direct.native.unit_command
            def owned_command(*args,**kwargs):
                # This root test orchestrator substitutes the UID, so files made
                # by the helper need the ownership a real normal-user run has.
                for parent,_,files in os.walk(top):
                    os.chown(parent,65534,65534)
                    for name in files:os.chown(Path(parent)/name,65534,65534,follow_symlinks=False)
                return unit_command(*args,**kwargs)
            def start_web(candidate,runtime,host_network=False):
                modes.append(host_network)
                cmd=direct.native.unit_command(unit,direct.web.web_properties(candidate,runtime,host_network))+['--collect','/usr/bin/python3','-c','import time; time.sleep(60)']
                subprocess.run(cmd,check=True,capture_output=True)
            try:
                with patch.object(direct.web,'UNIT',unit),patch.object(direct.web,'start',side_effect=start_web),patch.object(direct.native,'unit_command',side_effect=owned_command),patch.object(os,'getuid',return_value=65534),patch.object(os,'getgid',return_value=65534):
                    start_web(candidate,runtime)
                    self.assertEqual(direct.run_test(candidate,runtime,'127.0.0.1',port,3),0)
                    state=subprocess.check_output(['systemctl','show',unit+'.service','-p','PrivateNetwork'],text=True)
                    self.assertIn('PrivateNetwork=yes',state)
                self.assertEqual(modes,[False,True,False])
                self.assertEqual((runtime/'root/data/wire.bytes').read_bytes(),wire)
                thread.join(5);self.assertEqual(received,[b''])
                result=json.loads(next(top.glob('native-direct-test-*/result.json')).read_text())
                self.assertEqual(result['sensors'],{'wind0':1,'thb0':1,'t2':1})
                self.assertTrue(result['pressure_archive_observed'])
                self.assertFalse((home/'plugin.sh').exists())
                self.assertFalse((runtime/'root/data/tcp-feed/feed.json').exists())
                print('PASS: direct native-config TCP with synthetic logger; exact bytes, no source commands/plugin/JSON; private web namespace restored')
                # An early receiver failure must not count the prior archive
                # as success, and must still restore the original web profile.
                previous=set(top.glob('native-direct-test-*'))
                binary=candidate/'bin/loggerd';binary.write_text('#!/usr/bin/python3\nraise SystemExit(42)\n')
                manifest=candidate/'manifest.json';record=json.loads(manifest.read_text())
                for item in record['files']:
                    if item['target']=='bin/loggerd':item['candidate_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
                manifest.write_text(json.dumps(record))
                with patch.object(direct.web,'UNIT',unit),patch.object(direct.web,'start',side_effect=start_web),patch.object(direct.native,'unit_command',side_effect=owned_command),patch.object(os,'getuid',return_value=65534),patch.object(os,'getgid',return_value=65534):
                    self.assertEqual(direct.run_test(candidate,runtime,'127.0.0.1',port,3),3)
                failed_report=(set(top.glob('native-direct-test-*'))-previous).pop()
                failure=json.loads((failed_report/'result.json').read_text())
                self.assertFalse(failure['archive_observed'])
                self.assertIn('ExecMainStatus=42',failure['logger_status'])
                self.assertTrue(failure['web_private_network_restored'])
                self.assertEqual(modes,[False,True,False,True,False])
                print('PASS: early receiver exit rejected; old rows not counted; private web profile restored')
            finally:
                subprocess.run(['systemctl','stop',unit+'.service'],capture_output=True,check=False)

if __name__=='__main__':unittest.main()
