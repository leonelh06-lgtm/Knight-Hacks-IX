"""Serve Ethan's game with consistent JavaScript MIME types on Windows/Jetson."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path

class GameHandler(SimpleHTTPRequestHandler):
    extensions_map={**SimpleHTTPRequestHandler.extensions_map,'.mjs':'application/javascript','.js':'application/javascript'}

def game_handler():
    return partial(GameHandler,directory=str(Path(__file__).resolve().parent/'fight'))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',type=int,default=8000);args=p.parse_args()
    with ThreadingHTTPServer(('127.0.0.1',args.port),game_handler()) as server:
        print(f'Serving game at http://localhost:{server.server_port}/debug.html',flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
if __name__=='__main__':main()
