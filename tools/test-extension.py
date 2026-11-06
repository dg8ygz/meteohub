#!/usr/bin/env python3
"""Extension update/rollback and actual Python index/API/SVG tests with synthetic data."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name+'.py'))
    m = importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


ext=load('extension-update');web=load('web-test')


class Extension(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.runtime=Path(self.tmp.name)/'runtime';root=self.runtime/'root'
        for d in ('opt/meteohub-web','srv/www/cgi-bin','data','home/meteohub'):
            (root/d).mkdir(parents=True)
        web.write_config(root/'opt/meteohub-web')
        (root/'opt/meteohub-web/users.htpasswd').write_text('private auth fixture')
        (root/'home/meteohub/meteohub.conf').write_text('native settings fixture')
        self.source=Path(self.tmp.name)/'source';shutil.copytree(ext.REPO/'dashboard',self.source)
        self.candidate=Path(self.tmp.name)/'candidate'
        self.native=(root/'home/meteohub/meteohub.conf').read_bytes()
        self.password=(root/'opt/meteohub-web/users.htpasswd').read_bytes()

    def update(self,**kw):
        return ext.update(self.candidate,self.runtime,services=False,source=self.source,**kw)

    def test_update_rollback_preserves_state_and_settings(self):
        first=self.update();state=self.runtime/'root/data/dashboard/sentinel'
        state.write_text('must remain')
        self.assertEqual(self.update(),first)
        with (self.source/'index.html').open('a') as f:f.write('\n<!-- changed release -->\n')
        second=self.update();self.assertNotEqual(first,second)
        self.assertEqual(self.update(rollback=True),first)
        self.assertEqual(ext.verify_installed(self.runtime),first)
        self.assertEqual(state.read_text(),'must remain')
        self.assertEqual((self.runtime/'root/home/meteohub/meteohub.conf').read_bytes(),self.native)
        self.assertEqual((self.runtime/'root/opt/meteohub-web/users.htpasswd').read_bytes(),self.password)

    def test_modified_release_refused(self):
        name=self.update();base=self.runtime/'root/opt/meteohub-dashboard'
        (base/'releases'/name/'weather_svg.py').write_text('modified')
        with self.assertRaisesRegex(ValueError,'Modified'):self.update()

    def test_unowned_web_path_refused(self):
        link=self.runtime/'root/srv/www/dashboard';link.mkdir()
        with self.assertRaisesRegex(ValueError,'occupied'):self.update()
        self.assertTrue(link.is_dir())

    def test_failed_activation_restores_previous(self):
        first=self.update()
        with (self.source/'weather.css').open('a') as f:f.write('\n/* next */')
        activate=ext.activate;calls=[]
        def failing(runtime,name):
            activate(runtime,name);calls.append(name)
            if len(calls)==1:raise ValueError('injected activation failure')
        with patch.object(ext,'activate',side_effect=failing):
            with self.assertRaisesRegex(ValueError,'injected'):self.update()
        self.assertEqual(ext.verify_installed(self.runtime),first)

    def test_real_index_api_svg_pressure_only(self):
        name=self.update();release=self.runtime/'root/opt/meteohub-dashboard/releases'/name
        state=self.runtime/'root/data/dashboard';live=Path(self.tmp.name)/'live.jsonl'
        now=time.strftime('%Y%m%d%H%M%S',time.gmtime())
        live.write_text(json.dumps({'source':str(now)+' thb0 1289 100 9839','source_format':'plugin','pressure_only':True})+'\n'+
                        json.dumps({'source':str(now)+' t2 137','plugin':'t2 137'})+'\n')
        env=dict(os.environ,METEO_DASHBOARD_LIB=str(release),METEO_DASHBOARD_STATE=str(state),
                 METEO_DASHBOARD_LIVE=str(live),METEO_DASHBOARD_ARCHIVE=str(Path(self.tmp.name)/'no-archive'),
                 REMOTE_USER='meteohub',REQUEST_METHOD='GET',QUERY_STRING='range=24h',PYTHONDONTWRITEBYTECODE='1')
        subprocess.run([sys.executable,str(release/'index_weather.py'),'--once'],env=env,check=True,capture_output=True)
        with sqlite3.connect(state/'weather.sqlite') as db:
            rows=db.execute('SELECT sensor,field,value FROM samples ORDER BY sensor').fetchall()
        self.assertEqual(rows,[('t2','temperature',13.7),('thb0','pressure',983.9)])
        api=subprocess.check_output([sys.executable,str(release/'weather-api.cgi')],env=env).decode()
        data=json.loads(api.split('\r\n\r\n',1)[1]);self.assertTrue(data['metrics'])
        svg=subprocess.check_output([sys.executable,str(release/'weather-image.cgi')],env=env).decode()
        self.assertIn('983,9',svg);self.assertIn('width="600" height="180"',svg)
        self.assertNotIn('128,9',svg)
        # Source stops: processing a recent index must not turn old measurements fresh.
        with sqlite3.connect(state/'weather.sqlite') as db:db.execute('UPDATE samples SET ts=ts-3600')
        svg=subprocess.check_output([sys.executable,str(release/'weather-image.cgi')],env=env).decode()
        self.assertNotIn('983,9',svg)


if __name__=='__main__':unittest.main()
