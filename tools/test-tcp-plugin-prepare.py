#!/usr/bin/env python3
"""Check private plugin wiring without touching a station or starting its logger."""
import importlib.util
import hashlib
import io
import json
import os
import socket
import subprocess
import sys
import threading
from pathlib import Path
import unittest
from unittest import mock
from contextlib import redirect_stdout


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name+'.py'))
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


ISOLATION = '--isolation' in sys.argv
if ISOLATION: sys.argv.remove('--isolation')
tool = load('prepare-tcp-plugin')
fixture = load('test-runtime')
CONFIG = '@DATAPATH /data/weather/\n@ERRORLOG /data/log/meteohub.log\n@WEATHERSTATION 0 9 5 /home/meteohub/plugin.sh 43515920 300 336\n'


class PreparationTests(unittest.TestCase):
    def setUp(self):
        case = fixture.RuntimeTests();case.setUp();self.addCleanup(case.doCleanups)
        self.runtime = case.runtime
        fixture.stage.materialize(self.runtime, fixture.stage.prepare(case.image), os.getuid(), os.getgid(), 'fixture')
        self.home = self.runtime/'root/home/meteohub'
        self.config = self.home/'logger.conf';self.config.write_text(CONFIG)

    def test_prepare_keeps_config_and_installs_actual_plugin(self):
        before = (self.home/'meteohub.conf').read_bytes()
        tool.prepare(self.runtime)
        self.assertEqual(self.config.read_text(), CONFIG)
        self.assertEqual((self.home/'meteohub.conf').read_bytes(), before)
        self.assertEqual((self.home/'plugin.sh').read_text(), tool.WRAPPER)
        source = Path(__file__).resolve().parent.parent/'live_feed_plugin.py'
        self.assertEqual((self.home/'live_feed_plugin.py').read_bytes(), source.read_bytes())
        self.assertFalse((self.runtime/'root/data/tcp-feed/feed.json').exists())
        self.assertEqual((self.home/'plugin.sh').stat().st_mode & 0o777, 0o700)
        self.assertEqual(json.loads((self.runtime/'tcp-plugin-prepared.json').read_text())['schema'], 1)
        with self.assertRaisesRegex(ValueError, 'already exists'):tool.prepare(self.runtime)

    def test_wrong_missing_or_multiple_station_refused_before_writes(self):
        for config in (CONFIG.replace(' 9 5 ', ' 1 1 '), CONFIG+CONFIG,
                       CONFIG.replace('/home/meteohub/plugin.sh', '/dev/ttyUSB0'),
                       CONFIG.split('@WEATHERSTATION')[0], CONFIG.replace('/data/weather/', '/tmp/')):
            with self.subTest(config=config):
                self.config.write_text(config)
                with self.assertRaises(ValueError):tool.prepare(self.runtime)
                self.assertFalse((self.home/'plugin.sh').exists())

    def test_existing_target_or_symlink_not_overwritten(self):
        plugin = self.home/'plugin.sh';plugin.write_text('keep')
        with self.assertRaises(ValueError):tool.prepare(self.runtime)
        self.assertEqual(plugin.read_text(), 'keep')
        plugin.unlink()
        link = self.runtime/'root/data/tcp-feed';link.symlink_to('/tmp')
        with self.assertRaises(ValueError):tool.prepare(self.runtime)
        self.assertTrue(link.is_symlink())
        self.assertFalse(plugin.exists())

    @unittest.skipUnless(ISOLATION, 'optional actual TCP/systemd/plugin test')
    def test_real_tcp_collector_to_isolated_installed_plugin(self):
        if os.geteuid() != 0:self.skipTest('root test orchestrator required')
        tool.prepare(self.runtime)
        feed = self.runtime/'root/data/tcp-feed/feed.json'
        listener = socket.socket();listener.bind(('127.0.0.1', 0));listener.listen(1)
        listener.settimeout(10)
        received = []
        def source():
            try:
                connection, _ = listener.accept()
                with connection:
                    connection.settimeout(10)
                    connection.sendall(b't2 137\nwind0 70 67 23\nthb0 1289 100 9839\n')
                    received.append(connection.recv(1024))
            finally:listener.close()
        port = listener.getsockname()[1]
        thread = threading.Thread(target=source, daemon=True);thread.start()
        collector = subprocess.run([sys.executable, str(Path(__file__).with_name('tcp-feed.py')),
            '--host', '127.0.0.1', '--port', str(port), '--duration', '2', '--output', str(feed)],
            capture_output=True, text=True, timeout=10)
        thread.join(timeout=10)
        self.assertEqual(collector.returncode, 0, collector.stderr)
        self.assertEqual(received, [b''])
        candidate = self.runtime.parent/'candidate';entries = []
        for name in ('bin/loggerd','bin/meteometar','bin/meteonet','bin/meteoschedule','bin/meteohub.cgi','lib/libgcgi.so.0'):
            p = candidate/name;p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b'not executed')
            entries.append({'target':name, 'candidate_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        (candidate/'manifest.json').write_text(json.dumps({'files':entries}))
        manifest = self.runtime/'runtime-manifest.json'
        data = json.loads(manifest.read_text());data.update(uid=65534,gid=65534)
        manifest.write_text(json.dumps(data))
        for parent, _, files in os.walk(self.runtime.parent):
            os.chown(parent,65534,65534)
            for name in files:os.chown(Path(parent)/name,65534,65534,follow_symlinks=False)
        probe = tool.probe_tool();output = io.StringIO()
        argv = ['probe-cgi.py',str(candidate),'--runtime',str(self.runtime),'--probe-plugin']
        with mock.patch.object(sys,'argv',argv), mock.patch.object(os,'getuid',return_value=65534), mock.patch.object(os,'geteuid',return_value=65534), mock.patch.object(os,'getgid',return_value=65534), redirect_stdout(output):
            result = probe.main()
        self.assertEqual(result,0,output.getvalue())
        report = next(self.runtime.parent.glob('cgi-probe-*'))
        summary = json.loads((report/'plugin-result.json').read_text())
        self.assertEqual(summary['sensors'],{'t2':1,'wind0':1})
        self.assertEqual(summary['pressure_records'],1)
        self.assertEqual((report/'response.txt').read_text().splitlines(),['t2 137','wind0 70 67 23'])
        self.assertFalse((self.runtime/'root/run/loggerd.pid').exists())
        print('PASS: actual TCP collector -> installed plugin in systemd isolation; pressure separated; bounded stop')

    def test_empty_thb_output_and_unexpected_exit_never_pass(self):
        report = self.runtime/'result-test';report.mkdir()
        provenance = report/'absent-provenance.jsonl'
        for output, code in (('',124),('thb0 200 50 9839\n',124),('t2 137\n',0),('t2 137\n',125)):
            with self.subTest(output=output, code=code):
                (report/'response.txt').write_text(output)
                with redirect_stdout(io.StringIO()):
                    result = tool.probe_tool().plugin_result(report,code,provenance,0)
                self.assertEqual(result,3)
                self.assertFalse(json.loads((report/'plugin-result.json').read_text())['plugin_probe_passed'])

    def test_linked_config_refused(self):
        self.config.unlink();self.config.symlink_to('/etc/passwd')
        with self.assertRaises(ValueError):tool.prepare(self.runtime)
        self.assertFalse((self.home/'plugin.sh').exists())


if __name__ == '__main__':unittest.main()
