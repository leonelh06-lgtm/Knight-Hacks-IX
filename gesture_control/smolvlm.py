"""Live camera capture and asynchronous local SmolVLM2 gesture controls."""

from dataclasses import replace
import math
import threading
import time

from .controls import Command
from .tracking import Snapshot, BACKENDS, open_camera
from .smolvlm_model import LocalModel, REVISION, parse_label

DIRECTIONS = {'open_palm': (0, -1), 'fist': (0, 1),
              'index_pinch': (-1, 0), 'pinkie_pinch': (1, 0)}


def gesture_command(snapshot, now, prediction_timeout, camera_timeout):
    if snapshot.error:
        return Command((0, 0), 'SmolVLM2 error')
    if snapshot.timestamp <= 0 or not 0 <= now - snapshot.timestamp <= camera_timeout:
        return Command((0, 0), 'Camera frame stale')
    if snapshot.prediction_timestamp <= 0 or not 0 <= now - snapshot.prediction_timestamp <= prediction_timeout:
        return Command((0, 0), 'Waiting for fresh SmolVLM2 prediction')
    velocity = DIRECTIONS.get(snapshot.prediction)
    if velocity is None:
        return Command((0, 0), 'Unknown / unclear gesture: stop')
    return Command(velocity, 'SmolVLM2: ' + snapshot.prediction, True)


class SmolTracker:
    def __init__(self, camera=0, mirror=False, backend='auto', device='cuda',
                 offline=False, startup_timeout=300):
        if device not in ('cuda', 'cpu') or backend not in BACKENDS:
            raise ValueError('Invalid SmolVLM2 device or camera backend.')
        if not math.isfinite(startup_timeout) or startup_timeout <= 0:
            raise ValueError('Startup timeout must be positive.')
        self.camera, self.mirror, self.backend = camera, mirror, backend
        self.device, self.offline = device, offline
        self.startup_timeout = startup_timeout
        self.started_at = time.monotonic()
        self._snapshot = Snapshot()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._frame_ready = threading.Event()
        self._threads = [threading.Thread(target=self._capture, daemon=True),
                         threading.Thread(target=self._infer, daemon=True)]

    def start(self):
        self.started_at = time.monotonic()
        for thread in self._threads:
            thread.start()

    def latest(self, now=None):
        with self._lock:
            snapshot = self._snapshot
        now = time.monotonic() if now is None else now
        if not snapshot.error and snapshot.prediction_timestamp == 0 and now - self.started_at > self.startup_timeout:
            return replace(snapshot, error=f'{snapshot.phase} timed out after '
                           f'{self.startup_timeout:g}s. Check camera, download, and CUDA setup.')
        return snapshot

    def close(self):
        self._stop.set()
        self._frame_ready.set()
        for thread in self._threads:
            if thread.ident is not None:
                thread.join(timeout=2)

    def _fail(self, error):
        with self._lock:
            self._snapshot = replace(self._snapshot, prediction='unknown',
                prediction_timestamp=0, error=f'SmolVLM2 {self.device} failed: '
                f'{type(error).__name__}: {error}. No CPU fallback was used.')
        self._stop.set()
        self._frame_ready.set()

    def _capture(self):
        cap = None
        try:
            import cv2
            cap = open_camera(self.camera, self.backend)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            while not self._stop.is_set():
                captured = time.monotonic()
                ok, frame = cap.read()
                if not ok or frame is None or frame.size == 0:
                    raise RuntimeError('Camera stopped returning usable frames.')
                if self.mirror:
                    frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                with self._lock:
                    self._snapshot = replace(self._snapshot, timestamp=captured, frame=rgb)
                self._frame_ready.set()
        except Exception as error:
            self._fail(error)
        finally:
            if cap is not None:
                cap.release()

    def _infer(self):
        try:
            while not self._stop.is_set() and not self._frame_ready.wait(.1):
                pass
            if self._stop.is_set():
                return
            with self._lock:
                self._snapshot = replace(self._snapshot, phase='Loading SmolVLM2')
            model = LocalModel(self.device, self.offline, REVISION)
            last_capture = 0
            while not self._stop.is_set():
                snapshot = self.latest()
                if snapshot.timestamp == last_capture or snapshot.frame is None:
                    self._stop.wait(.01)
                    continue
                # Latest frame only: never queue old frames behind slow inference.
                last_capture = snapshot.timestamp
                answer, latency = model.predict(snapshot.frame)
                with self._lock:
                    if not self._stop.is_set():
                        self._snapshot = replace(self._snapshot, prediction=parse_label(answer),
                            prediction_timestamp=last_capture, raw_answer=answer,
                            inference_ms=latency, phase='Tracking')
        except Exception as error:
            self._fail(error)
