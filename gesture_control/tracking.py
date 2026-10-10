"""Camera and CPU inference worker; rendering never waits on camera reads."""

from dataclasses import dataclass, replace
from pathlib import Path
import threading
import time

from .controls import from_landmarks


@dataclass(frozen=True)
class Snapshot:
    timestamp: float = 0
    observation: object = None
    frame: object = None
    points: tuple = ()
    inference_ms: float = 0
    error: str = ''
    phase: str = 'Opening camera'


BACKENDS = {'auto': 'CAP_ANY', 'dshow': 'CAP_DSHOW', 'msmf': 'CAP_MSMF',
            'v4l2': 'CAP_V4L2', 'gstreamer': 'CAP_GSTREAMER'}


def open_camera(camera, backend='auto'):
    import cv2
    cap = cv2.VideoCapture(camera, getattr(cv2, BACKENDS[backend]))
    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f'Cannot open camera {camera} using {backend}. '
                           'Check the index, camera permissions, and other apps using the camera.')
    return cap


class Tracker:
    def __init__(self, model, camera=0, hand='any', mirror=False,
                 backend='auto', startup_timeout=30):
        self.model = Path(model)
        self.camera = camera
        self.hand = hand
        self.mirror = mirror
        if backend not in BACKENDS or startup_timeout <= 0:
            raise ValueError('Invalid camera backend or startup timeout.')
        self.backend = backend
        self.startup_timeout = startup_timeout
        self.started_at = time.monotonic()
        self._lock = threading.Lock()
        self._snapshot = Snapshot()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.started_at = time.monotonic()
        self._thread.start()

    def latest(self, now=None):
        with self._lock:
            snapshot = self._snapshot
        now = time.monotonic() if now is None else now
        if not snapshot.error and snapshot.phase != 'Tracking' and now - self.started_at > self.startup_timeout:
            return replace(snapshot, error=f'{snapshot.phase} timed out after {self.startup_timeout:g}s. '
                           'On Windows try --camera-backend dshow. Close other camera apps and check permissions.')
        return snapshot

    def close(self):
        self._stop.set()
        self._thread.join(timeout=2)

    def _publish(self, snapshot):
        with self._lock:
            self._snapshot = snapshot

    def _run(self):
        cap = None
        try:
            import cv2
            cap = open_camera(self.camera, self.backend)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self._publish(Snapshot(phase='Waiting for first camera frame'))
            captured = time.monotonic()
            ok, first_frame = cap.read()
            if not ok or first_frame is None or first_frame.size == 0:
                raise RuntimeError('Camera opened but returned no image. Try a different camera backend or index.')
            if self.mirror:
                first_frame = cv2.flip(first_frame, 1)
            self._publish(Snapshot(timestamp=captured,
                                   frame=cv2.cvtColor(first_frame, cv2.COLOR_BGR2RGB),
                                   phase='Loading hand model'))
            import mediapipe as mp
            from mediapipe.tasks.python import vision
            options = vision.HandLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(self.model),
                                                 delegate=mp.tasks.BaseOptions.Delegate.CPU),
                running_mode=vision.RunningMode.VIDEO,
                num_hands=1 if self.hand == 'any' else 2,
                min_hand_detection_confidence=.6,
                min_hand_presence_confidence=.6,
                min_tracking_confidence=.6)
            last_ms = -1
            with vision.HandLandmarker.create_from_options(options) as detector:
                while not self._stop.is_set():
                    # Timestamp BEFORE read: a stalled read cannot yield a fresh-looking command.
                    captured = time.monotonic()
                    ok, frame = cap.read()
                    if not ok or frame is None or frame.size == 0:
                        raise RuntimeError('Camera stopped returning frames. Reconnect it and restart.')
                    if self.mirror:
                        frame = cv2.flip(frame, 1)
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    timestamp_ms = max(last_ms + 1, int(captured * 1000))
                    last_ms = timestamp_ms
                    start = time.monotonic()
                    result = detector.detect_for_video(
                        mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp_ms)
                    inference_ms = (time.monotonic() - start) * 1000
                    observation, points = None, ()
                    for landmarks, handedness in zip(result.hand_landmarks, result.handedness):
                        label = handedness[0].category_name.lower()
                        if not self.mirror:
                            label = 'right' if label == 'left' else 'left'
                        if self.hand != 'any' and label != self.hand:
                            continue
                        try:
                            observation = from_landmarks(landmarks, aspect_ratio=rgb.shape[0] / rgb.shape[1])
                            points = tuple((point.x, point.y) for point in landmarks)
                        except ValueError:
                            pass
                        break
                    self._publish(Snapshot(captured, observation, rgb, points, inference_ms, phase='Tracking'))
        except Exception as error:
            self._publish(Snapshot(error=f'{type(error).__name__}: {error}'))
        finally:
            if cap is not None:
                cap.release()
