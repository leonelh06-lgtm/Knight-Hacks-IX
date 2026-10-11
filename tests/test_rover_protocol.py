import unittest,json,copy
from pathlib import Path
from rover.protocol import validate_message
class ProtocolTests(unittest.TestCase):
 def test_shared_fixtures(self):
  for row in json.loads(Path('tests/fixtures/rover_messages.json').read_text()):
   with self.subTest(message=row['message']):
    if row['valid']: self.assertEqual(validate_message(row['message']), row['message'])
    else:
     with self.assertRaises((ValueError,TypeError)): validate_message(row['message'])
 def test_nonfinite_rejected(self):
  base=json.loads(Path('tests/fixtures/rover_messages.json').read_text())[0]['message']
  for value in (float('nan'),float('inf'),True):
   m=copy.deepcopy(base);m['player']['x_mm']=value
   with self.assertRaises((ValueError,TypeError)):validate_message(m)
