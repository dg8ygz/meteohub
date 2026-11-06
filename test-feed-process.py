import tempfile,pathlib,json,time,subprocess,select,sys
script=pathlib.Path(__file__).with_name('live_feed_plugin.py')
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d);f=p/'feed.json';state=p/'state'
 def write(lines):
  f.write_text(json.dumps({'source_read_at':time.time(),'source_format':'plugin','lines':lines}))
 ts=time.strftime('%Y%m%d%H%M%S',time.gmtime());wind=ts+' wind0 90 20 10';temp=ts+' t2 90'
 write([wind]);proc=subprocess.Popen([sys.executable,str(script),str(f),str(state)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 try:
  time.sleep(3);assert not select.select([proc.stdout],[],[],0)[0], 'wind emitted without temperature'
  write([wind,temp]);time.sleep(3)
  proc.terminate();out,err=proc.communicate(timeout=3)
  assert out.splitlines()==['t2 90','wind0 90 20 10'],out
  assert not err,err
  proc=subprocess.Popen([sys.executable,str(script),str(f),str(state)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  time.sleep(3);proc.terminate();out,err=proc.communicate(timeout=3);assert out=='',out
  print('PASS: real process defers wind, emits actual t2 before wind, no replay after restart')
 finally:
  if proc.poll() is None:proc.kill();proc.wait()

# A combined sensor contributes only pressure, even when its temperature is valid.
# Check the real process and the actual indexer together, not just a conversion helper.
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d);f=p/'feed.json';state=p/'state'
 ts=time.strftime('%Y%m%d%H%M%S',time.gmtime())
 f.write_text(json.dumps({'source_read_at':time.time(),'source_format':'plugin',
   'lines':[ts+' thb0 1289 100 9839',ts+' thb1 215 45 10132',ts+' thb2 200 50 99999']}))
 proc=subprocess.Popen([sys.executable,str(script),str(f),str(state)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 try:
  deadline=time.monotonic()+5
  while not (state/'cursor.json').exists() and time.monotonic()<deadline:time.sleep(.05)
  assert (state/'cursor.json').exists(),'pressure batch not checkpointed'
  proc.terminate();out,err=proc.communicate(timeout=3)
  assert out=='',out
  assert err=='',err
  rows=[json.loads(x) for x in (state/'provenance.jsonl').read_text().splitlines()]
  assert [r['pressure_hpa'] for r in rows if r.get('pressure_only')]==[983.9,1013.2],rows
  assert any('pressure outside' in r.get('reason','') for r in rows),rows
  assert not any('plugin' in r for r in rows),rows
  sys.path.insert(0,str(script.parent/'dashboard'))
  import sqlite3
  from index_weather import ingest
  with sqlite3.connect(':memory:') as db:
   db.executescript('CREATE TABLE samples(sensor TEXT,field TEXT,ts INTEGER,value REAL,PRIMARY KEY(sensor,field,ts));CREATE TABLE positions(path TEXT PRIMARY KEY,inode INTEGER,offset INTEGER);')
   assert ingest(db,state/'provenance.jsonl',True)==(2,0)
   assert db.execute('SELECT sensor,field,value FROM samples ORDER BY sensor').fetchall()==[('thb0','pressure',983.9),('thb1','pressure',1013.2)]
   assert ingest(db,state/'provenance.jsonl',True)==(0,0)
  print('PASS: real plugin/indexer retains only valid pressure; no THB temperature/humidity output or index entries')
 finally:
  if proc.poll() is None:proc.kill();proc.wait()

# A closed reader must end the plugin, allowing loggerd's pclose/reconnect.
# A failed write must not be reported as a successfully forwarded record.
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d);f=p/'feed.json';state=p/'state'
 ts=time.strftime('%Y%m%d%H%M%S',time.gmtime())
 f.write_text(json.dumps({'source_read_at':time.time(),'source_format':'plugin',
                         'lines':[ts+' t2 90']}))
 proc=subprocess.Popen([sys.executable,str(script),str(f),str(state)],
                       stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 proc.stdout.close()
 try:
  assert proc.wait(timeout=5)==1
  err=proc.stderr.read().decode()
  assert 'reader closed; exiting' in err,err
  rows=[json.loads(x) for x in (state/'provenance.jsonl').read_text().splitlines()]
  assert not any('plugin' in r for r in rows),rows
  assert not (state/'cursor.json').exists(), 'failed delivery checkpointed'
  print('PASS: closed reader exits promptly without false delivery or checkpoint')
 finally:
  if proc.poll() is None:proc.kill();proc.wait()
