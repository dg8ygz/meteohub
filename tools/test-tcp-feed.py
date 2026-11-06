#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest

SCRIPT = Path(__file__).with_name('tcp-feed.py')
spec = importlib.util.spec_from_file_location('tcp_feed', SCRIPT)
feed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feed)


class FeedTests(unittest.TestCase):
    def test_framing_and_limits(self):
        f = feed.Framer()
        self.assertEqual(f.feed(b'wind0 70 '), [])
        self.assertEqual(f.feed(b'67 30\r\ndata0 600\n'), ['wind0 70 67 30', 'data0 600'])
        self.assertEqual(f.feed(b'x' * 600 + b'\nwind0 1 2 3\n'), ['wind0 1 2 3'])
        self.assertEqual(f.feed(b't2 10\xff\nt2 2147483648\nwind0 1 2\n'), [])
        self.assertEqual(f.rejected, 4)
        self.assertEqual(f.feed(b'rain0 0 10\nsol0 20 30\nthb0 1289 55 10132 0\n'),
                         ['rain0 0 10', 'sol0 20 30', 'thb0 1289 55 10132 0'])

    def test_actual_tcp_receive_only_and_feed_consumer(self):
        with tempfile.TemporaryDirectory() as temporary, socket.socket() as server:
            server.bind(('127.0.0.1', 0))
            server.listen()
            server.settimeout(5)
            unexpected = []

            def serve():
                with server.accept()[0] as client:
                    client.sendall(b'wind0 70 ')
                    time.sleep(0.05)
                    client.sendall(b'67 30\nt2 132\ndata0 600\n')
                    client.settimeout(4)
                    unexpected.append(client.recv(1024))

            thread = threading.Thread(target=serve)
            thread.start()
            output = Path(temporary) / 'feed.json'
            process = subprocess.run([sys.executable, str(SCRIPT), '--host', '127.0.0.1',
                '--port', str(server.getsockname()[1]), '--duration', '1.5',
                '--output', str(output)], capture_output=True, text=True, timeout=10)
            thread.join(5)
            self.assertFalse(thread.is_alive())
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            self.assertEqual(unexpected, [b''])
            snapshot = json.loads(output.read_text())
            self.assertEqual([line.split(' ', 1)[1] for line in snapshot['lines']],
                             ['wind0 70 67 30', 't2 132', 'data0 600'])
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            sys.path.insert(0, str(SCRIPT.parent.parent))
            from live_feed_plugin import Cursor
            accepted, rejected = Cursor().fresh(snapshot['lines'], time.time(), 'plugin')
            self.assertEqual(len(accepted), 3)
            self.assertEqual(rejected, [])
            status = json.loads(output.with_suffix('.status.json').read_text())
            self.assertEqual(status['records'], 3)

    def test_reconnect_discards_partial_line(self):
        # Exercise collect in its own process, with a short test retry interval.
        with tempfile.TemporaryDirectory() as temporary, socket.socket() as server:
            server.bind(('127.0.0.1', 0)); server.listen(); server.settimeout(5)
            unexpected = []

            def serve():
                with server.accept()[0] as client:
                    client.sendall(b't2 999')
                with server.accept()[0] as client:
                    client.sendall(b'wind0 1 2 3\nt2 120\n')
                    client.settimeout(4)
                    unexpected.append(client.recv(1024))

            thread = threading.Thread(target=serve); thread.start()
            output = Path(temporary) / 'feed.json'
            output.write_text('{"lines":["old record must not be replayed"]}')
            code = '''import importlib.util, pathlib, sys
s=importlib.util.spec_from_file_location('tcp_feed',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
sys.exit(m.collect('127.0.0.1',int(sys.argv[2]),pathlib.Path(sys.argv[3]),duration=1.5,retry=0.05))
'''
            result = subprocess.run([sys.executable, '-c', code, str(SCRIPT),
                str(server.getsockname()[1]), str(output)], capture_output=True, text=True, timeout=10)
            thread.join(5)
            self.assertFalse(thread.is_alive())
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            data = json.loads(output.read_text())
            self.assertEqual([s.split(' ', 1)[1] for s in data['lines']], ['wind0 1 2 3', 't2 120'])
            status = json.loads(output.with_suffix('.status.json').read_text())
            self.assertEqual(status['partial_disconnects'], 1)
            self.assertEqual(status['connections'], 2)
            self.assertEqual(unexpected, [b''])


if __name__ == '__main__':
    unittest.main()
