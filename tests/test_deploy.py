import json,unittest,tomllib
from pathlib import Path
class NetlifyConfiguration(unittest.TestCase):
 def test_native_function_deploy(self):
  root=Path(__file__).parents[1]
  config=tomllib.loads((root/'netlify.toml').read_text())
  self.assertEqual(config['build']['command'],'npm run build')
  self.assertEqual(config['build']['publish'],'dist')
  self.assertEqual(config['functions']['directory'],'netlify/functions')
  packages=json.loads((root/'package.json').read_text())['dependencies']
  self.assertIn('@netlify/database',packages)
  self.assertIn('@netlify/blobs',packages)
  self.assertNotIn('SONG_GUARD_API_ORIGIN',(root/'scripts/build-netlify.mjs').read_text())
