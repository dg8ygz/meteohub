import importlib.util
import io
import json
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
from contextlib import redirect_stdout

spec=importlib.util.spec_from_file_location('probe',Path(__file__).with_name('probe-cgi.py'))
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
ISOLATION='--isolation' in sys.argv
if ISOLATION:sys.argv.remove('--isolation')


class SummaryTests(unittest.TestCase):
    def test_selected_directives_do_not_disclose_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'logger.conf'
            path.write_text('@DATAPATH /data/weather/\n@ERRORLOG /data/log/meteohub.log\n'
                            '@WEATHERSTATION 0 9 5 secret-station-settings\n'
                            '@PASSWORD secret-password\n@OTHER hidden\n')
            result=probe.logger_config_summary(path)
            self.assertEqual(result,['@DATAPATH /data/weather/',
                '@ERRORLOG /data/log/meteohub.log',
                '@WEATHERSTATION 0 9 5 [remaining settings withheld]'])
            self.assertNotIn('secret',str(result))

    def test_link_and_unexpected_content_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'logger.conf'
            path.symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):probe.logger_config_summary(path)
            path.unlink();path.write_text('not a logger config\n')
            with self.assertRaises(ValueError):probe.logger_config_summary(path)
            path.write_text('@WEATHERSTATION unexpected credentials\n')
            with self.assertRaises(ValueError):probe.logger_config_summary(path)

    @unittest.skipUnless(ISOLATION, 'optional actual systemd test')
    def test_actual_generator_invocation_and_private_output(self):
        if os.geteuid()!=0:self.skipTest('root test orchestrator required')
        spec=importlib.util.spec_from_file_location('fixture',Path(__file__).with_name('test-runtime.py'))
        fixture_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture_module)
        fixture=fixture_module.RuntimeTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        fixture_module.stage.materialize(fixture.runtime,fixture_module.stage.prepare(fixture.image),65534,65534,'probe')
        candidate=fixture.top/'candidate';entries=[]
        for name in ('bin/loggerd','bin/meteometar','bin/meteonet','bin/meteoschedule','bin/meteohub.cgi','lib/libgcgi.so.0'):
            path=candidate/name;path.parent.mkdir(parents=True,exist_ok=True)
            data=b'fixture, not executed'
            if name=='bin/meteohub.cgi':
                data=b'''#!/bin/sh
set -eu
[ "$#" = 1 ] && [ "$1" = -2 ]
[ -z "${REQUEST_METHOD-}" ] && [ -z "${QUERY_STRING-}" ]
[ "${METEO_PREPARING-}" = 1 ]
printf '%s\\n' '@DATAPATH /data/weather/' '@ERRORLOG /data/log/meteohub.log' '@WEATHERSTATION 0 9 5 private-placeholder' > /home/meteohub/logger.conf
'''
            path.write_bytes(data);path.chmod(0o700)
            entries.append({'target':name,'candidate_sha256':hashlib.sha256(data).hexdigest()})
        (candidate/'manifest.json').write_text(json.dumps({'files':entries}))
        for parent,_,names in os.walk(fixture.top):
            os.chown(parent,65534,65534)
            for name in names:os.chown(Path(parent)/name,65534,65534,follow_symlinks=False)
        output=io.StringIO()
        with mock.patch.object(sys,'argv',['probe-cgi.py',str(candidate),'--runtime',str(fixture.runtime),'--generate-logger-config']),mock.patch.object(os,'getuid',return_value=65534),mock.patch.object(os,'geteuid',return_value=65534),mock.patch.object(os,'getgid',return_value=65534),redirect_stdout(output):
            code=probe.main()
        self.assertEqual(code,0,output.getvalue())
        self.assertIn('GENERATED: logger.conf',output.getvalue())
        self.assertNotIn('private-placeholder',output.getvalue())
        self.assertTrue((fixture.runtime/'root/home/meteohub/logger.conf').is_file())
        print('PASS: actual isolated CGI -2 invocation, clean environment, private generated config')


if __name__=='__main__':unittest.main()
