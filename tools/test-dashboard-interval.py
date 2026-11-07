#!/usr/bin/env python3
"""Exercise the real API/SVG with slow pressure readings and stale input."""
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

spec = importlib.util.spec_from_file_location('interval', Path(__file__).with_name('dashboard-interval.py'))
interval = importlib.util.module_from_spec(spec); spec.loader.exec_module(interval)
DASH = Path(__file__).resolve().parents[1] / 'dashboard'


class Intervals(unittest.TestCase):
    def test_pressure_four_minutes_old_api_svg_and_expiry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); config = root / 'config.json'
            now = int(time.time())
            with sqlite3.connect(root / 'weather.sqlite') as db:
                db.execute('CREATE TABLE samples(sensor TEXT,field TEXT,ts INTEGER,value REAL)')
                db.executemany('INSERT INTO samples VALUES(?,?,?,?)', [
                    ('thb0', 'pressure', now-240, 981.6), ('wind0', 'speed', now-240, 2)])
            status = root / 'status.json'
            status.write_text(json.dumps({'last_success':now}))
            env = dict(os.environ, METEO_DASHBOARD_LIB=str(DASH), METEO_DASHBOARD_STATE=str(root),
                       METEO_DASHBOARD_CONFIG=str(config), REMOTE_USER='test', REQUEST_METHOD='GET', QUERY_STRING='')
            def run(name):
                return subprocess.check_output([sys.executable, str(DASH/name)], env=env).decode()
            self.assertNotIn('981,6', run('weather-image.cgi'))
            interval.configure(config, 'thb0', 300)
            self.assertIn('981,6', run('weather-image.cgi'))
            data = json.loads(run('weather-api.cgi').split('\r\n\r\n', 1)[1])
            metrics = {m['sensor']:m for m in data['metrics']}
            self.assertEqual(metrics['thb0']['max_age'], 660)
            self.assertLess(metrics['thb0']['age'], metrics['thb0']['max_age'])
            self.assertEqual(metrics['wind0']['max_age'], 180)
            status.write_text(json.dumps({'last_success':now-120}))
            self.assertNotIn('981,6', run('weather-image.cgi'))
            status.write_text(json.dumps({'last_success':now}))
            with sqlite3.connect(root/'weather.sqlite') as db:db.execute('UPDATE samples SET ts=?', (now-720,))
            self.assertNotIn('981,6', run('weather-image.cgi'))

    def test_preserves_existing_config_and_backup(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'config.json'
            old = {'sensor_intervals_seconds':{'wind0':15}, 'other':True}
            path.write_text(json.dumps(old))
            interval.configure(path, 'thb0', 300)
            self.assertEqual(json.loads(path.read_text()), {'sensor_intervals_seconds':{'wind0':15,'thb0':300},'other':True})
            backup = next(path.parent.glob('config.json.before-*'))
            self.assertEqual(json.loads(backup.read_text()), old)
            for bad in (0, -1, 86401, True):
                with self.assertRaises(ValueError):interval.configure(path, 'thb0', bad)
            link = path.parent/'linked';link.symlink_to(path)
            with self.assertRaises(ValueError):interval.configure(link, 'thb0', 300)


if __name__ == '__main__':unittest.main()
