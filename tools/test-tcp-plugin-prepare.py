#!/usr/bin/env python3
"""Check private plugin wiring without touching a station or starting its logger."""
import importlib.util
import json
import os
from pathlib import Path
import unittest


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name+'.py'))
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


tool = load('prepare-tcp-plugin')
fixture = load('test-runtime')
CONFIG = '@DATAPATH /data/weather/\n@ERRORLOG /data/log/meteohub.log\n@WEATHERSTATION 0 9 5 /home/meteohub/plugin.sh 43515920 300 336\n'


class PreparationTests(unittest.TestCase):
    def setUp(self):
        case = fixture.RuntimeTests();case.setUp();self.addCleanup(case.doCleanups)
        self.runtime = case.runtime
        fixture.stage.materialize(self.runtime, fixture.stage.prepare(case.image), os.getuid(), os.getgid(), 'fixture')
        self.home = self.runtime/'root/home/meteohub'
        self.config = self.home/'logger.conf';self.config.write_text(CONFIG)

    def test_prepare_keeps_config_and_installs_actual_plugin(self):
        before = (self.home/'meteohub.conf').read_bytes()
        tool.prepare(self.runtime)
        self.assertEqual(self.config.read_text(), CONFIG)
        self.assertEqual((self.home/'meteohub.conf').read_bytes(), before)
        self.assertEqual((self.home/'plugin.sh').read_text(), tool.WRAPPER)
        source = Path(__file__).resolve().parent.parent/'live_feed_plugin.py'
        self.assertEqual((self.home/'live_feed_plugin.py').read_bytes(), source.read_bytes())
        self.assertFalse((self.runtime/'root/data/tcp-feed/feed.json').exists())
        self.assertEqual((self.home/'plugin.sh').stat().st_mode & 0o777, 0o700)
        self.assertEqual(json.loads((self.runtime/'tcp-plugin-prepared.json').read_text())['schema'], 1)
        with self.assertRaisesRegex(ValueError, 'already exists'):tool.prepare(self.runtime)

    def test_wrong_missing_or_multiple_station_refused_before_writes(self):
        for config in (CONFIG.replace(' 9 5 ', ' 1 1 '), CONFIG+CONFIG,
                       CONFIG.replace('/home/meteohub/plugin.sh', '/dev/ttyUSB0'),
                       CONFIG.split('@WEATHERSTATION')[0], CONFIG.replace('/data/weather/', '/tmp/')):
            with self.subTest(config=config):
                self.config.write_text(config)
                with self.assertRaises(ValueError):tool.prepare(self.runtime)
                self.assertFalse((self.home/'plugin.sh').exists())

    def test_existing_target_or_symlink_not_overwritten(self):
        plugin = self.home/'plugin.sh';plugin.write_text('keep')
        with self.assertRaises(ValueError):tool.prepare(self.runtime)
        self.assertEqual(plugin.read_text(), 'keep')
        plugin.unlink()
        link = self.runtime/'root/data/tcp-feed';link.symlink_to('/tmp')
        with self.assertRaises(ValueError):tool.prepare(self.runtime)
        self.assertTrue(link.is_symlink())
        self.assertFalse(plugin.exists())

    def test_linked_config_refused(self):
        self.config.unlink();self.config.symlink_to('/etc/passwd')
        with self.assertRaises(ValueError):tool.prepare(self.runtime)
        self.assertFalse((self.home/'plugin.sh').exists())


if __name__ == '__main__':unittest.main()
