"""Throwaway feasibility probe: sampled video frames, no game integration."""

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import mean
import time

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gesture_control.smolvlm_model import MODEL, REVISION, LABELS, PROMPT, parse_label, LocalModel


def sample_frames(video, interval, count):
    import cv2
    cap = cv2.VideoCapture(str(video))
    try:
        if not cap.isOpened():
            raise RuntimeError(f'Cannot open video: {video}')
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not math.isfinite(fps) or fps <= 0:
            raise RuntimeError('Video must have valid FPS metadata.')
        stride = max(1, round(fps * interval))
        index = emitted = 0
        while emitted < count:
            ok, frame = cap.read()
            if not ok:
                break
            if index % stride == 0:
                yield index, index / fps, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                emitted += 1
            index += 1
    finally:
        cap.release()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', required=True, type=Path)
    parser.add_argument('--device', choices=('cuda', 'cpu'), default='cuda')
    parser.add_argument('--interval', type=float, default=2)
    parser.add_argument('--samples', type=int, default=12)
    parser.add_argument('--expected', choices=LABELS,
                        help='Ground truth only for a clip containing ONE held gesture throughout.')
    parser.add_argument('--revision', default=REVISION)
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--dry-run', action='store_true', help='Check video sampling without loading AI.')
    parser.add_argument('--output', type=Path, default=Path('benchmark-results/smolvlm.csv'))
    args = parser.parse_args(argv)
    if not math.isfinite(args.interval) or args.interval <= 0 or args.samples <= 0:
        parser.error('--interval and --samples must be positive.')
    if not args.video.is_file():
        parser.error(f'Video not found: {args.video}')
    metadata_path = args.output.with_suffix('.json')
    if args.video.resolve() in (args.output.resolve(), metadata_path.resolve()):
        parser.error('Output must not overwrite the input video.')
    try:
        frames = iter(sample_frames(args.video, args.interval, args.samples))
        first = next(frames, None)
        if first is None:
            raise RuntimeError('Video has no readable frames.')
        model = None
        if not args.dry_run:
            print(f'Loading {MODEL} on {args.device}; first run downloads weights.', flush=True)
            model = LocalModel(args.device, args.offline, args.revision)
            print('Warming up once (excluded from results)...', flush=True)
            model.predict(first[2])
        from itertools import chain
        args.output.parent.mkdir(parents=True, exist_ok=True)
        latencies = []
        correct = total = 0
        with args.output.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=(
                'frame', 'video_seconds', 'prediction', 'raw_answer',
                'processing_ms', 'expected', 'correct'))
            writer.writeheader()
            for index, seconds, rgb in chain((first,), frames):
                answer, latency = model.predict(rgb) if model else ('', None)
                prediction = parse_label(answer) if model else 'not_run'
                match = prediction == args.expected if args.expected and model else None
                total += 1
                correct += bool(match)
                if latency is not None:
                    latencies.append(latency)
                writer.writerow(dict(frame=index, video_seconds=round(seconds, 3),
                                     prediction=prediction, raw_answer=answer,
                                     processing_ms=latency, expected=args.expected or '',
                                     correct=match if match is not None else ''))
                stream.flush()
                timing = f'{latency:.0f} ms' if latency is not None else 'dry run'
                print(f'{seconds:6.2f}s: {prediction:13s} ({timing}) {answer}', flush=True)
        metadata = dict(model=MODEL, revision=args.revision, device=args.device,
                        dry_run=args.dry_run, video=str(args.video.resolve()),
                        prompt=PROMPT, samples=total, expected=args.expected,
                        mean_processing_ms=mean(latencies) if latencies else None,
                        accuracy=correct / total if args.expected and model else None,
                        timing='Preprocessing + generation + decoding, CUDA synchronized; '
                               'excludes video decode, model loading, and one warmup.')
        if model:
            import transformers
            metadata.update(torch_version=model.torch.__version__,
                            transformers_version=transformers.__version__)
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        print(f'Results: {args.output} and {metadata_path}')
        if latencies:
            print(f'Mean processing: {mean(latencies):.0f} ms per sampled image')
        if metadata['accuracy'] is not None:
            print(f'Agreement with expected gesture: {correct}/{total} '
                  f'({metadata["accuracy"]:.1%})')
        print('Feasibility probe only; sampled images do not measure clinical progress or live game FPS.')
        return 0
    except (ImportError, RuntimeError, OSError, ValueError) as error:
        print(f'Probe failed: {error}')
        print('No alternate model or CPU fallback was used. See experiments/README.md for setup.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
