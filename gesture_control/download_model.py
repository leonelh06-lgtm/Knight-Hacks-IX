"""Fetch the official model once; gameplay reads it locally."""

import argparse
from pathlib import Path
import urllib.request

MODEL_URL = ('https://storage.googleapis.com/mediapipe-models/'
             'hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='models/hand_landmarker.task')
    args = parser.parse_args()
    path = Path(args.output)
    if path.is_file():
        print(f'Model already exists: {path}')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.download')
    try:
        with urllib.request.urlopen(MODEL_URL, timeout=60) as response:
            temporary.write_bytes(response.read())
        if temporary.stat().st_size < 100000:
            raise RuntimeError('Model download was unexpectedly small.')
        temporary.replace(path)
        print(f'Saved model: {path}')
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
