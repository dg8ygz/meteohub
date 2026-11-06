#!/usr/bin/python3
import os,sys,time,sqlite3
sys.path.insert(0,os.environ.get('METEO_DASHBOARD_LIB','/usr/local/lib/meteohub-dashboard'))
from weather_svg import read_weather,render
method=os.environ.get('REQUEST_METHOD','GET')
if method not in ('GET','HEAD'):
 print('Status: 405 Method Not Allowed\r\nAllow: GET, HEAD\r\nContent-Type: text/plain\r\n\r\nGET oder HEAD erforderlich');sys.exit()
now=time.time()
try:data=read_weather(now)
except (OSError,ValueError,sqlite3.Error):data={'items':{},'wind':[],'index_ok':False}
body=render(data,now).encode('utf-8')
headers='Content-Type: image/svg+xml; charset=utf-8\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nContent-Security-Policy: default-src \'none\'; style-src \'unsafe-inline\'; sandbox\r\nContent-Length: '+str(len(body))+'\r\n\r\n'
sys.stdout.buffer.write(headers.encode('ascii'))
if method!='HEAD':sys.stdout.buffer.write(body)
