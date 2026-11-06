#!/usr/bin/python3
"""Build native logger configuration, with explicit isolated-source overrides."""
import os,pathlib,subprocess,tempfile
BASE=pathlib.Path('/var/local/meteohub-live-test')
def main():
 env=dict(os.environ,METEO_PREPARING='1');env.pop('REQUEST_METHOD',None);env.pop('QUERY_STRING',None)
 with (BASE/'config-generator.log').open('ab') as log:
  subprocess.run(['/srv/www/cgi-bin/meteohub.cgi','-1'],env=env,stdout=log,stderr=log,timeout=45,check=True)
 lines=pathlib.Path('/home/meteohub/logger.conf').read_text().splitlines();out=[];stations=0
 for line in lines:
  parts=line.split()
  if not parts:out.append(line);continue
  if parts[0]=='@WEATHERSTATION':
   if len(parts)<5 or parts[1:4]!=['0','9','5']:raise RuntimeError('Isolated mirror requires exactly plugin station 0; hardware selection cannot be applied to the mirror')
   parts[4]=str(BASE/'plugin.sh');line=' '.join(parts);stations+=1
  elif parts[0]=='@DATAPATH':line='@DATAPATH '+str(BASE/'weather')+'/'
  elif parts[0]=='@ERRORLOG':line='@ERRORLOG '+str(BASE/'logger.log')
  elif parts[0] in ('@INETUPLOADFREQ','@INETUPLOADFREQRAPID','@LIVEUPLOADFREQ'):line=parts[0]+' 0'
  out.append(line)
 if stations!=1:raise RuntimeError('Expected one isolated mirror station')
 fd,tmp=tempfile.mkstemp(dir=BASE,prefix='.logger-')
 try:
  with os.fdopen(fd,'w') as f:f.write('\n'.join(out)+'\n');f.flush();os.fsync(f.fileno())
  os.replace(tmp,BASE/'logger.conf')
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
if __name__=='__main__':main()
