#!/usr/bin/python3
"""Real ext4/RAM overlay, cgroup freezer, SQLite WAL and persistent TCP tests."""
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('quiet', TOOLS/'quiet-checkpoint.py')
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
b=q.load_base(TOOLS/'ram-storage.py')


class Integration(unittest.TestCase):
    def test_live_tcp_freeze_snapshot_failure_and_deadline(self):
        self.assertEqual(os.geteuid(), 0)
        top=Path(tempfile.mkdtemp(prefix='meteohub-freeze-test-',dir='/var/tmp'))
        prefix='meteohub-freeze-test-'+str(time.time_ns())
        paths=[]; loop=None; s=None; stop=threading.Event(); clients=[]; accepted=[]
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();listener.settimeout(.2)
        port=listener.getsockname()[1]
        def source():
            while not stop.is_set():
                try: conn,_=listener.accept()
                except socket.timeout:continue
                except OSError:return
                accepted.append(1);clients.append(conn);n=0
                try:
                    while not stop.is_set():
                        conn.sendall((str(n)+'\n').encode());n+=1;time.sleep(.01)
                except OSError:pass
                finally:conn.close()
        thread=threading.Thread(target=source,daemon=True);thread.start()
        def unit(name,body):
            p=Path('/run/systemd/system')/name;p.write_text(body);paths.append(p)
        apps=[prefix+x for x in ('-web.socket','-web.service','-logger.service','-index.service')]
        timer=prefix+'-thaw.timer';service=prefix+'-thaw.service'
        try:
            runtime=top/'runtime'; dashboard=runtime/'root/data/dashboard';dashboard.mkdir(parents=True)
            db=dashboard/'weather.sqlite'
            with sqlite3.connect(db) as c:c.execute('create table readings(n integer)')
            raw=runtime/'raw';raw.write_bytes(b'')
            image=top/'disk.img'
            with image.open('wb') as f:f.truncate(256*1024*1024)
            b.run('mkfs.ext4','-q','-E','lazy_itable_init=0,lazy_journal_init=0',image)
            loop=b.run('losetup','--find','--show',image).stdout.strip()
            persist=top/'persist';persist.mkdir();b.run('mount','-o','ro',loop,persist)
            cfg=dict(runtime=str(runtime),persist=str(persist),ram=str(top/'ram'),
                     uuid=b.run('blkid','-s','UUID','-o','value',loop).stdout.strip(),
                     ram_mib=64,apps=apps,target=prefix+'.target',prefix=prefix,lock=str(top/'storage.lock'))
            s=b.Storage(cfg);seed=s.capture();s.restore()
            writer=top/'writer.py'
            writer.write_text('''import socket,sqlite3,sys
from pathlib import Path
root=Path(sys.argv[1]); c=sqlite3.connect(root/'root/data/dashboard/weather.sqlite')
c.execute('pragma journal_mode=wal')
s=socket.create_connection(('127.0.0.1',int(sys.argv[2])))
with s.makefile('r') as stream,(root/'raw').open('a',buffering=1) as raw:
 for line in stream:
  n=int(line);c.execute('insert into readings values (?)',(n,));c.commit();raw.write(line)
''')
            unit(apps[0],f'[Socket]\nListenStream={top}/socket\n')
            for app in (apps[1],apps[3]):unit(app,'[Service]\nExecStart=/usr/bin/sleep infinity\n')
            unit(apps[2],f'[Service]\nExecStart=/usr/bin/python3 {writer} {runtime} {port}\n')
            marker=top/'freeze.json'
            command=f'/usr/bin/python3 {TOOLS}/quiet-checkpoint.py --base {TOOLS}/ram-storage.py --marker {marker} --watchdog {timer}'
            unit(service,f'[Service]\nType=oneshot\nExecStart={command} thaw\n')
            unit(timer,'[Timer]\nOnActiveSec=25s\nAccuracySec=1ms\n')
            b.run('systemctl','daemon-reload');b.run('systemctl','start',*apps)
            deadline=time.monotonic()+8
            while raw.stat().st_size<30 and time.monotonic()<deadline:time.sleep(.05)
            self.assertGreater(raw.stat().st_size,30)
            with patch.object(q,'MARKER',marker),patch.object(q,'WATCHDOG',timer),patch.object(q,'BASE',TOOLS/'ram-storage.py'):
                op=q.Quiet(b,s)
                pid=q.state(apps[2])['MainPID'];first=raw.read_bytes()
                result=op.checkpoint()
                self.assertEqual(result['mode'],'freeze')
                self.assertNotEqual(s.reference(),seed)
                self.assertEqual(s.live_state()['ref'],seed)
                saved=s.verify(s.reference())
                self.assertTrue((saved/'raw').read_bytes().startswith(first))
                self.assertEqual(q.state(apps[2])['MainPID'],pid)
                time.sleep(.2)
                values=[int(x) for x in raw.read_text().splitlines()]
                self.assertEqual(values,list(range(len(values))))
                self.assertEqual(len(accepted),1)
                with sqlite3.connect(saved/'root/data/dashboard/weather.sqlite') as c:
                    self.assertEqual(c.execute('pragma integrity_check').fetchone()[0],'ok')
                    self.assertGreater(c.execute('select count(*) from readings').fetchone()[0],0)
                c.close()
                print('PASS: same logger PID, one TCP connection, sequential records, verified SQLite WAL copy',flush=True)
                ref=s.reference()
                with patch.object(b,'check_sqlite',side_effect=ValueError('injected copy failure')):
                    with self.assertRaisesRegex(ValueError,'injected'):op.checkpoint()
                self.assertEqual(s.reference(),ref)
                self.assertTrue(all(q.state(n)['FreezerState']=='running' for n in apps[1:]))
                self.assertIn('ro',b.mount_info(persist)['options'].split(','))
                print('PASS: snapshot failure keeps saved generation, thaws all writers and restores RO',flush=True)
                # Independent systemd timer resumes processes while the copier hangs.
                tpath=Path('/run/systemd/system')/timer
                tpath.write_text('[Timer]\nOnActiveSec=1s\nAccuracySec=1ms\n')
                b.run('systemctl','daemon-reload')
                original=s.capture
                def slow():time.sleep(2);return original()
                with patch.object(s,'capture',side_effect=slow):
                    with self.assertRaisesRegex((RuntimeError,ValueError),'deadline|thawed|Runtime changed'):op.checkpoint()
                self.assertEqual(s.reference(),ref)
                self.assertFalse(marker.exists())
                self.assertTrue(all(q.state(n)['FreezerState']=='running' for n in apps[1:]))
                print('PASS: independent timeout thaws writers; no timed-out generation published',flush=True)
                # Kernel/service manager cleanup survives SIGKILL of the copier.
                driver=top/'killed-copier.py'
                driver.write_text("import importlib.util,json,time\n"
                    +f"sp=importlib.util.spec_from_file_location('q',{str(TOOLS/'quiet-checkpoint.py')!r});q=importlib.util.module_from_spec(sp);sp.loader.exec_module(q)\n"
                    +f"q.MARKER=q.Path({str(marker)!r});q.WATCHDOG={timer!r};q.BASE=q.Path({str(TOOLS/'ram-storage.py')!r})\n"
                    +f"b=q.load_base();s=b.Storage({cfg!r});s.capture=lambda:time.sleep(60)\n"
                    +"q.Quiet(b,s).checkpoint()\n")
                killed=prefix+'-killed.service'
                tpath.write_text('[Timer]\nOnActiveSec=25s\nAccuracySec=1ms\n')
                unit(killed,f'[Service]\nExecStart=/usr/bin/python3 {driver}\nExecStopPost={command} cleanup\n')
                b.run('systemctl','daemon-reload');b.run('systemctl','start',killed)
                until=time.monotonic()+5
                while time.monotonic()<until:
                    if q.state(apps[2]).get('FreezerState')=='frozen':break
                    time.sleep(.05)
                self.assertEqual(q.state(apps[2])['FreezerState'],'frozen')
                b.run('systemctl','kill','--kill-whom=main','--signal=KILL',killed)
                until=time.monotonic()+5
                while time.monotonic()<until and marker.exists():time.sleep(.05)
                self.assertFalse(marker.exists())
                self.assertTrue(all(q.state(n)['FreezerState']=='running' for n in apps[1:]))
                self.assertEqual(s.reference(),ref)
                b.run('systemctl','stop',timer)
                b.run('systemctl','reset-failed',killed)
                print('PASS: SIGKILL cleanup thaws writers and retains last verified backup',flush=True)
                # Bound RAM use: memory pressure retains the original rebase path.
                with (runtime/'pressure').open('wb') as f:
                    for unused in range(40):f.write(b'x'*(1024*1024))
                pressured=op.checkpoint()
                self.assertEqual(pressured['mode'],'stop-rebase-memory-pressure')
                self.assertEqual(s.live_state()['ref'],s.reference())
                self.assertNotEqual(q.state(apps[2])['MainPID'],pid)
                self.assertTrue(all(s.active(n)=='active' for n in apps))
                print('PASS: >=60% RAM pressure takes original stop/rebase path and restores applications',flush=True)

        finally:
            stop.set()
            for c in clients:
                with contextlib.suppress(OSError):c.shutdown(socket.SHUT_RDWR)
            listener.close();thread.join(timeout=2)
            subprocess.run(['systemctl','thaw',*apps[1:]],capture_output=True)
            subprocess.run(['systemctl','stop',timer,service,*apps],capture_output=True)
            for p in paths:p.unlink(missing_ok=True)
            subprocess.run(['systemctl','daemon-reload'],capture_output=True)
            subprocess.run(['systemctl','reset-failed',service,*apps[1:]],capture_output=True)
            for mount in (top/'runtime',top/'ram',top/'persist'):
                if b.mount_info(mount):b.run('umount',mount)
            if loop:b.run('losetup','-d',loop)
            shutil.rmtree(top)


if __name__=='__main__':unittest.main()
