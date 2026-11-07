#!/usr/bin/env python3
"""Native-test orchestration checks; optional real systemd/TCP with a synthetic logger."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import shutil
import tempfile
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch

ISOLATION='--isolation' in sys.argv
if ISOLATION:sys.argv.remove('--isolation')

def load(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

native=load('test-native-logger');fixture=load('test-runtime')

class NativeTests(unittest.TestCase):
    def setUp(self):
        case=fixture.RuntimeTests('test_selected_resources_and_existing_destination')
        case.setUp();self.addCleanup(case.doCleanups)
        temp=tempfile.TemporaryDirectory(prefix='meteohub-native-check-',dir='/var/lib' if ISOLATION else None)
        self.addCleanup(temp.cleanup)
        self.top=Path(temp.name);self.image=self.top/'image';self.runtime=self.top/'runtime'
        shutil.copytree(case.image,self.image)
        fixture.stage.materialize(self.runtime,fixture.stage.prepare(self.image),os.getuid(),os.getgid(),'test')
        self.weather=self.runtime/'root/data/weather'
        self.raw=self.weather/time.strftime('%Y%m',time.gmtime())/'raw'
        self.raw.parent.mkdir()
        self.config=self.runtime/'root/home/meteohub/logger.conf'
        self.config.write_text('@DATAPATH /data/weather/\n@ERRORLOG /data/log/meteohub.log\n@WEATHERSTATION 0 9 5 /home/meteohub/plugin.sh\n@INETUPLOADFREQ 5\n@CALIBRATE example 1\n')

    def test_fresh_raw_required_and_old_rows_not_counted(self):
        now=time.time();stamp=time.strftime('%Y%m%d%H%M%S',time.gmtime())
        self.raw.write_text('20000101000000 t2 12\n')
        before=native.archive_snapshot(self.weather)
        self.assertEqual(native.archive_result(self.weather,before,now)['fresh_raw_records'],0)
        with self.raw.open('a') as f:f.write(stamp+' t2 -05\n')
        result=native.archive_result(self.weather,before,now)
        self.assertEqual(result['fresh_raw_records'],1);self.assertEqual(result['sensors'],{'t2':1})

    def test_invalid_rows_and_truncation_detected(self):
        self.raw.write_text('before\n');before=native.archive_snapshot(self.weather)
        with self.raw.open('a') as f:f.write('invalid new record\n')
        self.assertEqual(native.archive_result(self.weather,before,time.time())['invalid_new_lines'],1)
        self.raw.write_text('')
        self.assertTrue(native.archive_result(self.weather,before,time.time())['truncated_or_replaced'])

    def test_configuration_preserves_source_and_disables_upload(self):
        before=self.config.read_bytes();value=native.config_copy(self.config)
        self.assertIn('@INETUPLOADFREQ 0',value);self.assertIn('@CALIBRATE example 1',value)
        self.assertEqual(self.config.read_bytes(),before)
        self.config.write_text(self.config.read_text().replace('0 9 5','0 1 1'))
        with self.assertRaises(ValueError):native.config_copy(self.config)

    @unittest.skipUnless(ISOLATION,'optional real service/network integration')
    def test_real_private_network_join_tcp_plugin_archive(self):
        if os.geteuid()!=0:self.skipTest('root orchestration required')
        tool=load('prepare-tcp-plugin');tool.prepare(self.runtime)
        candidate=self.top/'candidate';entries=[]
        stub='''#!/usr/bin/python3
import datetime,pathlib,socket,subprocess
with socket.create_connection(('127.0.0.1',5555),timeout=5) as sock:
 assert sock.recv(20)==b'shared namespace'
pathlib.Path('/data/network-joined').write_text('yes')
p=subprocess.Popen(['/home/meteohub/plugin.sh'],stdout=subprocess.PIPE,text=True)
for line in p.stdout:
 now=datetime.datetime.now(datetime.timezone.utc)
 path=pathlib.Path('/data/weather')/now.strftime('%Y%m')/'raw'
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('a') as f:f.write(now.strftime('%Y%m%d%H%M%S')+' '+line)
'''
        for name in ('bin/loggerd','bin/meteometar','bin/meteonet','bin/meteoschedule','bin/meteohub.cgi','lib/libgcgi.so.0'):
            p=candidate/name;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(stub if name=='bin/loggerd' else 'not executed');p.chmod(0o700)
            entries.append({'target':name,'candidate_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        (candidate/'manifest.json').write_text(json.dumps({'files':entries}))
        report=self.top/'report';report.mkdir();(report/'collector.py').write_bytes(Path(__file__).with_name('tcp-feed.py').read_bytes())
        for parent,_,files in os.walk(self.top):
            os.chown(parent,65534,65534)
            for name in files:os.chown(Path(parent)/name,65534,65534,follow_symlinks=False)
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();listener.settimeout(15)
        port=listener.getsockname()[1];stop=threading.Event()
        def source():
            try:
                conn,_=listener.accept()
                with conn:
                    while not stop.is_set():
                        conn.sendall(b't2 137\nwind0 90 20 15\nthb0 1289 100 9839\n');stop.wait(.5)
            except (OSError,TimeoutError):pass
            finally:listener.close()
        thread=threading.Thread(target=source,daemon=True);thread.start()
        prefix='meteohub-native-integration-'+str(time.time_ns());guardian=prefix+'-web';tcp=prefix+'-tcp';logger=prefix+'-logger'
        actual_run=subprocess.run
        with patch.object(os,'getuid',return_value=65534),patch.object(os,'getgid',return_value=65534):
            guardian_cmd=native.unit_command(guardian,fixture.probe.properties(candidate,self.runtime))+[
                '/usr/bin/python3','-c',"import socket; s=socket.socket(); s.bind(('127.0.0.1',5555)); s.listen(); c,a=s.accept(); c.sendall(b'shared namespace'); import time; time.sleep(15)"]
            tcp_cmd=native.unit_command(tcp,native.collector_properties(self.runtime,'127.0.0.1',5))+[
                '/usr/bin/python3',str(report/'collector.py'),'--host','127.0.0.1','--port',str(port),'--duration','10','--output',str(self.runtime/'root/data/tcp-feed/feed.json')]
            logger_cmd=native.unit_command(logger,native.logger_properties(candidate,self.runtime,5,guardian+'.service'))+['--wait','--pipe','/home/meteohub/bin/loggerd']
        try:
            actual_run(guardian_cmd,check=True,capture_output=True);time.sleep(.4)
            actual_run(tcp_cmd,check=True,capture_output=True)
            before=native.archive_snapshot(self.weather);started=time.time()
            output=actual_run(logger_cmd,capture_output=True,text=True,timeout=20)
            result=native.archive_result(self.weather,before,started)
            self.assertGreater(result['fresh_raw_records'],0,output.stderr)
            self.assertIn('thb0',result['sensors'])
            self.assertEqual((self.runtime/'root/data/network-joined').read_text(),'yes')
            actual_run(['systemctl','stop',logger+'.service'],capture_output=True,check=False)
            status=actual_run(['systemctl','show',logger+'.service','-p','Result'],capture_output=True,text=True)
            self.assertIn('Result=timeout',status.stdout)
            self.assertTrue((self.runtime/'root/data/tcp-feed/state/provenance.jsonl').is_file())
            print('PASS: real TCP -> real plugin -> synthetic archive writer; shared private loopback, bounded cgroup stop')
        finally:
            stop.set()
            for unit in (logger,tcp,guardian):
                actual_run(['systemctl','stop',unit+'.service'],capture_output=True,check=False)
                actual_run(['systemctl','reset-failed',unit+'.service'],capture_output=True,check=False)
            thread.join(timeout=2)

if __name__=='__main__':unittest.main()
