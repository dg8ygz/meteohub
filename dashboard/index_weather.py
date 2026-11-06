#!/usr/bin/python3
"""Incremental derived display index; raw archives remain authoritative/read-only."""
import datetime,json,os,pathlib,sqlite3,time,sys
from weather_data import timestamp,decode,pressure_only
BASE=pathlib.Path(os.environ.get('METEO_DASHBOARD_STATE','/var/lib/meteohub-dashboard'))
ARCHIVE=pathlib.Path(os.environ.get('METEO_DASHBOARD_ARCHIVE','/data/weather'))
LIVE=pathlib.Path(os.environ.get('METEO_DASHBOARD_LIVE','/var/local/meteohub-live-test/state/provenance.jsonl'))
def ingest(db,path,live=False):
 st=path.stat();key=str(path);old=db.execute('SELECT inode,offset FROM positions WHERE path=?',(key,)).fetchone();off=old[1] if old and old[0]==st.st_ino and old[1]<=st.st_size else 0
 count=bad=0;scanned=0;started=time.monotonic();cutoff=time.time()-35*86400
 with path.open('rb') as f:
  f.seek(off)
  while True:
   pos=f.tell();line=f.readline()
   if not line or not line.endswith(b'\n'):off=pos;break
   scanned+=1
   if scanned>2000 or (scanned%100==0 and time.monotonic()-started>2):off=pos;break
   try:
    if live:
     row=json.loads(line)
     if row.get('pressure_only') is True:
      parts=row['source'].split();ts=timestamp(parts.pop(0))
      fmt=row['source_format']
      if fmt not in ('plugin','recorded'):raise ValueError('pressure source format')
      pressure_fields=pressure_only(parts[0],parts[1:],raw=fmt=='recorded')
     elif 'plugin' in row:
      ts=timestamp(row['source'].split()[0]);parts=row['plugin'].split();pressure_fields=None
     elif row.get('reason','').startswith('source temperature'):
      parts=row['rejected'].split();ts=timestamp(parts.pop(0));pressure_fields=pressure_only(parts[0],parts[1:],raw=len(parts)==7)
     else:continue
    else:
     parts=line.decode().split();ts=timestamp(parts.pop(0))
    if ts<cutoff or ts>time.time()+5:continue
    sensor=parts.pop(0);fields=pressure_fields if live and pressure_fields is not None else decode(sensor,parts,raw=not live)
    db.executemany('INSERT INTO samples(sensor,field,ts,value) VALUES(?,?,?,?) ON CONFLICT(sensor,field,ts) DO UPDATE SET value=excluded.value',[(sensor,k,ts,v) for k,v in fields.items()]);count+=1
   except (ValueError,IndexError,KeyError,UnicodeError):bad+=1
 db.execute('INSERT OR REPLACE INTO positions VALUES(?,?,?)',(key,st.st_ino,off));return count,bad

def main():
 BASE.mkdir(parents=True,exist_ok=True)
 db=sqlite3.connect(BASE/'weather.sqlite',timeout=5);db.execute('PRAGMA journal_mode=WAL')
 db.executescript('CREATE TABLE IF NOT EXISTS samples(sensor TEXT,field TEXT,ts INTEGER,value REAL,PRIMARY KEY(sensor,field,ts)) WITHOUT ROWID;CREATE INDEX IF NOT EXISTS time_idx ON samples(ts);CREATE TABLE IF NOT EXISTS positions(path TEXT PRIMARY KEY,inode INTEGER,offset INTEGER);')
 while True:
  start=time.time();count=bad=0
  try:
   with db:
    now=datetime.datetime.now(datetime.timezone.utc);months={(now-datetime.timedelta(days=d)).strftime('%Y%m') for d in (0,20,35)}
    if LIVE.exists():a,b=ingest(db,LIVE,True);count+=a;bad+=b
    for month in sorted(months,reverse=True):
     path=ARCHIVE/month/'raw'
     if path.is_file():a,b=ingest(db,path);count+=a;bad+=b
    db.execute('DELETE FROM samples WHERE ts<?',(time.time()-35*86400,))
   report={'at':time.time(),'last_success':time.time(),'seconds':round(time.time()-start,3),'records_added':count,'rejected':bad,'history_importing':any(pathlib.Path(path).stat().st_size>off for path,off in db.execute('SELECT path,offset FROM positions'))}
  except Exception as e:db.rollback();report={'at':time.time(),'error':type(e).__name__}
  tmp=BASE/'status.tmp';tmp.write_text(json.dumps(report));os.replace(tmp,BASE/'status.json');print(json.dumps(report),flush=True)
  if '--once' in sys.argv:break
  time.sleep(10)
if __name__=='__main__':main()
