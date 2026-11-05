#!/usr/bin/python3
import json,time,requests
from pathlib import Path
p=Path(__file__).parent
cfg=json.loads((p/'live-monitor-private.json').read_text())
s=requests.Session();s.auth=(cfg['user'],cfg['password'])
with (p/'live-test-observations.jsonl').open('a',buffering=1) as log:
 while True:
  start=time.monotonic(); wall_start=time.time()
  try:
   r=s.get(cfg['url'],timeout=30);r.raise_for_status();row=r.json();row['http_seconds']=round(time.monotonic()-start,3); row['host_received_at']=time.time(); row['clock_offset_interval_s']=[round(row['at']-row['host_received_at'],3),round(row['at']-wall_start,3)]
  except Exception as e:row={'at':time.time(),'error':type(e).__name__,'healthy_reception':False}
  log.write(json.dumps(row)+'\n');print(json.dumps({k:row.get(k) for k in ['at','healthy_reception','accepted_records','archive_records_flushed','logger_data_age_seconds','error']}),flush=True)
  time.sleep(30)
