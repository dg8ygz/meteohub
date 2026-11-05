LC_ALL=C python -u - <<'PY'
import socket,time,select,json,sys
s=socket.create_connection(('127.0.0.1',5500),5);s.settimeout(5)
b='';last=time.time()
while True:
 if select.select([s],[],[],2)[0]:
  d=s.recv(4096)
  if not d:break
  b+=d
  if len(b)>8192:raise RuntimeError('oversized source line')
  while '\n' in b:
   line,b=b.split('\n',1)
   print(json.dumps({'at':time.time(),'line':line.rstrip('\r')}));sys.stdout.flush()
 if time.time()-last>=5:
  print(json.dumps({'at':time.time(),'heartbeat':True}));sys.stdout.flush();last=time.time()
PY
