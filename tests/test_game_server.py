import unittest,threading,urllib.request
from http.server import ThreadingHTTPServer
from game.serve import game_handler
class Tests(unittest.TestCase):
 def test_game_modules_have_browser_accepted_content_type(self):
  server=ThreadingHTTPServer(('127.0.0.1',0),game_handler());thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   for path in ('/rover_protocol.mjs','/levels.mjs','/fight.js'):
    with urllib.request.urlopen('http://127.0.0.1:'+str(server.server_port)+path) as response:
     self.assertIn(response.headers.get_content_type(),('text/javascript','application/javascript'));self.assertTrue(response.read())
  finally:server.shutdown();server.server_close();thread.join(1)
