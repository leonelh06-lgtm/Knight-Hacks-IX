# Physical rover boss

The Jetson runs two local camera processes: MediaPipe GPU hand control moves the
projected player, and OpenCV AprilTag tracking steers the physical mBot toward it.
The mBot is an autonomous enemy only in the final **Boss Arena**. Earlier levels
need no rover on the table. BLE and existing W/A/D/X motor firmware are retained;
no ESP32 camera or cloud model is used.

**Software is tested with synthetic cameras and fake BLE. Tabletop motion,
motor directions, stopping distance and power draw still require hardware tests.**
The copied example cannot arm motors. BLE mode starts disarmed and requires
g + Enter after valid final-level state and tracking arrive.

## Install on the Jetson

Run from the repository root in every terminal. Keep your working MediaPipe
environment; these dependencies are for the separate overhead tracker.

```bash
source .venv/bin/activate
python -m pip install -r rover/requirements.txt
npm ci --prefix game/fight
```

If pip reports multiple OpenCV packages, check `python -m pip list | grep opencv`.
Use a single OpenCV contrib package providing `cv2.aruco`; do not keep both
opencv-python and opencv-contrib-python in the same environment. An existing
MediaPipe setup may already include contrib. Check the working hand controller
again after changing dependencies.

## Measure and calibrate first

Board: **914.4 x 508 mm** (36 x 20 inches). Origin is its physical top-left,
x to the right, y down. Rover nominal dimensions are 177.8 mm (7 inches), but
measure the actual footprint and tag height rather than copying that number.

Use three different **AprilTag 36h11** markers. ID 0 goes flat and rigid on the
rover; its decoded top edge points toward the rover's forward driving direction.
IDs 1 and 2 are fixed beside diagonally opposite corners, at the same height
as the tabletop calibration plane, and visible throughout operation. Their
locations must span at least 300 mm horizontally and 150 mm vertically.
These references can stay beside the board in earlier levels, leaving the
playing surface clear. The tracker estimates the current camera transform from
both references and checks induced position error over the board at tabletop
and raised tag height. Over 4 mm of induced error invalidates calibration and
exits the process; the allowed 4 mm drift is added to stopping clearance.
Missing any required tag stops driving; recovery requires explicit re-arm.

The overhead camera must see the entire board and all three markers. Use a different
camera from the hand controller. Prefer a persistent Linux device path if camera
numbers change. Leave resolution, focus, zoom and mount fixed after calibration.
If projector alignment or arena placement changes, press I in the browser,
stop the rover, and recalibrate before resuming.

1. Measure the checkerboard's inner-corner counts and square side in mm.
   Collect at least 12 views spanning the image and different tilts. The sample
   command uses a 9 x 6 inner-corner board with **25 mm squares**; replace these
   values with your measured checkerboard.

   ```bash
   python -m rover --camera 1 --calibrate-intrinsics --checkerboard 9 6 --square-mm 25
   ```

   Space records a view, Enter solves after 12 views, Q cancels. RMS must be
   at most 2 pixels. Intrinsics are saved to rover-intrinsics.json.

2. Start the game server and open the game in the Jetson browser. Press 4 to
   display the final map. Arrange the projection. The HUD shows the canvas pixel
   dimensions; record those values. Measure the projected full canvas rectangle
   on the board: x, y, width, height in mm. The browser maps the full canvas to
   that rectangle; measure its edges rather than the forest artwork's outline.
   Keep the projector square to the board (no uncorrected trapezoid).
   The player uses the final post-collision position. Its collision radius uses
   the larger x/y scale, conservatively covering any nonuniform projected scale.

3. Measure tabletop-to-tag height and the rover centre relative to the tag
   centre. Offset is **tag centre to rover centre**, positive forward and right.
   Run the following with your measured values. Shell variables deliberately
   have no defaults so nominal dimensions cannot silently become calibration.

   ```bash
   python -m rover --camera 1 --calibrate-board \
     --tag-height-mm "$TAG_HEIGHT_MM" --centre-offset-mm "$OFFSET_FORWARD_MM" "$OFFSET_RIGHT_MM" \
     --arena-mm "$ARENA_X_MM" "$ARENA_Y_MM" "$ARENA_WIDTH_MM" "$ARENA_HEIGHT_MM" \
     --projection-size "$CANVAS_WIDTH_PX" "$CANVAS_HEIGHT_PX"
   ```

   Click the **physical board** corners in top-left, top-right, bottom-right,
   bottom-left order. This models viewing rays at the measured raised tag
   plane; a tabletop-only homography would misplace a seven-inch-high rover.
   The result is initially unverified.

4. Keep reference IDs 1 and 2 fixed. Place the rover at the centre and at least four
   positions near the usable area's corners. Measure the rover centre's board
   coordinates with a ruler for each position.

   ```bash
   python -m rover --camera 1 --tag-id 0 --validate-calibration
   ```

   Space captures the detected centre and asks for measured x_mm y_mm in the
   terminal. Enter finishes after five locations spanning at least 300 mm
   horizontally and 150 mm vertically. Maximum error must be at most 20 mm.
   Both fixed tag baselines are saved with the validation.

5. Export the matching calibration ID/arena/pixel dimensions to the browser:

   ```bash
   python -m rover --export-game-calibration
   cp rover/config.example.json rover-config.json
   ```

   Reload the page. Measure and edit rover-config.json's footprint, stopping
   distance and extra margin. Set its verified flag true **only after the
   hardware acceptance checks below**. Calibration verification and physical
   motion verification are separate requirements. Config never infers a
   stopping distance or firmware speed from rover size.

## Run the game

Five terminals, all opened in the repository root:

**1 â€” relay**

```bash
node game/fight/relay.mjs
```

Its startup line says relay: udp 5005 -> ws://localhost:8765.
It stays running; it does not print the web server's Serving message.

**2 â€” GPU hand controller (hand camera)**

```bash
source .venv/bin/activate
python -u -m gesture_control --headless --inference-device gpu --camera 0 --udp-port 5005
```

**3 â€” game server**

```bash
python3 -u -m game.serve
```

Open **http://localhost:8000/debug.html** in the Jetson browser. B starts,
1/2/3/4 select levels. Keep one game tab open. A second tab cannot take ownership
of the rover feed. The server explicitly serves .mjs as JavaScript on Windows
and Linux.

**4 â€” rover dry-run (overhead camera)**

```bash
source .venv/bin/activate
python -u -m rover --camera 1 --tag-id 0 \
  --config rover-config.json --calibration rover-calibration.json --dry-run
```

Dry-run never scans or connects BLE, and prints intended W/A/D/X commands.
It prints measured x/y in mm, heading in degrees, source-frame age and VALID/STALE/INVALID status at least once per second, even when disarmed. It obeys the same arming eligibility as real operation. If measurements remain
unverified, it will show tracking status but refuse arming.

**5 â€” optional BLE discovery, when rover process is stopped**

```bash
source .venv/bin/activate
python -m mbot_ble.scan --name Makeblock_LE001b10674482
```

This reads BLE services and does not send motor commands.

For an authorized motion test, stop the dry-run process and run the same rover
command **without --dry-run**. Do not run two rover processes at once.
The existing verified characteristic is
0000ffe3-0000-1000-8000-00805f9b34fb, writes without response.

Place the rover only when entering the final level. B prepares a new encounter.
The game waits for valid tracking, BLE and g + Enter in the rover terminal.
Terminal x + Enter stops/disarms; q + Enter or Ctrl+C shuts down. Input closure
also shuts down. In the browser P pauses/resumes the physical encounter; resume
still needs g + Enter. Switching levels, hiding/closing the tab, terminal
victory/defeat, and changing projection size stop the rover. Resizing permanently
invalidates that page's projection: stop, update calibration, export and reload.

A contact stops/latches motors immediately and sends an event. By default it ends
the level as defeat. Restart with B and explicitly re-arm; acknowledging the
event alone never resumes motion. Remove the rover before returning to earlier
levels.

## Integration points for the game team

Final level id: boss-arena, physicalBoss: true. Other levels publish false.
`?physicalBoss=0` opts into the existing virtual final boss for software-only play.
Physical mode disables the virtual boss's attacks and projected boss circle.

- `window.physicalRoverBoss.finish('victory')` ends the encounter and deactivates
  pursuit. The game team supplies its win condition; none is invented here.
- `window.physicalRoverBoss.setContactPolicy(event => ...)` replaces the contact
  response (for example, damage). The tracker still stops and latches on physical
  contact; a new encounter is required before driving again.
- Default policy 'end_level' applies defeat once. Events carry session_id,
  calibration_id, level_id and event_id; duplicates are acknowledged once per
  effect without applying that effect again.
- Browser publishes authoritative board-space player position at ~20 Hz through
  existing WebSocket 8765. Relay forwards to localhost UDP 8766; rover state/contact
  returns on UDP 8767. Hand gestures retain UDP 5005. Telemetry also includes run_id, a unique rover-process generation; restarting the process pauses the encounter until P and explicit re-arm. Old generations cannot return.
- Python uses its own monotonic receive time, not a browser timestamp.
  Game age above 500 ms or source-frame age above 250 ms stops and disarms.
  Capture/detection runs in a worker; BLE heartbeat is independent at ~100 ms.
  Writes time out at 200 ms, then stop/disconnect. No automatic BLE reconnect.
  Existing firmware's 500 ms watchdog is the final stop if the process/link stalls.

Direct pursuit uses heading hysteresis: turn above 0.30 rad; leave turn below
0.15 rad. A circumscribed footprint limits targets and turning near table edges.
Clearance also includes measured stopping distance, measured calibration error,
the 4 mm camera-guard allowance, and configured margin. Edge-adjacent projected targets may be physically
unreachable; the rover waits inside its safe region.

Existing firmware drives at a fixed speed (150/255 on the rover branch).
W/A/D/X cannot change speed. If this is too fast for the table, leave it disarmed
and make a separate firmware-speed change before measuring stopping distance.

## Hardware acceptance â€” pending

No rows below have been physically verified by this implementation.

| Check | Required record | Status |
|---|---|---|
| Board and projected canvas | Actual dimensions, placement, canvas pixels | Pending |
| Rover and tag | Measured length/width/height, offset, forward tag edge | Pending |
| Overhead camera | Device, resolution, intrinsics RMS, fixed tag baselines | Pending |
| Reference positions | Five measured centres and maximum residual <=20 mm | Pending |
| Wheels raised, controlled hardware test | Confirm W forward, A left, D right, X stop; firmware watchdog <=500 ms | Pending |
| Fixed-speed braking test on suitable surface | Worst observed stopping distance including turn, current draw, power stability | Pending |
| Dry-run on actual board | Direction, scale, contact, unreachable target, edge stop | Pending |
| Authorized tabletop test | Tag occlusion, stale camera/game, manual stop, tab/level exit, re-arm | Pending |
| Full system load | GPU hand + overhead camera + BLE + browser + projector | Pending |
| Final encounter | Place rover, explicit arm, contact, stop, restart, removal | Pending |

Perform direction/watchdog/braking measurements on a suitable surface with
manual motor access before enabling pursuit on the small board. Only after the
results support the configured margins should rover-config.json become verified.
Retain the current firmware; this software does not flash it.
