import unittest
from normalize_native import normalize_record
class NativeNormalization(unittest.TestCase):
 def test_north(self):self.assertEqual(normalize_record('wind0 360 58 41'),normalize_record('20261105070000 wind0 0 58 41 -010',True))
 def test_rain(self):self.assertEqual(normalize_record('rain0 4 2764'),normalize_record('20261105070000 rain0 04 0 2764',True))
 def test_uv_decimal(self):self.assertEqual(normalize_record('uv0 37'),normalize_record('20261105070000 uv0 037',True))
 def test_uv_integer(self):self.assertEqual(normalize_record('uv0 30'),normalize_record('20261105070000 uv0 3',True))
if __name__=='__main__':unittest.main()
