#!/usr/bin/python3
"""Authenticated, bounded feed ingestion for the isolated test guest only."""
import fcntl,json,math,os,pathlib,re,sys,tempfile,time
ROOT=pathlib.Path('/var/local/meteohub-live-feed')
def reply(code,text):
 print('Status: '+code+'\r\nContent-Type: text/plain\r\nCache-Control: no-store\r\n\r\n'+text)
 raise SystemExit
if not os.environ.get('REMOTE_USER'): reply('401 Unauthorized','Authentication required')
if os.environ.get('REQUEST_METHOD')!='POST': reply('405 Method Not Allowed','POST required')
try: length=int(os.environ.get('CONTENT_LENGTH','0'))
except ValueError: reply('400 Bad Request','Invalid length')
if not 0<length<=65536: reply('413 Content Too Large','Invalid size')
try:
 payload=sys.stdin.buffer.read(length)
 if len(payload)!=length: raise ValueError
 data=json.loads(payload)
 if set(data)!={'source_read_at','source_format','lines'}: raise ValueError
 at=data['source_read_at']
 if type(at) not in (int,float) or not math.isfinite(at) or not -5<=time.time()-at<=45: raise ValueError
 if data['source_format']!='plugin' or not isinstance(data['lines'],list) or len(data['lines'])>500: raise ValueError
 for row in data['lines']:
  if not isinstance(row,str) or len(row)>512 or not re.fullmatch(r'\d{14} (?:wind|rain|thb|th|t|uv|sol|data)\d+(?: -?\d+){1,6}',row): raise ValueError
except (ValueError,TypeError,KeyError): reply('400 Bad Request','Invalid or stale feed')
with (ROOT/'ingest.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 path=ROOT/'feed.json'
 if path.exists() and json.loads(path.read_text())['source_read_at']>at: reply('409 Conflict','Older feed rejected')
 fd,tmp=tempfile.mkstemp(prefix='.feed-',dir=ROOT)
 try:
  with os.fdopen(fd,'wb') as f: f.write(payload)
  os.chmod(tmp,0o640);os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
reply('200 OK','FEED_WRITTEN')
