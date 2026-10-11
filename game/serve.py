"""Serve the game and Guiding Hands companion with consistent JS MIME types."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError
from urllib.parse import urlsplit


class GameHandler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map,
                      '.mjs': 'application/javascript', '.js': 'application/javascript'}

    def __init__(self, *args, preview_port=8766, **kwargs):
        self.preview_port = preview_port
        super().__init__(*args, **kwargs)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path in ('/', '/index.html'):
            if Path(self.directory, 'play', 'index.html').is_file():
                self.send_response(302)
                self.send_header('Location', '/play/')
                self.end_headers()
            else:
                body = (b'<!doctype html><meta charset="utf-8"><title>Guiding Hands</title>'
                        b'<h1>Build Guiding Hands</h1><p>From the repository root:</p>'
                        b'<pre>npm ci --prefix frontend\nnpm run build --prefix frontend</pre>'
                        b'<a href="/debug.html">Open the standalone game</a>')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            return
        if path in ('/tracking/status', '/tracking/stream.mjpg'):
            self.proxy_preview()
            return
        super().do_GET()

    def proxy_preview(self):
        endpoint = urlsplit(self.path).path.removeprefix('/tracking')
        try:
            upstream = urlopen(f'http://127.0.0.1:{self.preview_port}{endpoint}', timeout=2)
        except (URLError, OSError):
            self.send_error(503, 'Tracking preview unavailable')
            return
        with upstream:
            self.connection.settimeout(3)
            self.send_response(200)
            self.send_header('Content-Type', upstream.headers['Content-Type'])
            self.send_header('Cache-Control', 'no-store')
            if upstream.headers.get('Content-Length'):
                self.send_header('Content-Length', upstream.headers['Content-Length'])
            self.end_headers()
            try:
                while chunk := upstream.read1(65536):
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except (OSError, ValueError):
                pass  # Both endpoints are closed on disconnect or upstream timeout.


def game_handler(preview_port=8766, directory=None):
    return partial(GameHandler, preview_port=preview_port,
                   directory=str(directory or Path(__file__).resolve().parent/'fight'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--preview-port', type=int, default=8766)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535 or not 1 <= args.preview_port <= 65535:
        parser.error('Ports must be between 1 and 65535.')
    with ThreadingHTTPServer(('127.0.0.1', args.port), game_handler(args.preview_port)) as server:
        print(f'Guiding Hands: http://localhost:{server.server_port}/', flush=True)
        print(f'Standalone game: http://localhost:{server.server_port}/debug.html', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
