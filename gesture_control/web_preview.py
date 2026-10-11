"""Optional loopback-only, read-only view of the existing camera worker."""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

EDGES = ((0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),
         (5,9),(9,10),(10,11),(11,12),(9,13),(13,14),(14,15),(15,16),
         (13,17),(0,17),(17,18),(18,19),(19,20))


class PreviewServer:
    def __init__(self, host='127.0.0.1', port=8766):
        self.host, self.port = host, port
        self.lock = threading.Lock()
        self.encoding_lock = threading.Lock()
        self.stopped = threading.Event()
        self.snapshot = self.command = None
        self.flags = dict(paused=False, calibrating=False, simulated=False, stale_after=.35)
        self.jpeg = None
        self.encoded_stamp = None
        self.encoded_at = 0
        self.encoding_error = ''
        self.server = self.thread = None

    def start(self):
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.path == '/status':
                    body = json.dumps(owner.status()).encode()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                elif self.path == '/stream.mjpg':
                    self.connection.settimeout(2)
                    self.send_response(200)
                    self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
                    self.send_header('Cache-Control', 'no-store')
                    self.end_headers()
                    last = None
                    try:
                        while not owner.stopped.is_set():
                            stamp, jpeg = owner.frame()
                            if jpeg is not None and stamp != last:
                                self.wfile.write(b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: '
                                    + str(len(jpeg)).encode() + b'\r\n\r\n' + jpeg + b'\r\n')
                                self.wfile.flush()
                                last = stamp
                            owner.stopped.wait(.1)
                    except (OSError, ValueError):
                        pass
                else:
                    self.send_error(404)
        self.server = ThreadingHTTPServer((self.host, self.port), Handler)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def update(self, snapshot, command, *, paused, calibrating, simulated, stale_after):
        with self.lock:
            self.snapshot, self.command = snapshot, command
            self.flags = dict(paused=paused, calibrating=calibrating,
                              simulated=simulated, stale_after=stale_after)

    def status(self):
        with self.lock:
            s, c, flags = self.snapshot, self.command, self.flags.copy()
        age = max(0, time.monotonic()-s.timestamp) if s and s.timestamp else None
        fresh = age is not None and age <= flags['stale_after'] and not s.error
        active = bool(fresh and c and c.active and not any(flags[k] for k in
                      ('paused','calibrating','simulated')))
        direction = {(0,-1):'up',(0,1):'down',(-1,0):'left',(1,0):'right'}.get(tuple(c.velocity),'stop') if active else 'stop'
        return dict(phase=s.phase if s else 'Waiting for camera',
                    status=c.status if c else 'Waiting for camera', direction=direction,
                    active=active, handDetected=bool(fresh and s.observation is not None and not flags['simulated']),
                    frameAgeMs=round(age*1000,1) if age is not None else None,
                    staleAfterMs=flags['stale_after']*1000,
                    inferenceMs=s.inference_ms if s else 0,
                    simulated=flags['simulated'], paused=flags['paused'],
                    calibrating=flags['calibrating'],
                    hasFrame=bool(fresh and s.frame is not None and not flags['simulated']),
                    error=(s.error if s else '') or self.encoding_error)

    def frame(self):
        # Only HTTP workers encode, and all viewers share one latest JPEG.
        with self.encoding_lock:
            with self.lock:
                s, flags = self.snapshot, self.flags.copy()
            if not s or s.frame is None or s.error or flags['simulated']:
                return None, None
            if time.monotonic()-s.timestamp > flags['stale_after']:
                return None, None
            if s.timestamp == self.encoded_stamp or time.monotonic()-self.encoded_at < .1:
                return self.encoded_stamp, self.jpeg
            try:
                import cv2
                h, w = s.frame.shape[:2]
                width = min(320,w)
                rgb = cv2.resize(s.frame,(width,max(1,round(h*width/w))))
                image = cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR)
                points = [(round(x*image.shape[1]),round(y*image.shape[0])) for x,y in s.points]
                for a,b in EDGES:
                    if max(a,b)<len(points):
                        cv2.line(image,points[a],points[b],(115,211,177),1,cv2.LINE_AA)
                for point in points:
                    cv2.circle(image,point,3,(118,226,224),-1,cv2.LINE_AA)
                ok, data = cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,75])
                if not ok:
                    raise RuntimeError('Camera preview encoding failed')
                self.jpeg, self.encoded_stamp = data.tobytes(), s.timestamp
                self.encoded_at = time.monotonic()
                self.encoding_error = ''
            except Exception as error:
                self.encoding_error = f'Preview unavailable: {error}'
                return None, None
            return self.encoded_stamp, self.jpeg

    def close(self):
        self.stopped.set()
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        if self.thread:
            self.thread.join(2)
