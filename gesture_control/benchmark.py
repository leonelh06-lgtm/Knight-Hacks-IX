"""Replay identical video frames to compare CPU and GPU hand tracking."""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import math
from pathlib import Path
import platform
from statistics import mean
import time

from .controls import from_landmarks
from .tracking import create_detector


def summarize(latencies, detected, elapsed):
    if not latencies or elapsed <= 0 or not math.isfinite(elapsed):
        raise ValueError('A benchmark needs measured frames and positive elapsed time.')
    if not all(math.isfinite(value) and value > 0 for value in latencies):
        raise ValueError('Inference times must be finite and positive.')
    if not 0 <= detected <= len(latencies):
        raise ValueError('Invalid detection count.')
    ordered = sorted(latencies)
    return {'frames': len(latencies), 'mean_inference_ms': mean(latencies),
            'p95_inference_ms': ordered[math.ceil(.95 * len(ordered)) - 1],
            'processing_seconds': elapsed, 'processing_fps': len(latencies) / elapsed,
            'detected_frames': detected, 'detection_rate_percent': 100 * detected / len(latencies)}


def compare(cpu, gpu):
    cpu_ms, gpu_ms = cpu['mean_inference_ms'], gpu['mean_inference_ms']
    if cpu_ms <= 0 or gpu_ms <= 0:
        raise ValueError('Cannot compare zero inference times.')
    return {'inference_speedup': cpu_ms / gpu_ms,
            'inference_latency_reduction_percent': 100 * (1 - gpu_ms / cpu_ms)}


def file_hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def load_clip(path, count, mirror):
    import cv2
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise RuntimeError(f'Cannot open video: {path}')
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not math.isfinite(fps) or fps <= 0:
            raise RuntimeError('Video FPS is missing; use a standard MP4 or AVI recording.')
        frames = []
        while len(frames) < count:
            ok, frame = cap.read()
            if not ok or frame is None or frame.size == 0:
                break
            height, width = frame.shape[:2]
            scale = min(1, 640 / width, 480 / height)
            if scale < 1:
                frame = cv2.resize(frame, (max(1, round(width * scale)), max(1, round(height * scale))))
            if mirror:
                frame = cv2.flip(frame, 1)
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        return frames, fps
    finally:
        cap.release()


def run_trial(model, device, frames, fps, warmup):
    import mediapipe as mp
    latencies, raw = [], []
    detected = 0
    last_timestamp = -1
    with create_detector(model, 'any', device) as detector:
        measured_started = None
        for index, frame in enumerate(frames):
            if index == warmup:
                measured_started = time.perf_counter()
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
            timestamp = max(last_timestamp + 1, round(index * 1000 / fps))
            last_timestamp = timestamp
            started = time.perf_counter_ns()
            result = detector.detect_for_video(image, timestamp)
            inference_ms = (time.perf_counter_ns() - started) / 1_000_000
            usable = False
            if result.hand_landmarks:
                try:
                    from_landmarks(result.hand_landmarks[0], aspect_ratio=frame.shape[0] / frame.shape[1])
                    usable = True
                except ValueError:
                    pass
            if index >= warmup:
                latencies.append(inference_ms)
                detected += usable
                raw.append({'frame_index': index, 'inference_ms': inference_ms,
                            'hand_detected': int(usable)})
        elapsed = time.perf_counter() - measured_started
    return summarize(latencies, detected, elapsed), raw


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', required=True, help='Recorded hand video; live cameras are not used')
    parser.add_argument('--model', default='models/hand_landmarker.task')
    parser.add_argument('--devices', nargs='+', choices=('cpu', 'gpu'), default=['cpu', 'gpu'])
    parser.add_argument('--frames', type=int, default=300, help='Measured frames per trial')
    parser.add_argument('--warmup', type=int, default=20, help='First frames excluded from measurement')
    parser.add_argument('--trials', type=int, default=3)
    parser.add_argument('--mirror', action='store_true')
    parser.add_argument('--label', default=platform.node(), help='Hardware label, e.g. jetson-orin-nano')
    parser.add_argument('--output', default='benchmark-results/summary.csv')
    args = parser.parse_args()
    if args.frames < 1 or args.warmup < 0 or args.trials < 1:
        parser.error('Frames/trials must be positive and warmup must be nonnegative.')
    video, model, output = Path(args.video), Path(args.model), Path(args.output)
    raw_output = output.with_name(output.stem + '-frames.csv')
    if not video.is_file() or not model.is_file():
        parser.error('Video and model must be existing local files.')
    if any(path.resolve() in (video.resolve(), model.resolve()) for path in (output, raw_output)):
        parser.error('Output files must not overwrite the video or model.')
    import mediapipe as mp
    frames, fps = load_clip(video, args.warmup + args.frames, args.mirror)
    if len(frames) <= args.warmup:
        parser.error('Video is too short to leave measured frames after warmup.')
    if len(frames) < args.warmup + args.frames:
        print(f'Clip is shorter than requested: using {len(frames) - args.warmup} measured frames per trial.')
    devices = list(dict.fromkeys(args.devices))
    metadata = {'label': args.label, 'platform': platform.platform(),
                'python_version': platform.python_version(), 'mediapipe_version': mp.__version__,
                'video_sha256': file_hash(video), 'model_sha256': file_hash(model),
                'video_fps': fps, 'width': frames[0].shape[1], 'height': frames[0].shape[0],
                'mirror': args.mirror, 'warmup_frames': args.warmup,
                'time_utc': datetime.now(timezone.utc).isoformat()}
    rows, raw_rows, failed = [], [], set()
    # Alternate which device runs first to reduce consistent order bias.
    for trial in range(1, args.trials + 1):
        order = devices if trial % 2 else list(reversed(devices))
        for device in order:
            if device in failed:
                continue
            print(f'{args.label}: {device.upper()} trial {trial}/{args.trials}', flush=True)
            try:
                stats, samples = run_trial(model, device, frames, fps, args.warmup)
                rows.append({**metadata, 'kind': 'trial', 'device': device, 'trial': trial,
                             'status': 'ok', 'error': '', **stats})
                raw_rows.extend({'device': device, 'trial': trial, **sample} for sample in samples)
                print(f"  Mean {stats['mean_inference_ms']:.2f} ms | p95 {stats['p95_inference_ms']:.2f} ms | "
                      f"{stats['processing_fps']:.1f} processing FPS | {stats['detection_rate_percent']:.1f}% detected")
            except Exception as error:
                failed.add(device)
                rows.append({**metadata, 'kind': 'trial', 'device': device, 'trial': trial,
                             'status': 'error', 'error': str(error)})
                print(f'  FAILED: {error}. No CPU substitution.', flush=True)
    aggregates = {}
    for device in devices:
        if device in failed:
            continue
        trials = [row for row in rows if row['device'] == device and row['status'] == 'ok']
        samples = [row for row in raw_rows if row['device'] == device]
        stats = summarize([row['inference_ms'] for row in samples],
                          sum(row['hand_detected'] for row in samples),
                          sum(row['processing_seconds'] for row in trials))
        aggregates[device] = stats
        rows.append({**metadata, 'kind': 'aggregate', 'device': device, 'trial': 'all',
                     'status': 'ok', 'error': '', **stats})
        if stats['detected_frames'] == 0:
            print(f'WARNING: {device.upper()} detected no usable hands. This clip cannot demonstrate gesture reliability.')
    fields = list(metadata) + ['kind', 'device', 'trial', 'status', 'error', 'frames',
                              'mean_inference_ms', 'p95_inference_ms', 'processing_seconds',
                              'processing_fps', 'detected_frames', 'detection_rate_percent',
                              'inference_speedup', 'inference_latency_reduction_percent']
    comparison = None
    if 'cpu' in aggregates and 'gpu' in aggregates:
        comparison = compare(aggregates['cpu'], aggregates['gpu'])
        for row in rows:
            if row['kind'] == 'aggregate' and row['device'] == 'gpu':
                row.update(comparison)
    write_csv(output, rows, fields)
    write_csv(raw_output, raw_rows, ['device', 'trial', 'frame_index', 'inference_ms', 'hand_detected'])
    print(f'Saved {output} and {raw_output}')
    if comparison is not None:
        print(f"GPU/CPU inference speedup: {comparison['inference_speedup']:.2f}x; "
              f"latency reduction: {comparison['inference_latency_reduction_percent']:.1f}%")
    else:
        print('CPU/GPU speedup unavailable: both devices must complete every trial successfully.')
    print('Processing FPS excludes video decoding, rendering, camera capture, and model initialization. '
          'Detection rate is not an accuracy or rehabilitation measure.')
    if failed:
        raise SystemExit(1)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ImportError, ValueError) as error:
        raise SystemExit(str(error))
