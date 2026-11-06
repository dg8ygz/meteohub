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
