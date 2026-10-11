# GPU hand-tracking: what's actually in the repo

Compiled by reading the repo directly (commits, source, README/CONTEXT.md) as of
`main` at commit `265fdc6`. Every claim below cites where it comes from. Nothing
here is inferred or estimated beyond what the cited source states.

## How GPU acceleration is enabled

- CLI flag: `python -m gesture_control --inference-device {cpu,gpu}`, default
  `cpu` (`gesture_control/__main__.py:27-28`).
- Selection logic: `create_detector()` picks
  `mediapipe.tasks.BaseOptions.Delegate.GPU` vs `...Delegate.CPU` based on that
  flag and passes it into `HandLandmarkerOptions` (`gesture_control/tracking.py:36-47`).
- This is **MediaPipe's own GPU delegate, not TensorRT**. It "does not promise
  that every operation uses CUDA or that inference will be faster. MediaPipe may
  still run some pipeline operations on CPU." (README.md, "GPU inference on the
  Jetson" section).
- **No application-level CPU fallback**: if GPU delegate creation fails, it
  raises `RuntimeError(f'{device.upper()} model initialization failed (no CPU
  fallback): {error}')` and the program stops (`gesture_control/tracking.py:51`).
  This is covered by a unit test that mocks the MediaPipe factory to simulate a
  GPU failure and asserts no CPU retry happens (`tests/test_tracking.py`,
  `test_gpu_failure_does_not_retry_on_cpu`) — the test verifies this error-handling
  code path, not real GPU hardware.
- The device label and the measured inference time for the *current* frame are
  shown in the Python app's own Pygame sidebar (`device_label`, `snapshot.inference_ms`
  in `gesture_control/__main__.py:247-248`). This is local to the Python process
  and is **not** sent anywhere (see "UDP packet contents" below).

## Device and software versions reported in the repo

- Target device, as stated by the team (not independently verified by this
  repo): **NVIDIA Jetson Orin Nano**, **JetPack 7.2.1-b49**, **Python 3.12.3**,
  **Linux aarch64**, **glibc 2.39** (README.md "Jetson setup"; CONTEXT.md line 56
  states the same target and adds: *"Jetson camera operation and performance
  have not yet been verified."*).
- `mediapipe==1.1.0` is pinned in `requirements.txt`. README states this
  version "has a Linux ARM64 wheel" (no further detail on whether that wheel
  was actually installed/run on the target device).
- Other pinned dependencies (`requirements.txt`): `opencv-contrib-python>=4.10,<5`,
  `pygame>=2.6,<3`.
- README, same section, in full: *"This repository has not yet been tested on
  that device."*

## Measured numbers (with source and conditions)

- **The only real-hardware claim in the repo**: *"The team successfully tested
  GPU model initialization and blank-frame inference on their Jetson."*
  (README.md, "GPU inference on the Jetson"). This is qualitative (it
  succeeded/failed) — no timing, FPS, or other number is attached to it, and no
  camera or live gesture input is implied ("blank-frame" only).
- **Explicit statement that no performance number exists yet**: *"No speedup
  has been measured on the team's Jetson by this repository's author yet."*
  (README.md, end of the "Benchmark CPU versus GPU" section).
- A benchmark tool exists (`gesture_control/benchmark.py`, added in commit
  `1959e03 "Jetson GPU Acceleration metrics"`) that runs CPU and GPU detectors
  over the same decoded video frames and reports, per trial and pooled: mean
  and p95 inference time (ms), processing FPS, hand-detection rate, and
  CPU/GPU speedup (`summarize()`/`compare()` in `gesture_control/benchmark.py`).
  Its unit tests (`tests/test_benchmark.py`) check the arithmetic on synthetic
  numbers (e.g. `[10,20,30,40]` → mean 25 → asserted), not on any real capture.
- Its designated input video, `recordings/handtest.mp4`, is present and
  committed (15,057,989 bytes). **Filename mismatch**: the README's documented
  benchmark command refers to `recordings/hand-test.mp4` (with a hyphen); the
  actual tracked file is `recordings/handtest.mp4` (no hyphen) — the command as
  literally written in the README would not find the file.
- `benchmark-results/` (where `summary.csv`/`summary-frames.csv` would land) is
  listed in `.gitignore` (added alongside the benchmark tool in `1959e03`) and
  does not exist in this checkout. No CSV, no numbers, are committed anywhere
  in the repo's history for this tool.
- `models/hand_landmarker.task` (7,819,105 bytes) is present locally but is
  gitignored, not committed — it's fetched by `python -m
  gesture_control.download_model` per the README.

## Not measured (explicit)

- No CPU-vs-GPU inference time, FPS, or speedup number exists anywhere in this
  repo, for any device (Jetson or otherwise) — see above.
- Jetson camera operation and performance: "not yet verified" (CONTEXT.md:56,
  README.md).
- "Package installation and camera performance must be verified on the
  Jetson." (README.md, "Jetson setup").
- No laptop-vs-Jetson comparison has been run; the README documents the command
  to produce one (`--devices cpu --label laptop`) but states none exists yet.
- No UDP-transmitted or HUD-visible performance metric exists: the UDP packet
  sent to the game is built in `gesture_control/__main__.py:190-192` and
  contains exactly `vx, vy, active, status, mode, timestamp` — no backend,
  device, fps, or latency field is included, ever. `relay.mjs` (the UDP→WebSocket
  bridge) forwards exactly `vx, vy, active, status, mode, recvAt` and adds
  nothing (`game/fight/relay.mjs`).

## Did the GPU work survive the two reverts?

**Yes, untouched.** Commit order on `main`:

```
064c312  GPU acceleration for jetson          <- base --inference-device/create_detector work
1959e03  Jetson GPU Acceleration metrics       <- benchmark.py, recordings/handtest.mp4
f9fb76f  Attempting hugging face model         <- unrelated experiment (experiments/smolvlm_probe.py)
8484ba4  Openface test2                        <- unrelated experiment (adds 3 unused Snapshot fields)
b4141d2  Revert "Openface test2"
a84a594  Revert "Attempting hugging face model"
```

The two reverted commits only touched an unrelated, abandoned experiment
(probing OpenFace/SmolVLM-style models as an alternative to MediaPipe) in
`experiments/` and added three now-removed fields to the `Snapshot` dataclass.
Diffing the current `gesture_control/tracking.py` against its state right
after `1959e03` shows **zero difference** — the GPU delegate selection, the
`--inference-device` flag, and `create_detector()` are exactly as they were
before the reverted detour.

## Sources checked

`README.md`, `CONTEXT.md`, `requirements.txt`, `.gitignore`,
`gesture_control/tracking.py`, `gesture_control/__main__.py`,
`gesture_control/benchmark.py`, `tests/test_tracking.py`,
`tests/test_benchmark.py`, `game/fight/relay.mjs`, `recordings/` and `models/`
directory listings, and `git log`/`git show` on commits `064c312`, `1959e03`,
`f9fb76f`, `8484ba4`, `b4141d2`, `a84a594`, `265fdc6`.
