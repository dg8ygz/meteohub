#!/usr/bin/python3
import datetime,json,os,pathlib,sqlite3,sys,time,urllib.parse,zoneinfo,math
sys.path.insert(0,'/usr/local/lib/meteohub-dashboard')
from weather_data import FIELDS
BASE=pathlib.Path('/var/lib/meteohub-dashboard');now=time.time()
def output(data,status='200 OK'):
 print('Status: '+status+'\r\nContent-Type: application/json; charset=utf-8\r\nCache-Control: no-store\r\n\r\n'+json.dumps(data,ensure_ascii=False,allow_nan=False))
if not os.environ.get('REMOTE_USER'):output({'error':'Anmeldung erforderlich'},'401 Unauthorized');sys.exit()
if os.environ.get('REQUEST_METHOD')!='GET':output({'error':'GET erforderlich'},'405 Method Not Allowed');sys.exit()
q=urllib.parse.parse_qs(os.environ.get('QUERY_STRING',''));ranges={'1h':3600,'24h':86400,'7d':7*86400,'30d':30*86400};selected=q.get('range',['24h'])[0]
if selected not in ranges:output({'error':'Unbekannter Zeitraum'},'400 Bad Request');sys.exit()
db=None
try:
 db=sqlite3.connect('file:'+str(BASE/'weather.sqlite')+'?mode=ro',uri=True,timeout=3)
 cadence_file=pathlib.Path('/etc/meteohub-dashboard.json')
 cadence=json.loads(cadence_file.read_text()).get('sensor_intervals_seconds',{}) if cadence_file.exists() else {}
 duration=ranges[selected];since=int(now-duration);step=max(15,math.ceil(duration/600));metrics=[]
 day=datetime.datetime.now(zoneinfo.ZoneInfo('Europe/Berlin')).replace(hour=0,minute=0,second=0,microsecond=0).timestamp()
 for sensor,field in db.execute('SELECT DISTINCT sensor,field FROM samples'):
  if field not in FIELDS or (sensor.startswith('thb') and field!='pressure'):continue
  last=db.execute('SELECT ts,value FROM samples WHERE sensor=? AND field=? ORDER BY ts DESC LIMIT 1',(sensor,field)).fetchone()
  stats=db.execute('SELECT min(value),max(value),count(*),min(ts),max(ts) FROM samples WHERE sensor=? AND field=? AND ts>=?',(sensor,field,day)).fetchone()
  rows=db.execute('SELECT CAST(ts/? AS INTEGER)*?,avg(value),min(value),max(value),count(*) FROM samples WHERE sensor=? AND field=? AND ts>=? GROUP BY CAST(ts/? AS INTEGER) ORDER BY ts',(step,step,sensor,field,since,step)).fetchall() if field!='direction' else []
  metric={'id':sensor+'.'+field,'sensor':sensor,'field':field,'label':FIELDS[field][0],'unit':FIELDS[field][1],'ts':last[0],'value':last[1],'age':round(now-last[0]),'today':{'min':stats[0],'max':stats[1],'count':stats[2],'first':stats[3],'last':stats[4]},'series':rows}
  if field in ('speed','gust'):
   metric['unit']='km/h';metric['value']*=3.6
   for key in ('min','max'):
    if metric['today'][key] is not None:metric['today'][key]*=3.6
   metric['series']=[[r[0],r[1]*3.6,r[2]*3.6,r[3]*3.6,r[4]] for r in rows]
  interval=cadence.get(sensor,60)
  if not isinstance(interval,(int,float)) or isinstance(interval,bool) or not 1<=interval<=86400:raise ValueError('Invalid sensor interval')
  metric['max_age']=max(90,2*interval+60)
  metrics.append(metric)
 wind=db.execute("SELECT (CAST((d.value+22.5)/45 AS INTEGER)%8),avg(s.value)*3.6,max(g.value)*3.6,count(*) FROM samples d JOIN samples s ON s.sensor=d.sensor AND s.ts=d.ts AND s.field='speed' JOIN samples g ON g.sensor=d.sensor AND g.ts=d.ts AND g.field='gust' WHERE d.sensor='wind0' AND d.field='direction' AND d.ts>=? GROUP BY 1",(since,)).fetchall()
 status=json.loads((BASE/'status.json').read_text())
 output({'at':now,'timezone':'Europe/Berlin','range':selected,'since':since,'step':step,'metrics':metrics,'wind_vector':wind,'index':status,'test_mode':True})
except (OSError,sqlite3.Error,ValueError):output({'error':'Messdaten derzeit nicht verfügbar','at':now},'503 Service Unavailable')
finally:
 if db is not None:db.close()
