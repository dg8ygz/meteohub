"""Small standalone weather image. Only weather readings; no browser dependencies."""
import os, datetime, html, json, math, pathlib, sqlite3, time, zoneinfo
from weather_data import freshness_limit
BASE = pathlib.Path(os.environ.get('METEO_DASHBOARD_STATE','/var/lib/meteohub-dashboard'))

def read_weather(now):
    cadence_path = pathlib.Path(os.environ.get('METEO_DASHBOARD_CONFIG','/etc/meteohub-dashboard.json'))
    cadence = json.loads(cadence_path.read_text()) if cadence_path.exists() else {}
    status = json.loads((BASE / 'status.json').read_text())
    index_ok = not status.get('error') and -5 <= now - status.get('last_success', 0) < 60
    db = sqlite3.connect('file:' + str(BASE / 'weather.sqlite') + '?mode=ro', uri=True, timeout=2)
    try:
        items = {}
        for sensor, field in [('t2','temperature'),('wind0','speed'),('wind0','gust'),('wind0','direction'),('thb0','pressure'),('rain0','rain_rate'),('sol0','solar'),('uv0','uv')]:
            row = db.execute('SELECT ts,value FROM samples WHERE sensor=? AND field=? ORDER BY ts DESC LIMIT 1', (sensor, field)).fetchone()
            max_age = freshness_limit(cadence, sensor)
            if row and math.isfinite(row[1]):
                age = now - row[0]
                items[field] = {'value':row[1], 'fresh':index_ok and -5 <= age < max_age, 'ts':row[0]}
        wind = db.execute("SELECT CAST((d.value+22.5)/45 AS INTEGER)%8,avg(s.value)*3.6,max(g.value)*3.6,count(*) FROM samples d JOIN samples s ON s.sensor=d.sensor AND s.ts=d.ts AND s.field='speed' JOIN samples g ON g.sensor=d.sensor AND g.ts=d.ts AND g.field='gust' WHERE d.sensor='wind0' AND d.field='direction' AND d.ts>=? GROUP BY 1", (now-86400,)).fetchall()
        return {'items':items,'wind':wind,'index_ok':index_ok,'history_importing':status.get('history_importing',False)}
    finally:
        db.close()

def render(data, now):
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="600" height="180" viewBox="0 0 600 180" role="img" aria-labelledby="title desc">',
           '<title id="title">Aktuelles Wetter und Windvektor</title>',
           '<desc id="desc">Winddiagramm: Mittelwind und maximale Böen der letzten 24 Stunden nach Himmelsrichtung. Fehlende oder veraltete aktuelle Messwerte erscheinen als Strich.</desc>',
           '<rect x="0.5" y="0.5" width="599" height="179" rx="8" fill="#f8fbfc" stroke="#cbd8df"/>',
           '<g font-family="Arial,Helvetica,sans-serif" fill="#17313a">']
    def text(x,y,value,size=11,fill=None,anchor=None,weight=None):
        attrs=f'x="{x}" y="{y}" font-size="{size}"'
        if fill: attrs+=f' fill="{fill}"'
        if anchor: attrs+=f' text-anchor="{anchor}"'
        if weight: attrs+=f' font-weight="{weight}"'
        parts.append('<text '+attrs+'>'+html.escape(str(value))+'</text>')
    def number(v, digits=1):return f'{v:.{digits}f}'.replace('.',',')
    items=data.get('items',{})
    def value(field,scale=1,digits=1):
        row=items.get(field)
        return number(row['value']*scale,digits) if row and row['fresh'] else '—'
    pressure='pressure'
    metrics=[('Außentemperatur','temperature','°C',1,1),('Wind','speed','km/h',3.6,1),('Stationsdruck',pressure,'hPa',1,1),('Regenrate','rain_rate','mm/h',1,1),('Solarstrahlung','solar','W/m²',1,0),('UV-Index','uv','',1,1)]
    for i,(label,field,unit,scale,digits) in enumerate(metrics):
        x=12+(i%3)*130;y=20+(i//3)*68
        if field=='speed' and items.get('direction',{}).get('fresh'):
            direction=items['direction']['value'];names=['N','NO','O','SO','S','SW','W','NW'];label+=' · '+names[round(direction/45)%8]+' '+number(direction,0)+'°'
        text(x,y,label,10,'#506974')
        v=value(field,scale,digits);text(x,y+28,v+((' '+unit) if unit else ''),21,weight='600')
        if field=='speed':text(x,y+44,'Böen '+value('gust',3.6)+' km/h',9,'#506974')
        elif v=='—':text(x,y+44,'Keine aktuellen Daten',9,'#956321')
    parts.append('<path d="M399 12V151 M12 77H387" stroke="#d8e2e7" fill="none"/>')
    text(500,17,'Windvektor · 24 h',11,anchor='middle',weight='600')
    wind={int(r[0]):r for r in data.get('wind',[]) if 0<=r[0]<8 and all(math.isfinite(v) and v>=0 for v in r[1:3])}
    maximum=max(5,math.ceil(max([r[2] for r in wind.values()]+[0])/5)*5)
    cx,cy,radius=500,85,47
    def point(i,v,extra=0):
        r=radius*v/maximum+extra
        return f'{cx+math.sin(i*math.pi/4)*r:.2f},{cy-math.cos(i*math.pi/4)*r:.2f}'
    for j in range(1,4):parts.append('<polygon points="'+' '.join(point(i,maximum*j/3) for i in range(8))+'" fill="none" stroke="#d8e2e7"/>')
    for i,name in enumerate(['N','NO','O','SO','S','SW','W','NW']):
        parts.append(f'<path d="M{cx},{cy}L{point(i,maximum)}" stroke="#e1e9ed"/>')
        x,y=point(i,maximum,11).split(',');text(x,float(y)+3,name,9,'#506974','middle')
    text(507,39,number(maximum,0)+' km/h',8,'#506974')
    for col,color in [(2,'#178a76'),(1,'#2876b5')]:
        if len(wind)==8:parts.append('<polygon points="'+' '.join(point(i,wind[i][col]) for i in range(8))+'" fill="'+color+'" fill-opacity="0.1" stroke="'+color+'" stroke-width="1.5"/>')
        else:
            for i,row in wind.items():
                n=(i+1)%8
                if n in wind:parts.append(f'<path d="M{point(i,row[col])}L{point(n,wind[n][col])}" fill="none" stroke="{color}" stroke-width="1.5"/>')
                x,y=point(i,row[col]).split(',');parts.append(f'<circle cx="{x}" cy="{y}" r="2" fill="{color}"/>')
    if not wind:text(500,88,'Keine Winddaten',10,'#956321','middle')
    text(440,151,'● Mittelwind',9,'#2876b5');text(515,151,'● Böen',9,'#178a76')
    stamp=datetime.datetime.fromtimestamp(now,zoneinfo.ZoneInfo('Europe/Berlin')).strftime('%d.%m.%Y %H:%M')
    text(12,168,'Teststation · '+stamp,10,'#506974')
    warning='Datenaufbereitung gestört' if not data.get('index_ok') else 'Historie noch unvollständig' if data.get('history_importing') else 'Windrichtung: Herkunft des Windes'
    text(588,168,warning,9,'#956321' if not data.get('index_ok') or data.get('history_importing') else '#506974','end')
    parts.append('</g></svg>');return ''.join(parts)
