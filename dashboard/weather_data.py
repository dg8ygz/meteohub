"""Meteohub formats, following manual v4.7 appendices B/C. No source mutation."""
import calendar,datetime,math,re,functools
FIELDS={'temperature':('Temperatur','°C'),'humidity':('Luftfeuchte','%'),'pressure':('Stationsdruck','hPa'),'sea_pressure':('Luftdruck auf Meereshöhe','hPa'),'speed':('Wind','m/s'),'gust':('Böen','m/s'),'direction':('Windrichtung','°'),'chill':('Windchill','°C'),'rain_rate':('Regenrate','mm/h'),'rain_total':('Regenzähler','mm'),'uv':('UV-Index',''),'solar':('Solarstrahlung','W/m²'),'value':('Messwert','')}
@functools.lru_cache(maxsize=4096)
def timestamp(s):
 if not re.fullmatch(r'\d{14}',s):raise ValueError('timestamp')
 return calendar.timegm(datetime.datetime(int(s[:4]),int(s[4:6]),int(s[6:8]),int(s[8:10]),int(s[10:12]),int(s[12:14])).timetuple())
def legacy_decimal(s):
 # Legacy raw values encode tenths by a leading zero (including -040).
 return int(s)/(10 if len(s.lstrip('-'))>1 and s.lstrip('-').startswith('0') else 1)
def pressure_only(sensor,values,raw=False):
 if not re.fullmatch(r'thb\d+',sensor):raise ValueError('not a pressure sensor')
 pressure=int(values[3 if raw else 2]);pressure=pressure/(10 if not raw or pressure>5000 else 1)
 if not 300<=pressure<=1200:raise ValueError('pressure range')
 return {'pressure':pressure}
def decode(sensor,values,raw=False):
 if re.fullmatch(r'thb\d+',sensor):return pressure_only(sensor,values,raw)
 v=[int(x) for x in values];d={}
 if re.fullmatch(r'wind\d+',sensor) and len(v)>=3:
  if not 0<=v[0]<=360 or min(v[1:3])<0 or max(v[1:3])>1500:raise ValueError('wind range')
  d={'direction':v[0]%360,'gust':v[1]/10,'speed':v[2]/10}
  if raw and len(v)>3:d['chill']=legacy_decimal(values[3])
 elif re.fullmatch(r'rain\d+',sensor) and len(v)>=(3 if raw else 2):
  rate=legacy_decimal(values[0]) if raw else v[0]/10;total=v[2 if raw else 1]/10
  if rate<0:raise ValueError('rain rate range')
  d={'rain_rate':rate}
  # A broken cumulative counter does not invalidate the independently measured rate.
  if total>=0:d['rain_total']=total
 elif re.fullmatch(r'(?:t|th|thb)\d+',sensor) and v:
  if not -800<=v[0]<=800:raise ValueError('temperature range')
  d={'temperature':v[0]/10}
  if sensor.startswith('th') and len(v)>1:
   if not 0<=v[1]<=100:raise ValueError('humidity range')
   d['humidity']=v[1]
  if sensor.startswith('thb') and len(v)>=(4 if raw else 3):
   pressure=v[3 if raw else 2];pressure=pressure/(10 if not raw or pressure>5000 else 1)
   if not 300<=pressure<=1200:raise ValueError('pressure range')
   d['pressure']=pressure
   if raw and len(v)>5:
    pressure=v[5]/(10 if v[5]>2000 else 1)
    if 300<=pressure<=1200:d['sea_pressure']=pressure
 elif re.fullmatch(r'uv\d+',sensor) and v:
  u=legacy_decimal(values[0]) if raw else v[0]/10
  if not 0<=u<=30:raise ValueError('uv range')
  d={'uv':u}
 elif re.fullmatch(r'sol\d+',sensor) and v:
  if not 0<=v[0]<=2000:raise ValueError('solar range')
  d={'solar':v[0]}
 elif re.fullmatch(r'data\d+',sensor) and v:d={'value':v[0]/100}
 else:raise ValueError('unsupported sensor')
 if any(not math.isfinite(x) for x in d.values()):raise ValueError('nonfinite')
 return d
