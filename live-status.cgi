#!/usr/bin/python3
import datetime,json,os,pathlib,time
p=pathlib.Path('/var/local/meteohub-live-test');now=time.time()
d={'test_only':True,'source':'existing Meteohub sensor-copy socket via SSH','at':now,'archive':str(p/'weather'),'historical_archive_readonly_for_logger':True}
try:
 pid=int(pathlib.Path('/run/loggerd.pid').read_text());cmd=pathlib.Path('/proc/%d/cmdline'%pid).read_bytes()
 d['logger_alive']=cmd.startswith(b'/home/meteohub/loggerd\0') and b'/var/local/meteohub-live-test/logger.conf' in cmd
except (OSError,ValueError):d['logger_alive']=False
try:
 d['logger_last_data_at']=int(pathlib.Path('/run/meteohub/logger.dat').read_text());d['logger_data_age_seconds']=round(now-d['logger_last_data_at'],1)
except (OSError,ValueError):pass
try:
 lines=(p/'state/provenance.jsonl').read_text().splitlines();rows=[json.loads(x) for x in lines if x]
 live=[r for r in rows if 'plugin' in r];rejected=[r for r in rows if 'rejected' in r]
 d['accepted_records']=len(live);d['rejected_records']=len(rejected)
 if live:
  last=live[-1];d['last_source_record']=last['source'];d['last_forwarded_at']=last['received_at'];d['last_transport_delay_seconds']=last['age_seconds']
 d['rejected_source_sensors']=sorted(set(r['rejected'].split()[1] for r in rejected if r.get('reason','').startswith('source temperature')))
except (OSError,ValueError,KeyError):pass
try:
 feed=json.loads(pathlib.Path('/var/local/meteohub-live-feed/feed.json').read_text());d['feed_heartbeat_age_seconds']=round(now-feed['source_read_at'],1)
except (OSError,ValueError,KeyError):pass
raw=p/'weather'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m')/'raw'
try:
 b=raw.read_bytes();d['archive_records_flushed']=b.count(b'\n');d['archive_bytes']=len(b);d['last_archived_record']=b.decode().splitlines()[-1] if b else None
except OSError:pass
d['healthy_reception']=bool(d['logger_alive'] and 0<=d.get('logger_data_age_seconds',999)<60 and 0<=d.get('feed_heartbeat_age_seconds',999)<30)
print('Content-Type: application/json\r\nCache-Control: no-store\r\n\r\n'+json.dumps(d))
