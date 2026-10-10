# Forest Motion: Jetson gesture control

A local Python hand-control prototype for the project in [CONTEXT.md](CONTEXT.md).
MediaPipe detects hand landmarks; adjustable control logic moves a character inside
a top-down forest arena. Both hands are supported. Default input uses **top-down hand
tilt for left/right, open hand for up, and closed fist for down**. A partially relaxed
hand at neutral stops movement. A second mode uses thumb-to-finger
touches. Robot tracking and enemy collision are future integration work.

## Jetson setup

Target supplied by the team: Orin Nano, JetPack 7.2.1-b49, Python 3.12.3,
Linux aarch64, glibc 2.39. This repository has not yet been tested on that device.
MediaPipe 1.1.0 has a Linux ARM64 wheel. Inference explicitly uses the CPU;
CUDA acceleration is not assumed. Package installation and camera performance
must be verified on the Jetson.

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

Mount the camera **above the hand, looking straight down at the back of the hand**.
Keep the wrist, knuckles, and fingertips visible, with the forearm supported on the
board/table where comfortable. Rotate the hand within the board plane to point in
different directions. The camera mount must be repositioned physically; software
cannot turn a front-facing camera into an overhead view. Keep the camera fixed after
calibration, and use even lighting without strong projector glare or shadows.

1. Press **C**. For each step, read the instruction and press **Enter** when ready.
2. Point straight ahead with your fingers **partially relaxed**: this is the neutral STOP pose.
3. Close your fingers into a comfortable fist; do not force a tight grip.
4. Open your fingers comfortably.
5. Hold a comfortable left tilt.
6. Hold a comfortable right tilt.

There are now **five steps**, each with a one-second preparation period and three
seconds of recording (20 seconds total, plus time between steps). Insufficient tracking
extends a step up to 12 seconds to collect 15 tracked samples. If that still fails,
the step waits for an explicit Enter retry and shows the reason in the central panel.
Final validation identifies the failed pose and preserves all other recordings;
it does not automatically restart all five steps. Press C only to start over.
Calibration is saved locally to `calibration.json` and excluded from Git. Recalibrate
for a different player, camera angle, distance, or setup. Changing `--hand` or
mirroring settings also requires recalibration.
Older calibration profiles are rejected; press C to record the new postures and tilts.
Neutral finger opening must be distinguishable from both fist and open hand. Each
recorded tilt must be 8–90 degrees from neutral; movement activates at half the
recorded angle and releases at a lower threshold to reduce flicker.

Click the game window so it has keyboard focus. Tap Enter once per step; do not
hold it. Both the main Enter key and numeric-keypad Enter are supported. The central
calibration panel shows a countdown and the number of tracked samples. If the
countdown runs but samples remain at zero, check the hand selection, camera view,
and frame-age display. The window fits the desktop and can be resized.

In **movement mode**, the wrist-to-knuckle vector measures left/right tilt relative
to the recorded neutral heading. Hand position in the camera image is ignored.

| Pose | Movement |
| --- | --- |
| Open hand, neutral angle | Up |
| Closed fist, neutral angle | Down |
| Left tilt, with any finger posture | Left |
| Right tilt, with any finger posture | Right |
| Partially relaxed fingers at neutral angle | Stop |
| Tracking lost or Space pressed | Stop |

Tilt takes priority over opening and closing. Commands select one cardinal
direction at a time; there is no diagonal movement in this mapping. Closing the
hand now means **down**, so use relaxed neutral or Space to stop. Opening thresholds
are derived from all three recorded postures. Circular angle smoothing and
hysteresis reduce jitter. Relaxed neutral stops immediately without a smoothing tail.
The player's arrow shows the actual movement command; the camera preview shows
the wrist-to-knuckle line used to estimate tilt.
Camera frames older
than 350 ms or a missing hand stop movement immediately at the next rendering frame.
With slow inference, the prototype deliberately stops rather than accepting stale
commands. The sidebar displays inference time and frame age for troubleshooting.

In **pinch mode**, touch your thumb to index (left), middle (up), ring (right),
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

Camera input is **unmirrored by default** for the overhead view. `--mirror` flips it
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
with rehabilitation expertise. Steering estimates the hand's direction in the board
plane, rather than measuring a wrist joint angle or forearm palm-up/palm-down rotation.
Moving the forearm can also change the detected direction, so the program cannot
confirm that movement was isolated to the wrist. Opening is an average finger-bend estimate, and
pinch is a landmark-distance estimate. Neither measures grip strength or establishes
clinical progress. Keep movements comfortable and use pause/rest as needed.

References: [MediaPipe Hand Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python),
[MediaPipe packages and privacy notice](https://pypi.org/project/mediapipe/),
[NHS rehabilitation exercise resource](https://www.worcsacute.nhs.uk/documents/documents/patient-information-leaflets-a-z/2550-self-directed-rehabilitation-and-information-pack/).
