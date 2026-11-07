import datetime as dt
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('observe',Path(__file__).with_name('observe-archive.py'))
observe=importlib.util.module_from_spec(spec);spec.loader.exec_module(observe)


class Observation(unittest.TestCase):
    def test_distinguishes_index_delay_from_archive_delay(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime=Path(temporary);data=runtime/'root/data'
            (data/'weather/202611').mkdir(parents=True)
            (data/'dashboard').mkdir()
            now=dt.datetime(2026,11,7,15,0,tzinfo=dt.timezone.utc).timestamp()
            raw=data/'weather/202611/raw'
            raw.write_bytes(b'20261107145700 wind0 0 0 0\n20261107145900 wind0 0 0 0')
            (data/'dashboard/status.json').write_text(json.dumps({'last_success':now,'records_added':0}))
            dbpath=data/'dashboard/weather.sqlite'
            with sqlite3.connect(dbpath) as db:
                db.execute('CREATE TABLE samples(sensor TEXT,ts INTEGER)')
                db.execute('INSERT INTO samples VALUES(?,?)',('wind0',now-240))
            result=observe.snapshot(runtime,now)
            self.assertEqual(result['raw_age_s']['wind0'],180)
            self.assertEqual(result['index_age_s']['wind0'],240)
            self.assertEqual(result['index_behind_raw_s']['wind0'],60)
            with sqlite3.connect(dbpath) as db:db.execute('UPDATE samples SET ts=?',(now-180,))
            result=observe.snapshot(runtime,now)
            self.assertEqual(result['index_behind_raw_s']['wind0'],0)
            self.assertEqual(result['raw_age_s'],result['index_age_s'])
            self.assertEqual(raw.read_bytes(),b'20261107145700 wind0 0 0 0\n20261107145900 wind0 0 0 0')


if __name__=='__main__':unittest.main()
