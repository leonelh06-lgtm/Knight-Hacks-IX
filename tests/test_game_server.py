import unittest,threading,urllib.request
from http.server import ThreadingHTTPServer
from game.serve import game_handler
class Tests(unittest.TestCase):
 def test_game_modules_have_browser_accepted_content_type(self):
  server=ThreadingHTTPServer(('127.0.0.1',0),game_handler());thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   for path in ('/predictor.mjs','/levels.mjs','/fight.js'):
    with urllib.request.urlopen('http://127.0.0.1:'+str(server.server_port)+path) as response:
     self.assertIn(response.headers.get_content_type(),('text/javascript','application/javascript'));self.assertTrue(response.read())
  finally:server.shutdown();server.server_close();thread.join(1)

class CompanionServerTests(unittest.TestCase):
 def launch(self, **options):
  server=ThreadingHTTPServer(('127.0.0.1',0),game_handler(**options))
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  self.addCleanup(thread.join,1)
  self.addCleanup(server.server_close)
  self.addCleanup(server.shutdown)
  return 'http://127.0.0.1:'+str(server.server_port)

 def test_unbuilt_root_explains_build_and_standalone_game_remains(self):
  import tempfile
  from pathlib import Path
  with tempfile.TemporaryDirectory() as folder:
   Path(folder,'debug.html').write_text('standalone game')
   url=self.launch(directory=folder)
   with urllib.request.urlopen(url+'/') as response:
    self.assertIn(b'Build The Guiding Hands',response.read())
   with urllib.request.urlopen(url+'/debug.html') as response:
    self.assertEqual(response.read(),b'standalone game')

 def test_built_root_opens_companion(self):
  import tempfile
  from pathlib import Path
  with tempfile.TemporaryDirectory() as folder:
   Path(folder,'play').mkdir()
   Path(folder,'play/index.html').write_text('The Guiding Hands')
   url=self.launch(directory=folder)
   with urllib.request.urlopen(url+'/') as response:
    self.assertEqual(response.url,url+'/play/')
    self.assertIn(b'The Guiding Hands',response.read())

 def test_unavailable_preview_reports_503(self):
  import socket
  from urllib.error import HTTPError
  with socket.socket() as sock:
   sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  url=self.launch(preview_port=port)
  with self.assertRaises(HTTPError) as raised:
   urllib.request.urlopen(url+'/tracking/status',timeout=3)
  self.assertEqual(raised.exception.code,503)

 def test_preview_proxy_forwards_status_and_stream(self):
  from gesture_control.web_preview import PreviewServer
  preview=PreviewServer(port=0);preview.start();self.addCleanup(preview.close)
  url=self.launch(preview_port=preview.port)
  with urllib.request.urlopen(url+'/tracking/status',timeout=3) as response:
   self.assertEqual(response.headers.get_content_type(),'application/json')
   self.assertIn(b'frameAgeMs',response.read())
  with urllib.request.urlopen(url+'/tracking/stream.mjpg',timeout=3) as response:
   self.assertIn('multipart/x-mixed-replace',response.headers['Content-Type'])
