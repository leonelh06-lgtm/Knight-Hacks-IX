import json
from pathlib import Path
from queue import Queue
import socket
import subprocess
import sys
import tempfile
import time
import unittest

from gesture_control.headless import HeadlessSession, run_headless
from gesture_control.__main__ import parse_args
from gesture_control.controls import Observation
from gesture_control.tracking import Snapshot
from unittest.mock import patch


class HeadlessTests(unittest.TestCase):
    def args(self, folder, *extra):
        with patch('sys.argv', ['gesture_control', '--headless', '--profile', str(Path(folder) / 'cal.json'), *extra]):
            return parse_args()

    def profile(self, folder):
        Path(folder, 'cal.json').write_text(json.dumps({'version': 4, 'hand': 'any',
            'mirror': False, 'calibration': {'closed': .2, 'opened': .9, 'neutral_opening': .55}}))

    def test_saved_profile_moves_and_stale_input_stops_without_gui(self):
        with tempfile.TemporaryDirectory() as folder:
            self.profile(folder)
            session = HeadlessSession(self.args(folder))
            sample = Snapshot(timestamp=10, phase='Tracking',
                observation=Observation(.5, .5, .95, (1, 1, 1, 1), finger_openings=(.95,) * 4))
            self.assertEqual(session.update(sample, 10.1).velocity, (0, -1))
            self.assertFalse(session.update(sample, 11).active)

    def test_pause_and_quit_send_zero_commands(self):
        with tempfile.TemporaryDirectory() as folder:
            self.profile(folder)
            session = HeadlessSession(self.args(folder))
            sample = Snapshot(timestamp=10, observation=Observation(.5, .5, .95, (1,) * 4))
            self.assertFalse(session.update(sample, 10.1, 'p').active)
            self.assertFalse(session.update(sample, 10.2, 'q').active)
            self.assertFalse(session.running)

    def test_missing_or_incompatible_profile_stops_for_terminal_calibration(self):
        with tempfile.TemporaryDirectory() as folder:
            session = HeadlessSession(self.args(folder))
            self.assertIsNotNone(session.wizard)
            self.assertFalse(session.update(Snapshot(timestamp=10), 10.1).active)
            self.profile(folder)
            session = HeadlessSession(self.args(folder, '--mirror'))
            self.assertIsNotNone(session.wizard)

    def test_terminal_calibration_finishes_and_saves_three_poses(self):
        with tempfile.TemporaryDirectory() as folder:
            session = HeadlessSession(self.args(folder))
            now = 10.
            for opening in (.55, .2, .9):
                session.update(Snapshot(timestamp=now), now, '')
                for index in range(16):
                    stamp = now + 1 + index * .2
                    sample = Snapshot(timestamp=stamp,
                        observation=Observation(.5, .5, opening, (1,) * 4))
                    command = session.update(sample, stamp)
                    self.assertFalse(command.active)
                now += 5
            self.assertIsNone(session.wizard)
            self.assertEqual(json.loads(Path(folder, 'cal.json').read_text())['version'], 4)

    def test_failed_pose_retries_without_losing_successful_recording(self):
        with tempfile.TemporaryDirectory() as folder:
            session = HeadlessSession(self.args(folder))
            neutral = Observation(.5, .5, .55, (1,) * 4)
            session.wizard.groups[0] = [neutral] * 16
            session.wizard.step = 1
            session.update(Snapshot(timestamp=10), 10, '')
            session.update(Snapshot(timestamp=23), 23)
            self.assertEqual(len(session.wizard.groups[0]), 16)
            self.assertEqual(session.wizard.step, 1)
            self.assertIsNone(session.wizard.started)

    def test_headless_launch_never_imports_pygame(self):
        script = '''
import builtins, sys
old = builtins.__import__
def guarded(name, *args, **kwargs):
    if name == 'pygame': raise RuntimeError('Headless mode imported Pygame')
    return old(name, *args, **kwargs)
builtins.__import__ = guarded
sys.argv = ['gesture_control', '--headless', '--simulate', '--frames', '2']
from gesture_control.__main__ import main
main()
'''
        result = subprocess.run([sys.executable, '-u', '-c', script], capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, (result.stdout + result.stderr).decode(errors='replace'))
        self.assertIn(b'No demo window', result.stdout)

    def test_camera_worker_receives_gpu_and_sends_movement_then_shutdown(self):
        class FakeTracker:
            options = None
            closed = False
            def __init__(self, *args, **kwargs): FakeTracker.options = kwargs
            def start(self): pass
            def close(self): FakeTracker.closed = True
            def latest(self):
                return Snapshot(timestamp=time.monotonic()-.01, phase='Tracking',
                    observation=Observation(.5, .5, .95, (1,) * 4))
        with tempfile.TemporaryDirectory() as folder, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
            receiver.bind(('127.0.0.1', 0))
            receiver.settimeout(2)
            self.profile(folder)
            args = self.args(folder, '--frames', '3', '--inference-device', 'gpu',
                             '--udp-port', str(receiver.getsockname()[1]))
            run_headless(args, tracker_factory=FakeTracker, commands=Queue())
            packets = []
            while not packets or packets[-1]['status'] != 'Shutdown':
                packets.append(json.loads(receiver.recv(4096)))
            self.assertEqual(FakeTracker.options['inference_device'], 'gpu')
            self.assertTrue(any(p['active'] and p['vy'] == -1 for p in packets))
            self.assertFalse(packets[-1]['active'])
            self.assertTrue(FakeTracker.closed)


if __name__ == '__main__':
    unittest.main()
