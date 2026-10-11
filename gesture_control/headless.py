"""Camera-to-UDP controls for the web game, without Pygame or a demo window."""

from dataclasses import asdict
import json
from pathlib import Path
from queue import Queue, Empty
import socket
import sys
import threading
import time

from .calibration import STEPS, MIN_SAMPLES, Wizard, build_calibration, CalibrationError
from .controls import Calibration, Controller, Observation
from .tracking import Snapshot, Tracker


class HeadlessSession:
    def __init__(self, args):
        self.args = args
        self.controller = Controller(mode=args.mode, pinch_threshold=args.pinch_threshold)
        self.profile = Path(args.profile)
        self.paused = False
        self.running = True
        self.last_stamp = 0
        self.last_command = self.controller.stop('Waiting for camera')
        self.wizard = None
        self.last_report = None
        if args.simulate:
            self.controller.calibration = Calibration(.2, .9)
            print('SIMULATED INPUT: no camera or GPU is being tested.', flush=True)
        elif self.profile.is_file() and not args.calibrate:
            try:
                data = json.loads(self.profile.read_text(encoding='utf-8'))
                if data.get('version') != 4:
                    raise ValueError('Profile is from older controls.')
                if data['hand'] != args.hand or data['mirror'] != args.mirror:
                    raise ValueError('Hand/mirror setting differs from saved calibration.')
                self.controller.calibration = Calibration(**data['calibration'])
                print(f'Calibration loaded: {self.profile}', flush=True)
            except (ValueError, KeyError, TypeError, OSError) as error:
                print(f'Calibration not loaded: {error}', flush=True)
        if not args.simulate and args.mode == 'movement' and self.controller.calibration is None:
            self.wizard = Wizard()
            self.report_step()
        elif args.calibrate and not args.simulate:
            self.wizard = Wizard()
            self.report_step()

    def report_step(self):
        if self.wizard is None:
            return
        print(f'Calibration {self.wizard.step + 1}/{len(STEPS)}: '
              f'{STEPS[self.wizard.step]}\nPress Enter to start recording. '
              'Keep the whole hand visible; recording takes 4 seconds '
              '(may extend to 12 seconds if tracking is sparse).', flush=True)
        self.last_report = None

    def update(self, snapshot, now, line=None):
        self.last_command = self._update(snapshot, now, line)
        return self.last_command

    def _update(self, snapshot, now, line=None):
        if snapshot.error:
            raise RuntimeError(snapshot.error)
        if line is not None:
            key = line.strip().lower()
            if key == 'q':
                self.running = False
            elif key == 'p':
                self.paused = not self.paused
                if self.wizard is not None:
                    self.wizard.started = None
                    self.report_step()
                print('Paused' if self.paused else 'Resumed', flush=True)
            elif key == 'c':
                self.wizard = Wizard()
                self.paused = False
                self.report_step()
            elif key == '' and self.wizard is not None and not self.paused:
                if self.wizard.started is None:
                    self.wizard.start_step(now)
                    print('Recording started. Hold the requested pose.', flush=True)
        fresh = snapshot.timestamp != self.last_stamp
        self.last_stamp = snapshot.timestamp
        age = now - snapshot.timestamp
        observation = snapshot.observation if 0 <= age <= self.args.stale_after else None
        if not self.running or self.paused:
            return self.controller.stop('Shutdown' if not self.running else 'Paused')
        if self.wizard is not None:
            stopped = self.controller.stop('Calibrating')
            if self.wizard.started is None:
                return stopped
            try:
                old_step = self.wizard.step
                if self.wizard.update(now, observation, fresh):
                    self.controller.calibration = build_calibration(self.wizard.groups)
                    try:
                        self.profile.parent.mkdir(parents=True, exist_ok=True)
                        self.profile.write_text(json.dumps({'version': 4, 'hand': self.args.hand,
                            'mirror': self.args.mirror,
                            'calibration': asdict(self.controller.calibration)}, indent=2), encoding='utf-8')
                        print(f'Calibration saved: {self.profile}', flush=True)
                    except OSError as error:
                        print(f'Calibration usable, but could not save it: {error}', flush=True)
                    self.wizard = None
                    print('Calibration complete. Play Ethan\'s game in the browser.', flush=True)
                elif self.wizard.step != old_step:
                    self.report_step()
                else:
                    elapsed = int(now - self.wizard.started)
                    if elapsed != self.last_report:
                        self.last_report = elapsed
                        print(f'Recording {elapsed}s; tracked samples '
                              f'{len(self.wizard.groups[self.wizard.step])}/{MIN_SAMPLES}', flush=True)
            except CalibrationError as error:
                print(str(error), flush=True)
                self.wizard.retry_step(error.step)
                self.report_step()
            return stopped
        # Re-evaluate fresh/validity every tick so missing or stale input stops
        # immediately. The primary cardinal controls do not use velocity smoothing.
        if observation is None:
            return self.controller.stop('Hand missing or camera frame stale')
        if fresh:
            return self.controller.update(observation)
        return self.last_command


def read_terminal(commands):
    for line in sys.stdin:
        commands.put(line.rstrip('\r\n'))
    commands.put('__eof__')


def run_headless(args, tracker_factory=Tracker, commands=None):
    print(f'Headless controller -> UDP 127.0.0.1:{args.udp_port}. No demo window.', flush=True)
    print('Terminal commands: c + Enter recalibrates, p + Enter pauses/resumes, '
          'q + Enter quits; Ctrl+C also stops.', flush=True)
    session = HeadlessSession(args)
    if commands is None:
        commands = Queue()
        if not sys.stdin.isatty() and session.wizard is not None:
            raise RuntimeError('Calibration needs an interactive terminal. Run with a terminal '
                               'attached, or provide a compatible saved --profile.')
        threading.Thread(target=read_terminal, args=(commands,), daemon=True).start()
    tracker = None
    preview = None
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    count = 0
    last_status = last_phase = None
    try:
        if getattr(args, 'web_preview_port', None) is not None:
            from .web_preview import PreviewServer
            preview = PreviewServer(port=args.web_preview_port)
            try:
                preview.start()
                print(f'Tracking preview: http://127.0.0.1:{preview.port}', flush=True)
            except OSError as error:
                print(f'Preview unavailable; controls continue: {error}', flush=True)
                preview.close()
                preview = None
        if not args.simulate:
            camera = int(args.camera) if args.camera.isdecimal() else args.camera
            tracker = tracker_factory(args.model, camera, args.hand, args.mirror,
                backend=args.camera_backend, startup_timeout=args.camera_timeout,
                inference_device=args.inference_device)
            tracker.start()
        while session.running:
            started = now = time.monotonic()
            snapshot = (Snapshot(timestamp=now, phase='Tracking',
                        observation=Observation(.5, .5, .95, (1,) * 4))
                        if args.simulate else tracker.latest())
            if snapshot.phase != last_phase:
                last_phase = snapshot.phase
                print('[tracking] ' + snapshot.phase, flush=True)
            try:
                line = commands.get_nowait()
            except Empty:
                line = None
            if line == '__eof__':
                if session.wizard is not None:
                    raise RuntimeError('Terminal input closed during calibration.')
                line = None
            command = session.update(snapshot, now, line)
            if preview is not None:
                preview.update(snapshot, command, paused=session.paused,
                    calibrating=session.wizard is not None, simulated=args.simulate,
                    stale_after=args.stale_after)
            packet = {'vx': command.velocity[0], 'vy': command.velocity[1],
                      'active': command.active, 'status': command.status,
                      'mode': session.controller.mode, 'timestamp': now}
            sock.sendto(json.dumps(packet).encode(), ('127.0.0.1', args.udp_port))
            if command.status != last_status:
                last_status = command.status
                print(f'[control] {command.status}; inference {snapshot.inference_ms:.0f} ms', flush=True)
            count += 1
            if args.frames and count >= args.frames:
                break
            time.sleep(max(0, 1 / 30 - (time.monotonic() - started)))
    except KeyboardInterrupt:
        print('Stopping headless controller.', flush=True)
    finally:
        try:
            sock.sendto(json.dumps({'vx': 0, 'vy': 0, 'active': False, 'status': 'Shutdown',
                'mode': session.controller.mode, 'timestamp': time.monotonic()}).encode(),
                ('127.0.0.1', args.udp_port))
        finally:
            sock.close()
            if preview is not None:
                preview.close()
            if tracker is not None:
                tracker.close()
