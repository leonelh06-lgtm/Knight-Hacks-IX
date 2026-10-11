"""Real HTTP boundary tests: freshness must never look like live movement."""
import json
import socket
import threading
import time
import unittest
from dataclasses import dataclass
from urllib.request import urlopen
from unittest.mock import patch
from gesture_control.tracking import Snapshot
from gesture_control.controls import Observation, Command
from gesture_control.__main__ import parse_args
try:
    from gesture_control.web_preview import PreviewServer
except ImportError:
    PreviewServer = None


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(PreviewServer, 'Optional preview service is not implemented')
        self.preview = PreviewServer(port=0)
        self.preview.start()
        self.addCleanup(self.preview.close)
        self.url = f'http://127.0.0.1:{self.preview.port}'

    def publish(self, age=0, **flags):
        sample = Snapshot(timestamp=time.monotonic()-age, phase='Tracking',
            observation=Observation(.5,.5,.95,(1,1,1,1)))
        command = Command((0,-1), 'Open palm: moving up', True)
        self.preview.update(sample, command, paused=flags.get('paused',False),
            calibrating=flags.get('calibrating',False), simulated=flags.get('simulated',False), stale_after=.35)

    def status(self):
        with urlopen(self.url+'/status', timeout=2) as response:
            self.assertEqual(response.headers.get_content_type(), 'application/json')
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
            return json.load(response)

    def test_fresh_command_and_expiring_capture(self):
        self.publish()
        self.assertEqual(self.status()['direction'], 'up')
        self.publish(age=1)
        state = self.status()
        self.assertEqual(state['direction'], 'stop')
        self.assertFalse(state['active'])
        self.assertFalse(state['handDetected'])

    def test_pause_calibration_and_simulation_do_not_look_live(self):
        for flag in ('paused', 'calibrating', 'simulated'):
            with self.subTest(flag=flag):
                self.publish(**{flag:True})
                state = self.status()
                self.assertTrue(state[flag])
                self.assertEqual(state['direction'], 'stop')

    def test_stream_wait_does_not_block_publishing_or_shutdown(self):
        response = urlopen(self.url+'/stream.mjpg', timeout=2)
        self.addCleanup(response.close)
        self.assertIn('multipart/x-mixed-replace',response.headers['Content-Type'])
        start = time.monotonic()
        for _ in range(100):
            self.publish()
        self.assertLess(time.monotonic()-start,.2)
        self.preview.close()
        self.assertFalse(self.preview.thread.is_alive())

    def test_occupied_port_does_not_leave_a_server_thread(self):
        other = PreviewServer(port=self.preview.port)
        with self.assertRaises(OSError):
            other.start()
        other.close()

    def test_landmarks_resize_and_valid_mjpeg(self):
        try:
            import cv2
            import numpy as np
        except ImportError:
            self.skipTest('OpenCV test runtime unavailable')
        image = np.zeros((480,640,3),dtype=np.uint8)
        snapshot = Snapshot(timestamp=time.monotonic(),frame=image,
            points=((.5,.5),)*21,phase='Tracking')
        self.preview.update(snapshot,Command((0,0),'No hand',False),
            paused=False,calibrating=False,simulated=False,stale_after=.35)
        with urlopen(self.url+'/stream.mjpg',timeout=2) as response:
            self.assertEqual(response.readline().strip(),b'--frame')
            self.assertEqual(response.readline().strip(),b'Content-Type: image/jpeg')
            size = int(response.readline().split(b':')[1])
            response.readline()
            encoded = response.read(size)
        decoded=cv2.imdecode(np.frombuffer(encoded,dtype=np.uint8),cv2.IMREAD_COLOR)
        self.assertEqual(decoded.shape[:2],(240,320))
        self.assertGreater(int(decoded.max()),100)
        self.assertFalse(image.any(), 'Annotation must not mutate the inference frame')


class PreviewArgumentTests(unittest.TestCase):
    def test_preview_is_opt_in_and_headless_only(self):
        with patch('sys.argv',['controller','--headless']):
            self.assertIsNone(getattr(parse_args(),'web_preview_port','missing'))
        with patch('sys.argv',['controller','--headless','--web-preview-port','8766']):
            self.assertEqual(parse_args().web_preview_port,8766)
        for argv in (['--web-preview-port','8766'],['--headless','--web-preview-port','0']):
            with patch('sys.argv',['controller',*argv]), self.assertRaises(SystemExit):
                parse_args()
