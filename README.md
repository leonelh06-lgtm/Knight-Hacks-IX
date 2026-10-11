# Forest Motion: Jetson gesture control

A local Python hand-control prototype for the project in [CONTEXT.md](CONTEXT.md).
MediaPipe detects hand landmarks; adjustable control logic moves a character inside
a top-down forest arena. Both hands are supported. The hand faces the camera, palm
out. Default controls use **open hand for up, fist for down, index-thumb pinch for
left, and pinkie-thumb pinch for right**. A partially relaxed hand stops movement.
A second mode uses four thumb-to-finger
touches. An autonomous overhead-camera rover can serve as the final boss; see [rover setup](rover/README.md).

## Jetson setup

### Ethan's web game with MediaPipe GPU controls

The web game in `game/fight/debug.html` consumes the same UDP movement packets
produced by this controller. No model conversion is needed: select GPU when
starting the Python controller. Run all three processes on the Jetson; the page
currently connects to `ws://localhost:8765`, so open it in the Jetson's browser.

From the repository root, update and install the web relay once (Node.js/npm required):

```bash
git pull origin main
npm ci --prefix game/fight
```

Terminal 1, from the repository root, starts the UDP-to-WebSocket relay:

```bash
node game/fight/relay.mjs
```

Terminal 2, from the repository root, starts GPU hand detection and sends controls
to the relay's UDP port 5005:

```bash
source .venv/bin/activate
python3 -u -m gesture_control --headless --inference-device gpu --camera 0 --udp-port 5005
```

Use `--camera 1` for a different webcam. **Headless mode opens no Python demo or
camera-preview window**; Ethan's browser page is the game. A compatible saved
calibration is loaded automatically. Otherwise follow the three terminal prompts:
relaxed fingers, fist, then open hand. Press Enter to start each recording. Failed
poses retry without discarding completed recordings. Keep this process running
while playing; only one process should open the webcam. Terminal commands require
Enter: `c` recalibrates, `p` pauses/resumes, `q` quits. Ctrl+C also stops and sends
a zero-movement packet. Use `--calibrate` to force fresh terminal calibration.
Headless mode defaults to UDP port 5005 when `--udp-port` is omitted.

Terminal 3, from the repository root, serves the game:

```bash
python3 -u -m game.serve
```

Open **http://localhost:8000/debug.html** in the Jetson browser, then press B to
start. Open palm = up, fist = down, index-thumb pinch = left, pinkie-thumb pinch =
right. The game HUD displays gesture/link status. It expects relay WebSocket
port 8765; overriding `WS_PORT` alone does not change the browser's hardcoded URL.
Type `p` then Enter in the controller terminal to pause gesture output; Space in
the browser activates the game's shield. The browser currently bridges zero-movement packets for 150ms
and expires disconnected input after 500ms, so stopping can have a short delay.

For a camera-free connection test, keep `--headless` and add `--simulate` to the
controller command. Headless simulation continuously sends UP; it verifies
transport/game input, not GPU inference. The
MediaPipe GPU CPU-comparison benchmark remains documented below.

Target supplied by the team: Orin Nano, JetPack 7.2.1-b49, Python 3.12.3,
Linux aarch64, glibc 2.39. This repository has not yet been tested on that device.
MediaPipe 1.1.0 has a Linux ARM64 wheel. CPU is the default; `--inference-device gpu`
explicitly selects MediaPipe's GPU delegate. Package installation and camera performance
must be verified on the Jetson.

### GPU inference on the Jetson

The team successfully tested GPU model initialization and blank-frame inference on
their Jetson. To use that delegate in the actual program:

```bash
source .venv/bin/activate
python -m gesture_control --inference-device gpu --camera 0 --hand any
```

The sidebar displays the selected CPU/GPU delegate and inference time. Compare the
same camera setup using `--inference-device cpu`. Simulated input is explicitly
labeled SIMULATED and does not test either delegate. GPU errors stop the program
and are reported in the terminal; there is no application-level CPU fallback.
MediaPipe may still run some pipeline operations on CPU. This option uses
MediaPipe's GPU delegate, not TensorRT; it does not promise that every operation
uses CUDA or that inference will be faster. Camera capture, gesture rules, and
calibration remain shared. No recalibration is required solely to switch delegates.

Run from the repository root in the Jetson desktop terminal:

```bash
git pull --ff-only
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m gesture_control.download_model
python -m gesture_control --camera 0 --hand any
```

If venv creation fails because ensurepip is unavailable:

```bash
sudo apt install python3.12-venv
```

The model downloader fetches Google's official version-1 Hand Landmarker bundle
once into `models/`. Subsequent gameplay needs no model download or cloud inference.
No camera images are recorded by this program. MediaPipe's own metrics behavior
is separate from the application's processing; see its upstream privacy notice.

Use a USB webcam initially. `--camera 1` selects another index, and
`--camera /dev/video0` accepts a Linux device path. CSI cameras may require a
camera-specific GStreamer pipeline; that backend is not included yet. Run the
program in a graphical desktop session so Pygame can open a window.

### Empty preview on Windows

Close Camera, Teams, Zoom, and other apps that may be using the webcam. Verify that
Windows camera privacy settings allow desktop apps to access it, and that any
physical privacy shutter is open. Camera indices can differ between backends.

Try DirectShow explicitly:

```bash
python -m gesture_control --camera 1 --camera-backend dshow --hand any
```

To test camera capture separately from gesture inference:

```bash
python -m gesture_control.camera_probe --camera 1 --camera-backend dshow
```

The probe reads five frames, reports their dimensions and brightness, and saves no
images. It times out after 10 seconds instead of hanging. Try camera 0 or 2, or
`--camera-backend msmf`, if necessary. On Linux/Jetson, `--camera-backend v4l2`
is another option for USB cameras.

The game now displays startup stages (opening camera, waiting for a frame, loading
hand model). It shows the first camera frame before loading MediaPipe and reports
a startup timeout after 30 seconds. `--camera-timeout` changes that limit.

## Calibration and playing

Place the camera **in front of the hand with the palm facing the lens**. Keep the
wrist, thumb, and all fingertips visible. Support the forearm where comfortable.
No wrist rotation or movement across the image is required. Keep the camera fixed
after calibration and use even lighting without strong projector glare or shadows.

1. Press **C**. For each step, read the instruction and press **Enter** when ready.
2. Face your palm toward the camera with fingers **partially relaxed**: this is STOP.
3. Close your fingers into a comfortable fist; do not force a tight grip.
4. Open your fingers comfortably.

There are now **three steps**, each with a one-second preparation period and three
seconds of recording (12 seconds total, plus time between steps). Insufficient tracking
extends a step up to 12 seconds to collect 15 tracked samples. If that still fails,
the step waits for an explicit Enter retry and shows the reason in the central panel.
Final validation identifies the failed pose and preserves all other recordings;
it does not automatically restart all three steps. Press C only to start over.
Calibration is saved locally to `calibration.json` and excluded from Git. Recalibrate
for a different player, camera angle, distance, or setup. Changing `--hand` or
mirroring settings also requires recalibration.
Older calibration profiles are rejected; press C to record the new postures.
Relaxed finger opening must be distinguishable from both fist and open hand.

Click the game window so it has keyboard focus. Tap Enter once per step; do not
hold it. Both the main Enter key and numeric-keypad Enter are supported. The central
calibration panel shows a countdown and the number of tracked samples. If the
countdown runs but samples remain at zero, check the hand selection, camera view,
and frame-age display. The window fits the desktop and can be resized.

In **movement mode**, finger posture and thumb-to-fingertip distances select the
direction. Hand position and orientation in the camera image are ignored.

| Pose | Movement |
| --- | --- |
| Open palm | Up |
| Closed fist | Down |
| Index finger touches thumb, other fingers reasonably open | Left |
| Pinkie touches thumb, other fingers reasonably open | Right |
| Partially relaxed fingers, or ambiguous pose | Stop |
| Both index and pinkie pinches detected | Stop |
| Tracking lost or Space pressed | Stop |

The program checks for a fist before pinch distance: a fist can naturally bring
the thumb close to fingertips. For a left/right pinch, keep at least two other
fingers reasonably open. Ambiguous pinches stop instead of choosing a direction.
Commands select one cardinal direction at a time; there is no diagonal movement.
Closing means **down**, so use partially relaxed fingers or Space to stop. Opening
thresholds are derived from all three recorded postures. Relaxed/unclear poses stop
immediately without a smoothing tail. The player's arrow shows the actual command.
The camera preview connects the thumb to the index/pinkie tips; yellow lines indicate
distance below the pinch threshold. The sidebar displays those normalized distances.
Use `--pinch-threshold` to adjust touch sensitivity (default `0.28`, relative to palm length).
Camera frames older
than 350 ms or a missing hand stop movement immediately at the next rendering frame.
With slow inference, the prototype deliberately stops rather than accepting stale
commands. The sidebar displays inference time and frame age for troubleshooting.

The optional legacy **pinch mode** differs from the new default: touch your thumb to index (left), middle (up), ring (right),
or little finger (down). Release to stop. The nearest qualifying fingertip wins
if multiple touches are detected. Pinch distance is normalized by palm length;
`--pinch-threshold` adjusts sensitivity (default `0.28`). Personal pinch calibration
is not yet implemented. Pinch mode works without the movement calibration; use
movement mode for players unable to perform those touches.

| Key | Action |
| --- | --- |
| C | Start / restart calibration |
| Enter | Begin current calibration recording |
| M | Switch movement / pinch mode |
| Space | Pause / resume |
| R | Return character to center |
| Q / Escape | Exit |

Pause during calibration cancels the current recording. Resume with Space, then
press Enter to record the current step again.

```bash
python -m gesture_control --mode pinch --hand left
python -m gesture_control --fullscreen --no-preview --speed 120
python -m gesture_control --simulate
```

Camera input is **unmirrored by default**. `--mirror` flips it
horizontally; `--no-mirror` explicitly selects the default. Recalibrate after changing
that setting. `--hand any` assumes exactly one
person's hand is in view; select left/right to reduce unwanted input switching.
The simulated demo uses synthetic input and does not validate real tracking.
Fullscreen uses the display selected by SDL/the desktop; configure the projector
as the target display using your desktop settings.

## Game integration

Camera/inference code lives in `gesture_control/tracking.py`; the camera-independent
`Controller` and `Command` live in `gesture_control/controls.py`. The demo illustrates
their use. Enable optional **local-only UDP** output for another game process:

```bash
python -m gesture_control --udp-port 5005
```

Packets sent to `127.0.0.1:5005` are JSON with `vx`, `vy` (normalized x-right,
y-down velocity), `active`, `mode`, `status`, and `timestamp` (local monotonic seconds).
They are sent at up to 30 Hz with a final zero command on orderly shutdown.
The receiver must stop movement if packets stop arriving (suggested timeout 500 ms),
including crashes or power loss. No robot commands are sent by this prototype.

## Verification

### Benchmark CPU versus GPU

Record a short MP4/AVI showing the palm-facing open, fist, index pinch, pinkie
pinch, and relaxed gestures. Include all gestures in the first 10 seconds and keep
the hand visible. Put the video at `recordings/hand-test.mp4` on the Jetson. You can
record it using a camera app; this command does not record or use a live webcam.

From the project root with the environment activated:

```bash
python -m gesture_control.benchmark --video recordings/hand-test.mp4 --label jetson-orin-nano
```

The default compares CPU/GPU over three trials each, using 20 warmup frames and
up to 300 measured frames per trial. Each trial starts a fresh detector and runs
the exact same warmup and measured frames. Run order alternates to reduce order
bias. Video is decoded once before timing, limited to 640x480 while preserving
aspect ratio; recorded timestamps are preserved for tracking. Close the game and
other heavy apps first, keep power/cooling settings fixed, and repeat before
publishing a performance claim.

Outputs (ignored by Git):

- `benchmark-results/summary.csv`: per-trial and pooled aggregate mean/p95 inference
  time, processing FPS, usable-hand detection rate, metadata, and CPU/GPU speedup.
- `benchmark-results/summary-frames.csv`: every measured frame's inference time
  and whether usable hand landmarks were detected.

GPU failures are marked as errors; CPU results are retained, the command exits
with status 1, and no speedup is reported. GPU is never replaced with CPU. A
speedup below 1 means GPU was slower. p95 uses the nearest-rank percentile; the
aggregate pools all measured frames, rather than averaging trial percentiles.

Processing FPS includes image wrapping, synchronous inference, and landmark feature
extraction. It excludes decoding, camera capture, rendering, gesture/game logic,
and model initialization. Inference timing measures the blocking `detect_for_video`
call. Detection rate is the share of frames with valid hand features, **not** gesture
accuracy; a reliable accuracy measure requires manually labeled ground truth.

For a laptop comparison, copy the exact same video and run:

```bash
python -m gesture_control.benchmark --video recordings/hand-test.mp4 --devices cpu --label laptop --output benchmark-results/laptop.csv
```

Match video/model hashes, input resolution, warmup, frame count, MediaPipe version,
and mirroring before comparing aggregate rows. Jetson CPU/GPU speedup alone does
not demonstrate that the Jetson beats the laptop. `--frames`, `--warmup`, `--trials`,
`--mirror`, and `--output` customize the benchmark. No speedup has been measured
on the team's Jetson by this repository's author yet.

### Automated tests

Pure control tests need no camera, MediaPipe, or Pygame:

```bash
python -m unittest discover -s tests -v
```

Optional graphics smoke test without a camera (Linux):

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m gesture_control --simulate --frames 30 --screenshot demo.png
```

On the Jetson, verify camera opening, both hands, calibration, all four movement
directions, relaxing to stop, hand removal, pause, both control modes, and actual
projection. Check responsiveness with the intended lighting and future game workload.

## Exercise interpretation

Opening/relaxing fingers and thumb-to-finger touches are prototype input movements,
not a prescribed rehabilitation program. Select movements appropriate to the player
with rehabilitation expertise. The default controls classify finger posture and
pinch distances, rather than measuring wrist rotation. Opening uses estimated
finger bend angles, and
pinch is a landmark-distance estimate. Neither measures grip strength or establishes
clinical progress. Keep movements comfortable and use pause/rest as needed.

References: [MediaPipe Hand Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python),
[MediaPipe packages and privacy notice](https://pypi.org/project/mediapipe/),
[NHS rehabilitation exercise resource](https://www.worcsacute.nhs.uk/documents/documents/patient-information-leaflets-a-z/2550-self-directed-rehabilitation-and-information-pack/).
