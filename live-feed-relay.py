#!/usr/bin/python3
"""24h lab relay: existing Meteohub raw socket via pinned read-only SSH."""
import collections,datetime,json,subprocess,time,base64,select,os,signal
from pathlib import Path
p=Path(__file__).parent
source=json.loads((p/'connection.json').read_text())
target=json.loads((p/'vm38-connection.json').read_text())
read=(p/'read-source-socket.sh').read_text()
auth=json.loads((p/'live-monitor-private.json').read_text())
records=collections.deque(maxlen=500);proc=None;stop=False

def halt(*args):
 global stop
 stop=True
 if proc is not None:proc.terminate()
signal.signal(signal.SIGTERM,halt)
signal.signal(signal.SIGINT,halt)
try:
 while not stop:
  with (p/'live-feed-source.stderr').open('ab') as errors:
   proc=subprocess.Popen(source,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors)
   proc.stdin.write(read.encode());proc.stdin.close()
   last_read=time.monotonic();last_write=0;source_at=0;b=b''
   try:
    while not stop and proc.poll() is None:
     if select.select([proc.stdout],[],[],1)[0]:
      chunk=os.read(proc.stdout.fileno(),65536)
      if not chunk:break
      b+=chunk
      if len(b)>131072:raise RuntimeError('oversized SSH output')
      while b'\n' in b:
       line,b=b.split(b'\n',1);item=json.loads(line);source_at=item['at'];last_read=time.monotonic()
       if 'line' in item:
        if len(item['line'])>512:raise RuntimeError('oversized record')
        ts=datetime.datetime.fromtimestamp(source_at,datetime.timezone.utc).strftime('%Y%m%d%H%M%S')
        records.append(ts+' '+item['line'])
     if time.monotonic()-last_read>25:raise RuntimeError('source heartbeat missing')
     if source_at and time.monotonic()-last_write>=5:
      data={'source_read_at':source_at,'source_format':'plugin','lines':list(records)}
      blob=base64.b64encode(json.dumps(data).encode()).decode()
      credential=base64.b64encode((auth['user']+':'+auth['password']).encode()).decode()
      url=auth['url'].rsplit('/',1)[0]+'/live-feed.cgi'
      script="import base64,urllib.request\nreq=urllib.request.Request("+repr(url)+",data=base64.b64decode("+repr(blob)+"),headers={'Authorization': 'Basic "+credential+"','Content-Type':'application/json'},method='POST')\nwith urllib.request.urlopen(req,timeout=10) as r: print(r.read().decode())\n"
      w=subprocess.run(target+['python3 -'],input=script,text=True,capture_output=True,timeout=15);w.check_returncode();assert 'FEED_WRITTEN' in w.stdout
      status={'at':time.time(),'ok':True,'source':'native socket 5500','source_read_at':source_at,'last_source':records[-1].split()[0] if records else None,'records':len(records)}
      (p/'live-feed-relay-status.json').write_text(json.dumps(status));print(json.dumps(status),flush=True);last_write=time.monotonic()
   except Exception as e:
    status={'at':time.time(),'ok':False,'error':type(e).__name__+': '+str(e)[:200]}
    (p/'live-feed-relay-status.json').write_text(json.dumps(status));print(json.dumps(status),flush=True)
   finally:
    proc.terminate()
    try:proc.wait(timeout=5)
    except subprocess.TimeoutExpired:proc.kill();proc.wait()
  if not stop:time.sleep(5)
finally:
 if proc and proc.poll() is None:proc.terminate()
