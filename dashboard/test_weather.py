import calendar,datetime,importlib.util,json,pathlib,sqlite3,tempfile,time,unittest
from weather_data import decode,timestamp
from index_weather import ingest
class Formats(unittest.TestCase):
 def test_wind(self):
  d=decode('wind0',['255','45','32','-040'],True);self.assertEqual(d,{'direction':255,'gust':4.5,'speed':3.2,'chill':-4})
 def test_temperature_humidity(self):self.assertEqual(decode('th1',['127','55']),{'temperature':12.7,'humidity':55})
 def test_pressure(self):
  d=decode('thb0',['218','46','10','10124','3','10165'],True);self.assertEqual(d['pressure'],1012.4);self.assertEqual(set(d),{'pressure'})
 def test_plugin_pressure(self):self.assertEqual(decode('thb0',['218','46','10124'])['pressure'],1012.4)
 def test_pressure_independent_of_invalid_temperature(self):
  self.assertEqual(decode('thb0',['1289','100','9859']),{'pressure':985.9})
 def test_uv_tenths(self):
  self.assertEqual(decode('uv0',['37'])['uv'],3.7);self.assertEqual(decode('uv0',['037'],True)['uv'],3.7);self.assertEqual(decode('uv0',['3'],True)['uv'],3)
 def test_rain(self):
  self.assertEqual(decode('rain0',['04','0','2764'],True),{'rain_rate':.4,'rain_total':276.4});self.assertEqual(decode('rain0',['4','2764']),{'rain_rate':.4,'rain_total':276.4})
 def test_rain_rate_survives_invalid_total(self):
  self.assertEqual(decode('rain0',['0','-31908']),{'rain_rate':0.0})
  self.assertEqual(decode('rain0',['0','0','-31908'],True),{'rain_rate':0.0})
  self.assertEqual(decode('rain0',['4','-31908']),{'rain_rate':0.4})
  with self.assertRaises(ValueError):decode('rain0',['-1','100'])
 def test_invalid(self):
  for sensor,v in [('thb0',['1289','55','99999']),('wind0',['361','1','1']),('th1',['10','101']),('uv0',['500']),('sol0',['-2'])]:
   with self.assertRaises(ValueError):decode(sensor,v)
 def test_utc_dst(self):self.assertEqual(timestamp('20261025013000')-timestamp('20261025003000'),3600)
 def test_rejected_combined_sensor_keeps_only_valid_pressure(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/'provenance.jsonl';ts=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')
   p.write_text(json.dumps({'rejected':ts+' thb0 1289 100 9859','reason':'source temperature outside -80..80C'})+'\n'+json.dumps({'rejected':ts+' thb0 1289 100 99999','reason':'source temperature outside -80..80C'})+'\n')
   db=sqlite3.connect(':memory:');self.addCleanup(db.close);db.executescript('CREATE TABLE samples(sensor TEXT,field TEXT,ts INTEGER,value REAL,PRIMARY KEY(sensor,field,ts));CREATE TABLE positions(path TEXT PRIMARY KEY,inode INTEGER,offset INTEGER);')
   self.assertEqual(ingest(db,p,True),(1,1));self.assertEqual(db.execute('SELECT sensor,field,value FROM samples').fetchall(),[('thb0','pressure',985.9)])
   self.assertEqual(ingest(db,p,True),(0,0))
 def test_partial_resume_and_duplicates(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/'raw';ts=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S');row=ts+' t2 123\n';p.write_text(row+ts+' uv0 0')
   db=sqlite3.connect(':memory:');self.addCleanup(db.close);db.executescript('CREATE TABLE samples(sensor TEXT,field TEXT,ts INTEGER,value REAL,PRIMARY KEY(sensor,field,ts));CREATE TABLE positions(path TEXT PRIMARY KEY,inode INTEGER,offset INTEGER);')
   self.assertEqual(ingest(db,p),(1,0));self.assertEqual(ingest(db,p),(0,0))
   with p.open('a') as f:f.write('\n')
   self.assertEqual(ingest(db,p),(1,0));self.assertEqual(db.execute('select count(*) from samples').fetchone()[0],2)
if __name__=='__main__':unittest.main()
