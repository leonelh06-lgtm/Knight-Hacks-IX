"""Check camera frames without loading MediaPipe. No images are saved."""

import argparse
import math
import subprocess
import sys

from .tracking import BACKENDS, open_camera


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--camera', default='0')
    parser.add_argument('--camera-backend', choices=tuple(BACKENDS), default='auto')
    parser.add_argument('--timeout', type=float, default=10)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error('Timeout must be positive.')
    if not args.worker:
        command = [sys.executable, '-m', 'gesture_control.camera_probe', '--worker',
                   '--camera', args.camera, '--camera-backend', args.camera_backend]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=args.timeout)
        except subprocess.TimeoutExpired:
            raise SystemExit(f'Camera {args.camera} ({args.camera_backend}) timed out without completing a frame read. '
                             'Try another backend/index and close other camera apps.')
        print(result.stdout.strip())
        if result.returncode:
            print(result.stderr.strip(), file=sys.stderr)
            raise SystemExit(result.returncode)
        return
    camera = int(args.camera) if args.camera.isdecimal() else args.camera
    cap = open_camera(camera, args.camera_backend)
    try:
        for _ in range(5):
            ok, frame = cap.read()
            if not ok or frame is None or frame.size == 0:
                raise RuntimeError('Camera opened but no usable frame was returned.')
        height, width = frame.shape[:2]
        brightness = float(frame.mean())
        print(f'Camera {args.camera}: frames received, {width}x{height}, '
              f'backend={cap.getBackendName()}, mean brightness={brightness:.1f}/255')
        if brightness < 2:
            print('Image is nearly black. Check the privacy shutter, lighting, and selected camera.')
    finally:
        cap.release()


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ImportError) as error:
        raise SystemExit(str(error))
