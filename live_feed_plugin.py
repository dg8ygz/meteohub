#!/usr/bin/python3
"""Read-only mirror of recorded sensor data for isolated logger testing.
The native logger timestamps reception; original UTC timestamps stay in provenance.
Never feeds stale records as new, and never opens the physical USB device.
"""
import collections, datetime, json, os, pathlib, re, sys, time

def stamp(s):
    return datetime.datetime.strptime(s, '%Y%m%d%H%M%S').replace(tzinfo=datetime.timezone.utc).timestamp()

def source_pressure(line,source_format):
    parts=line.split()
    if len(parts)<2 or not re.fullmatch(r'thb\d+',parts[1]):raise ValueError('not a pressure source')
    values=parts[2:];index=2 if source_format=='plugin' else 3
    try:value=int(values[index])
    except (IndexError,ValueError):raise ValueError('missing or invalid pressure') from None
    pressure=value/(10 if source_format=='plugin' or value>5000 else 1)
    if not 300<=pressure<=1200:raise ValueError('pressure outside 300..1200 hPa')
    return pressure

def convert(line):
    p=line.split()
    if len(p)<3 or not re.fullmatch(r'\d{14}', p[0]): raise ValueError('format')
    name=p[1]; v=[int(x) for x in p[2:]]
    if re.fullmatch(r't\d+',name) and len(v)==1: out=v
    elif re.fullmatch(r'data\d+',name) and len(v)==1: out=v
    elif re.fullmatch(r'uv\d+',name) and len(v)==1: out=v
    elif re.fullmatch(r'sol\d+',name) and len(v)==2: out=v
    elif re.fullmatch(r'wind\d+',name) and len(v)==4: out=v[:3]
    elif re.fullmatch(r'rain\d+',name) and len(v)==3: out=v[:2]
    elif re.fullmatch(r'th\d+',name) and len(v)==3: out=v[:2]
    elif re.fullmatch(r'thb\d+',name) and len(v)==6: out=[v[0],v[1],v[3],v[4]]
    else: raise ValueError('unsupported record')
    # Reject implausible source temperatures; retain rejected evidence.
    if name.startswith('t') and not name.startswith('thb') and not -800<=out[0]<=800: raise ValueError('source temperature outside -80..80C')
    return p[0], name+' '+' '.join(map(str,out))

class Cursor:
    def __init__(self,last='',seen=None): self.last=last;self.seen=collections.Counter(seen or {})
    def fresh(self,lines,now,source_format="recorded"):
        counts=collections.Counter(); accepted=[]; rejected=[]
        for line in lines:
            parts=line.split(); ts=parts[0] if parts else ''
            try: epoch=stamp(ts)
            except (ValueError,OverflowError): rejected.append((line,'timestamp'));continue
            if ts<self.last: continue
            if ts>self.last: self.last=ts;self.seen.clear();counts.clear()
            counts[line]+=1
            if counts[line]<=self.seen[line]: continue
            self.seen[line]=counts[line]
            age=now-epoch
            if not 0<=age<=180: rejected.append((line,'stale or future'));continue
            try:
                if source_format=='plugin':
                    _,name,*values=line.split()
                    if not re.fullmatch(r'(?:wind|rain|thb|th|t|uv|sol|data)[0-9]+',name): raise ValueError('sensor format')
                    if not values or len(values)>6 or any(not re.fullmatch(r'-?[0-9]+',x) for x in values): raise ValueError('value format')
                    if name.startswith('t') and not name.startswith('thb') and not -800<=int(values[0])<=800: raise ValueError('source temperature outside -80..80C')
                    converted=' '.join([name]+values)
                else: _,converted=convert(line)
                if converted.split()[0].startswith('thb'):source_pressure(line,source_format)
            except ValueError as e: rejected.append((line,str(e)));continue
            accepted.append((line,converted,round(age,3)))
        return accepted,rejected

def main():
    feed=pathlib.Path(sys.argv[1]); state=pathlib.Path(sys.argv[2]);state.mkdir(parents=True,exist_ok=True)
    cp=state/'cursor.json'
    saved=json.loads(cp.read_text()) if cp.exists() else {}
    c=Cursor(saved.get('last',''),saved.get('seen',{}));previous=None
    pending=saved.get('pending_wind',[]);temperature_ready=False
    with (state/'provenance.jsonl').open('a',buffering=1) as log:
        while True:
            try:
                b=feed.read_bytes()
                if b==previous: time.sleep(2);continue
                data=json.loads(b); now=time.time()
                if abs(now-data['source_read_at'])>45: time.sleep(2);continue
                accepted,rejected=c.fresh(data['lines'],now,data.get('source_format','recorded'))
                deliver=[];pressures=[]
                for raw,converted,age in accepted:
                    name=converted.split()[0]
                    if name.startswith('thb'):
                        # Native THB input combines temperature/humidity/pressure.
                        # Keep only pressure in the derived index; never fabricate
                        # replacement temperature or emit the combined THB record.
                        pressures.append({'received_at':now,'source':raw,
                            'source_format':data.get('source_format','recorded'),
                            'pressure_only':True,'pressure_hpa':source_pressure(raw,data.get('source_format','recorded')),
                            'age_seconds':age})
                        continue
                    if name.startswith('wind') and not temperature_ready:
                        if len(pending)>=64:
                            dropped=pending.pop(0);rejected.append((dropped[0],'startup wind buffer full'))
                        pending.append([raw,converted]);continue
                    deliver.append((raw,converted,age))
                    if name=='t2' and not temperature_ready:
                        temperature_ready=True
                        for oldraw,oldconverted in pending:
                            oldage=now-stamp(oldraw.split()[0])
                            if 0<=oldage<=180:deliver.append((oldraw,oldconverted,round(oldage,3)))
                            else:rejected.append((oldraw,'startup wind expired waiting for t2'))
                        pending=[]
                for raw,converted,age in deliver:
                    print(converted,flush=True)
                    log.write(json.dumps({'received_at':now,'source':raw,'plugin':converted,'age_seconds':age})+'\n')
                for pressure in pressures:log.write(json.dumps(pressure)+'\n')
                for raw,reason in rejected:
                    log.write(json.dumps({'received_at':now,'rejected':raw,'reason':reason})+'\n')
                temp=cp.with_suffix('.tmp');temp.write_text(json.dumps({'last':c.last,'seen':dict(c.seen),'pending_wind':pending}));os.replace(temp,cp)
                previous=b
            except BrokenPipeError:
                # The native logger closes this pipe before waiting for its
                # plugin to exit. Retrying forever deadlocks that reconnect.
                print('FEED reader closed; exiting for logger reconnect',file=sys.stderr,flush=True)
                # Avoid a second flush of the broken pipe during interpreter exit.
                with open(os.devnull,'w') as sink: os.dup2(sink.fileno(),sys.stdout.fileno())
                raise SystemExit(1)
            except (OSError,ValueError,KeyError) as e: print('FEED unavailable: '+str(e),file=sys.stderr,flush=True)
            time.sleep(2)
if __name__=='__main__':main()
