"""Optional integration check: real demo process and real local UDP socket."""

import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(importlib.util.find_spec('pygame'), 'Pygame not installed; pure controls still testable')
class DemoTests(unittest.TestCase):
    def test_simulated_demo_emits_movement_and_shutdown_stop(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver, tempfile.TemporaryDirectory() as folder:
            receiver.bind(('127.0.0.1', 0))
            receiver.settimeout(15)
            port = receiver.getsockname()[1]
            screenshot = Path(folder) / 'demo.png'
            environment = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
            process = subprocess.Popen([sys.executable, '-m', 'gesture_control', '--simulate',
                                       '--frames', '20', '--udp-port', str(port),
                                       '--screenshot', str(screenshot)], env=environment,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            packets = []
            try:
                while True:
                    packet = json.loads(receiver.recv(4096))
                    packets.append(packet)
                    if packet['status'] == 'Shutdown':
                        break
                stdout, stderr = process.communicate(timeout=15)
                self.assertEqual(process.returncode, 0, (stdout + stderr).decode(errors='replace'))
                self.assertTrue(any(packet['vx'] > 0 and packet['active'] for packet in packets))
                self.assertEqual((packets[-1]['vx'], packets[-1]['vy'], packets[-1]['active']), (0, 0, False))
                self.assertGreater(screenshot.stat().st_size, 1000)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate()

    def test_simulated_demo_emits_rover_game_state(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
            receiver.bind(('127.0.0.1', 0))
            receiver.settimeout(15)
            port = receiver.getsockname()[1]
            environment = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
            process = subprocess.Popen(
                [sys.executable, '-m', 'gesture_control', '--simulate',
                 '--frames', '20', '--rover-udp-port', str(port)],
                env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            packets = []
            try:
                while True:
                    packet = json.loads(receiver.recv(4096))
                    packets.append(packet)
                    if packet['active'] is False:
                        break
                stdout, stderr = process.communicate(timeout=15)
                self.assertEqual(process.returncode, 0, (stdout + stderr).decode(errors='replace'))
                self.assertTrue(any(packet['type'] == 'game_state' for packet in packets))
                self.assertEqual((packets[-1]['width'], packets[-1]['height']), (750, 620))
                self.assertFalse(packets[-1]['active'])
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate()
