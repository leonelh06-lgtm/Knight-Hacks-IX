"""Run the local gesture controller and top-down forest demo."""

import argparse
from dataclasses import asdict
import json
import math
from pathlib import Path
import random
import socket
import time

from .calibration import (STEPS, Wizard, build_calibration, CalibrationError,
                          MIN_SAMPLES, RECORDING_SECONDS, MAX_RECORDING_SECONDS)
from .controls import Calibration, Controller, Observation, advance
from .tracking import Snapshot, Tracker, BACKENDS

SIZE = (1120, 760)
ARENA = (750, 620)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--camera', default='0', help='Camera index or device path')
    parser.add_argument('--camera-backend', choices=tuple(BACKENDS), default='auto')
    parser.add_argument('--camera-timeout', type=float, default=30, help='Camera/model startup timeout in seconds')
    parser.add_argument('--model', default='models/hand_landmarker.task')
    parser.add_argument('--inference-device', choices=('cpu', 'gpu'), default='cpu',
                        help='MediaPipe inference delegate (GPU requires a supported build/driver)')
    parser.add_argument('--mode', choices=('movement', 'pinch'), default='movement')
    parser.add_argument('--hand', choices=('any', 'left', 'right'), default='any')
    mirror_options = parser.add_mutually_exclusive_group()
    mirror_options.add_argument('--mirror', dest='mirror', action='store_true',
                                help='Mirror camera input horizontally')
    mirror_options.add_argument('--no-mirror', dest='mirror', action='store_false')
    parser.set_defaults(mirror=False)
    parser.add_argument('--no-preview', action='store_true')
    parser.add_argument('--fullscreen', action='store_true')
    parser.add_argument('--profile', default='calibration.json')
    parser.add_argument('--speed', type=float, default=180, help='Maximum pixels/second')
    parser.add_argument('--pinch-threshold', type=float, default=.28, help='Thumb-tip distance / palm length')
    parser.add_argument('--stale-after', type=float, default=.35, help='Maximum capture age in seconds')
    parser.add_argument('--udp-port', type=int, help='Optional JSON control output to 127.0.0.1')
    parser.add_argument('--simulate', action='store_true', help='Exercise demo without a camera or MediaPipe')
    parser.add_argument('--frames', type=int, default=0, help='Exit after N frames (0 = interactive)')
    parser.add_argument('--screenshot', help='Save final demo frame to a PNG')
    args = parser.parse_args()
    if any(not math.isfinite(v) or v <= 0 for v in
           (args.speed, args.pinch_threshold, args.stale_after, args.camera_timeout)) or args.frames < 0:
        parser.error('Speed, pinch threshold and stale timeout must be positive; frames must be nonnegative.')
    if args.udp_port is not None and not 1 <= args.udp_port <= 65535:
        parser.error('UDP port must be between 1 and 65535.')
    return args


def main():
    args = parse_args()
    print(f'[startup] Controller starting: camera={args.camera}, '
          f'device={args.inference_device}, udp={args.udp_port or "disabled"}', flush=True)
    if not args.simulate and not Path(args.model).is_file():
        raise SystemExit('Model missing. Run: python -m gesture_control.download_model')
    try:
        print('[startup] Importing Pygame', flush=True)
        import pygame
    except ImportError:
        raise SystemExit('Dependencies missing. Run: python -m pip install -r requirements.txt')
    # Only these subsystems are used. Full pygame.init() also initializes audio
    # and joysticks, which can block even when the display itself is working.
    print('[startup] Initializing display', flush=True)
    pygame.display.init()
    print('[startup] Initializing fonts', flush=True)
    pygame.font.init()
    print('[startup] Opening controller window', flush=True)
    desktop_width, desktop_height = pygame.display.get_desktop_sizes()[0]
    window_size = SIZE if args.fullscreen else (
        min(SIZE[0], max(640, desktop_width - 80)),
        min(SIZE[1], max(480, desktop_height - 100)))
    display = pygame.display.set_mode(window_size, pygame.FULLSCREEN if args.fullscreen else pygame.RESIZABLE)
    print('[startup] Window ready; camera preview/calibration is here. '
          "Play Ethan's levels in the browser.", flush=True)
    pygame.display.set_caption('Forest Motion - local hand control')
    canvas = pygame.Surface(SIZE)
    font = pygame.font.Font(None, 25)
    title_font = pygame.font.Font(None, 38)
    clock = pygame.time.Clock()
    controller = Controller(mode=args.mode, pinch_threshold=args.pinch_threshold)
    profile = Path(args.profile)
    note = 'Press C to calibrate your comfortable movement.'
    if args.simulate:
        controller.calibration = Calibration(.2, .9)
        note = 'SIMULATED INPUT - hardware is not being tested.'
    elif profile.is_file():
        try:
            data = json.loads(profile.read_text(encoding='utf-8'))
            if data.get('version') != 4:
                raise ValueError('Older control profile; press C for relaxed, fist, open calibration.')
            if data['hand'] != args.hand or data['mirror'] != args.mirror:
                raise ValueError('Hand or mirror setting changed; recalibrate.')
            controller.calibration = Calibration(**data['calibration'])
            note = 'Profile loaded. Press C if player or camera position changed.'
        except (ValueError, KeyError, TypeError, OSError) as error:
            note = f'Profile not loaded: {error}'
    tracker = None
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) if args.udp_port else None
    if not args.simulate:
        camera = int(args.camera) if args.camera.isdecimal() else args.camera
        tracker = Tracker(args.model, camera, args.hand, args.mirror,
                          backend=args.camera_backend, startup_timeout=args.camera_timeout,
                          inference_device=args.inference_device)
        tracker.start()
        print('[startup] Camera/model worker started', flush=True)
    rng = random.Random(7)
    trees = [(rng.randrange(25, ARENA[0] - 25), rng.randrange(25, ARENA[1] - 25), rng.randrange(16, 28))
             for _ in range(38)]
    trees = [(x, y, r) for x, y, r in trees if x < 80 or x > 670 or y < 70 or y > 550]
    position = (ARENA[0] / 2, ARENA[1] / 2)
    wizard = None
    paused = False
    running = True
    last_stamp = 0
    last_send = 0
    frame_count = 0
    command = controller.stop('Waiting for camera')
    preview_stamp = 0
    preview = None
    last_phase = None
    try:
        while running:
            dt = clock.tick(60) / 1000
            now = time.monotonic()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False
                    elif event.key == pygame.K_SPACE:
                        paused = not paused
                        command = controller.stop()
                        if paused and wizard is not None:
                            wizard.started = None
                            note = 'Recording cancelled. Resume, then press Enter to retry the step.'
                    elif event.key == pygame.K_c:
                        wizard = Wizard()
                        paused = False
                        note = ''
                        command = controller.stop('Calibrating')
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and wizard is not None:
                        if wizard.started is None:
                            wizard.start_step(now)
                            note = ''
                    elif event.key == pygame.K_m:
                        controller.mode = 'pinch' if controller.mode == 'movement' else 'movement'
                        command = controller.stop('Mode changed')
                        last_stamp = 0
                    elif event.key == pygame.K_r:
                        position = (ARENA[0] / 2, ARENA[1] / 2)
                        command = controller.stop('Reset')
                        last_stamp = 0
            if args.simulate:
                gestures = (
                    (.75, (1, 1, 1, .1), (.9, .9, .9, .3)),
                    (.95, (1, 1, 1, 1), (.95,) * 4),
                    (.2, (.1, .1, .1, .1), (.2,) * 4),
                    (.75, (.1, 1, 1, 1), (.3, .9, .9, .9)),
                    (.55, (1, 1, 1, 1), (.55,) * 4),
                )
                opening, pinches, fingers = gestures[(frame_count // 120) % len(gestures)]
                snapshot = Snapshot(now, Observation(.5, .5, opening, pinches,
                                    finger_openings=fingers), phase='Tracking')
            else:
                snapshot = tracker.latest()
                if snapshot.phase != last_phase:
                    print('[tracking] ' + snapshot.phase, flush=True)
                    last_phase = snapshot.phase
            fresh = snapshot.timestamp != last_stamp
            age = now - snapshot.timestamp
            observation = snapshot.observation if 0 <= age <= args.stale_after else None
            if snapshot.error:
                raise RuntimeError(snapshot.error)
            if wizard is not None:
                command = controller.stop('Calibrating')
                try:
                    if not paused and wizard.update(now, observation, fresh):
                        controller.calibration = build_calibration(wizard.groups)
                        profile.parent.mkdir(parents=True, exist_ok=True)
                        profile.write_text(json.dumps({'version': 4, 'hand': args.hand, 'mirror': args.mirror,
                                           'calibration': asdict(controller.calibration)}, indent=2), encoding='utf-8')
                        wizard = None
                        note = 'Open: up | Fist: down | Index pinch: left | Pinkie pinch: right | Relaxed: stop'
                except CalibrationError as error:
                    note = str(error)
                    wizard.retry_step(error.step)
                except OSError as error:
                    # A completed profile is still usable if saving fails.
                    wizard = None
                    note = f'Calibration complete, but profile could not be saved: {error}'
            elif paused or not running:
                command = controller.stop('Paused')
            elif observation is None:
                command = controller.stop('Hand missing or camera frame stale')
            elif fresh:
                command = controller.update(observation)
            last_stamp = snapshot.timestamp
            position = advance(position, command.velocity, args.speed, dt, ARENA, 15)
            if udp is not None and now - last_send >= 1 / 30:
                packet = {'vx': command.velocity[0], 'vy': command.velocity[1],
                          'active': command.active, 'status': command.status,
                          'mode': controller.mode, 'timestamp': now}
                udp.sendto(json.dumps(packet).encode('utf-8'), ('127.0.0.1', args.udp_port))
                last_send = now
            canvas.fill((12, 22, 27))
            arena_rect = pygame.Rect(20, 75, *ARENA)
            pygame.draw.rect(canvas, (25, 51, 46), arena_rect, border_radius=12)
            for x in range(40, ARENA[0], 60):
                for y in range(35, ARENA[1], 60):
                    pygame.draw.circle(canvas, (36, 70, 58), (x + 20, y + 75), 2)
            for x, y, radius in trees:
                pygame.draw.circle(canvas, (15, 37, 37), (x + 23, y + 80), radius + 3)
                pygame.draw.circle(canvas, (39, 85, 67), (x + 20, y + 75), radius)
                pygame.draw.circle(canvas, (56, 108, 81), (x + 17, y + 71), radius // 2)
            pygame.draw.rect(canvas, (82, 140, 121), arena_rect, 2, border_radius=12)
            px, py = int(position[0]) + 20, int(position[1]) + 75
            pygame.draw.circle(canvas, (47, 116, 131), (px, py), 23)
            pygame.draw.circle(canvas, (159, 236, 229), (px, py), 14)
            pygame.draw.circle(canvas, (242, 250, 219), (px - 4, py - 4), 4)
            if command.active:
                dx, dy = command.velocity
                tip = (px + int(dx * 38), py + int(dy * 38))
                color = (237, 240, 173) if command.active else (113, 155, 149)
                pygame.draw.line(canvas, color, (px, py), tip, 3)
                pygame.draw.polygon(canvas, color, [tip,
                    (tip[0] - dx * 10 - dy * 6, tip[1] - dy * 10 + dx * 6),
                    (tip[0] - dx * 10 + dy * 6, tip[1] - dy * 10 - dx * 6)])
            def text(message, x, y, heading=False, color=(213, 233, 221)):
                canvas.blit((title_font if heading else font).render(message, True, color), (x, y))
            text('FOREST MOTION', 22, 23, True)
            text('Palm-facing hand control', 390, 30)
            text(controller.mode.upper() + ' MODE', 795, 80, True)
            text(f'Camera {args.camera} ({args.camera_backend})', 795, 113)
            if not args.no_preview and snapshot.frame is not None:
                if preview_stamp != snapshot.timestamp:
                    rgb = snapshot.frame
                    preview = pygame.image.frombuffer(rgb.tobytes(), (rgb.shape[1], rgb.shape[0]), 'RGB').copy()
                    for x, y in snapshot.points:
                        pygame.draw.circle(preview, (130, 255, 210),
                                           (int(x * rgb.shape[1]), int(y * rgb.shape[0])), 4)
                    if len(snapshot.points) == 21:
                        thumb = snapshot.points[4]
                        for finger_index, tip_index in ((0, 8), (3, 20)):
                            tip = snapshot.points[tip_index]
                            touching = snapshot.observation is not None and snapshot.observation.pinches[finger_index] < args.pinch_threshold
                            color = (255, 220, 80) if touching else (100, 150, 160)
                            pygame.draw.line(preview, color,
                                (int(thumb[0] * rgb.shape[1]), int(thumb[1] * rgb.shape[0])),
                                (int(tip[0] * rgb.shape[1]), int(tip[1] * rgb.shape[0])), 3)
                    preview = pygame.transform.smoothscale(preview, (300, 225))
                    preview_stamp = snapshot.timestamp
                if preview is not None:
                    canvas.blit(preview, (795, 130))
            if not args.simulate and snapshot.phase != 'Tracking':
                pygame.draw.rect(canvas, (12, 22, 27), (795, 130, 300, 30))
                text(snapshot.phase + '...', 800, 135)
            device_label = 'SIMULATED' if args.simulate else args.inference_device.upper()
            text(f'{device_label} inference: {snapshot.inference_ms:.0f} ms', 795, 372)
            text(f'Frame age: {min(age, 99):.2f} s', 795, 399)
            if observation:
                text(f'Opening estimate: {observation.opening:.2f}', 795, 426)
                text(f'Pinches I:{observation.pinches[0]:.2f} P:{observation.pinches[3]:.2f}', 795, 449)
            text('C  Calibrate    Enter  Record step', 795, 470)
            text('M  Switch control mode', 795, 501)
            text('Space  Pause / resume', 795, 532)
            text('R  Reset player    Q / Esc  Exit', 795, 563)
            if controller.mode == 'movement':
                text('Open: UP     Fist: DOWN', 795, 603)
                text('Index: LEFT     Pinkie: RIGHT', 795, 630)
                text('Relaxed / unclear: STOP', 795, 657)
            else:
                text('Pinch: index left / middle up', 795, 603)
                text('Ring right / little finger down', 795, 630)
                text('Release the touch: STOP', 795, 657)
            if wizard is not None:
                # Keep recording feedback visible even on small laptop displays.
                panel = pygame.Rect(55, 190, 680, 365)
                pygame.draw.rect(canvas, (12, 22, 27), panel, border_radius=12)
                pygame.draw.rect(canvas, (159, 236, 229), panel, 2, border_radius=12)
                text(f'CALIBRATION - STEP {wizard.step + 1} OF {len(STEPS)}', 80, 240, True)
                words = STEPS[wizard.step].split()
                line, lines = '', []
                for word in words:
                    candidate = (line + ' ' + word).strip()
                    if font.size(candidate)[0] > 620:
                        lines.append(line)
                        line = word
                    else:
                        line = candidate
                lines.append(line)
                for index, line in enumerate(lines):
                    text(line, 80, 285 + index * 27)
                if paused:
                    text('Paused - press Space to resume', 80, 355, True)
                elif wizard.started is None:
                    text('Tap Enter to start this step', 80, 355, True)
                    text('Click the game window first. No need to hold Enter.', 80, 399)
                else:
                    duration = RECORDING_SECONDS
                    remaining = max(0, duration - (now - wizard.started))
                    if remaining > 0:
                        text(f'Recording: {remaining:.1f} seconds remaining', 80, 355, True)
                    else:
                        extra = max(0, MAX_RECORDING_SECONDS - (now - wizard.started))
                        text(f'Collecting samples: {extra:.1f}s remaining', 80, 355, True)
                    samples = len(wizard.groups[wizard.step])
                    text(f'Tracked samples: {samples}/{MIN_SAMPLES} | ' +
                         ('Hand detected' if observation is not None else 'Hand not detected / frame stale'),
                         80, 399)
                if note:
                    error_lines, error_line = [], ''
                    for word in note.split():
                        candidate = (error_line + ' ' + word).strip()
                        if font.size(candidate)[0] > 620:
                            error_lines.append(error_line)
                            error_line = word
                        else:
                            error_line = candidate
                    error_lines.append(error_line)
                    for index, error_line in enumerate(error_lines[:4]):
                        text(error_line, 80, 433 + index * 26, color=(255, 194, 137))
                text(f'Calibration {wizard.step + 1}/{len(STEPS)}: {STEPS[wizard.step]}', 22, 710)
                if wizard.started is None:
                    text('Press Enter when ready. ' + note, 22, 737)
                else:
                    text(f'Recording... {now - wizard.started:.1f}s; keep the hand visible', 22, 737)
            else:
                text(command.status, 22, 710)
                text(note, 22, 737)
            display.blit(pygame.transform.smoothscale(canvas, display.get_size()), (0, 0))
            pygame.display.flip()
            frame_count += 1
            if args.frames and frame_count >= args.frames:
                running = False
        if args.screenshot:
            pygame.image.save(canvas, args.screenshot)
    finally:
        if udp is not None:
            try:
                udp.sendto(json.dumps({'vx': 0, 'vy': 0, 'active': False,
                           'status': 'Shutdown', 'mode': controller.mode,
                           'timestamp': time.monotonic()}).encode(), ('127.0.0.1', args.udp_port))
            finally:
                udp.close()
        if tracker is not None:
            tracker.close()
        pygame.quit()


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError) as error:
        raise SystemExit(str(error))
