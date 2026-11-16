#!/usr/bin/python3
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('native_eval',Path(__file__).with_name('native-eval.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Requests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  m.HOME=Path(self.tmp.name)/'home';m.HOME.mkdir();m.WEATHER=Path(self.tmp.name)/'weather';m.WEATHER.mkdir()
  self.request=m.HOME/'wmr928fulleval.conf';self.request.write_text('original')
 def test_failure_restores_request(self):
  with patch.object(m,'evaluate',side_effect=RuntimeError('disk full')):
   with self.assertRaises(RuntimeError):m.full()
  self.assertEqual(self.request.read_text(),'original')
  self.assertFalse((m.HOME/'wmr928fulleval.stage').exists())
 def test_failure_keeps_new_request_and_old_work(self):
  def failure(*args):self.request.write_text('new');raise RuntimeError('interrupted')
  with patch.object(m,'evaluate',side_effect=failure):
   with self.assertRaises(RuntimeError):m.full()
  self.assertEqual(self.request.read_text(),'new')
  self.assertEqual((m.HOME/'wmr928fulleval.do.conf').read_text(),'original')
 def test_exit_zero_without_output_is_not_success(self):
  with patch.object(m,'evaluate'),patch.object(m,'history'):
   with self.assertRaises(RuntimeError):m.full()
  self.assertTrue(self.request.exists())
 def test_completed_preserves_new_request(self):
  def evaluate(*args):self.request.write_text('new');(m.WEATHER/'wind0-min5').write_text('record')
  with patch.object(m,'evaluate',side_effect=evaluate),patch.object(m,'history'):m.full()
  self.assertEqual(self.request.read_text(),'new')
  self.assertFalse((m.HOME/'wmr928fulleval.do.conf').exists())
unittest.main()
