import contextlib,io,json,os,pathlib,sqlite3,tempfile,time,unittest
class Api(unittest.TestCase):
 def test_direction_sectors_units_and_missing_sector(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=pathlib.Path(tmp);db=sqlite3.connect(p/'weather.sqlite');db.execute('CREATE TABLE samples(sensor TEXT,field TEXT,ts INTEGER,value REAL,PRIMARY KEY(sensor,field,ts))');now=int(time.time())
   for n,(direction,speed,gust) in enumerate([(359,1,2),(1,3,4),(90,2,6)]):
    for field,value in [('direction',direction),('speed',speed),('gust',gust)]:db.execute('INSERT INTO samples VALUES(?,?,?,?)',('wind0',field,now-5+n,value))
   db.commit();db.close();(p/'status.json').write_text(json.dumps({'last_success':now,'history_importing':False}))
   code=pathlib.Path(__file__).with_name('weather-api.cgi').read_text().replace("BASE=pathlib.Path('/var/lib/meteohub-dashboard')",'BASE=pathlib.Path('+repr(tmp)+')')
   old=dict(os.environ);os.environ.update(REMOTE_USER='test',REQUEST_METHOD='GET',QUERY_STRING='range=24h')
   try:
    out=io.StringIO()
    with contextlib.redirect_stdout(out):exec(compile(code,'weather-api.cgi','exec'),{})
   finally:os.environ.clear();os.environ.update(old)
   data=json.loads(out.getvalue().split('\r\n\r\n',1)[1]);v={r[0]:r for r in data['wind_vector']};self.assertEqual(set(v),{0,2});self.assertAlmostEqual(v[0][1],7.2);self.assertAlmostEqual(v[0][2],14.4);self.assertEqual(v[0][3],2);self.assertAlmostEqual(v[2][2],21.6)
   speed=next(m for m in data['metrics'] if m['field']=='speed');self.assertEqual(speed['unit'],'km/h');self.assertAlmostEqual(speed['value'],7.2)
if __name__=='__main__':unittest.main()
