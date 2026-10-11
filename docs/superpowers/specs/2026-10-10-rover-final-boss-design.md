# Overhead-camera rover boss

Status: proposed design for user review; implementation is not started.

## Agreed intent and scope

Use the physical mBot as the enemy in the final level of Ethan's projected web
game. Earlier levels remain independent of rover control. The final level is an
open field: no maze planning or obstacle detection is required. The rover pursues
the projected player using overhead AprilTag tracking on the Jetson.

Keep the existing mBot BLE connection and motor firmware. Remove the ESP32 camera
from this runtime path. Keep the existing MediaPipe GPU headless hand controller.
All game, vision, relay, and pursuit processing runs locally on the Jetson.

Board dimensions are 36 by 20 inches (914.4 by 508 mm). The rover is approximately
7 by 7 by 7 inches (177.8 mm per dimension). These are initial configuration
values; measure the actual footprint and tag mounting height before motor arming.

For the first version, confirmed rover/player overlap ends the final level in
defeat and stops pursuit. This rule is provisional: other features are being
developed by another agent. Collision reporting and the game response must remain
separate so the response can later become damage, invulnerability, or another rule.
This design does not specify how the player wins the final level; preserve the
game team's selected victory rule and stop the rover on any terminal game state.

## Current repository evidence

The reviewed main branch includes Ethan's levels, the UDP-to-WebSocket relay, and
the headless MediaPipe GPU gesture controller. The final level is currently the
third entry, Boss Arena, in game/fight/levels.mjs. The implementation should use a
level property such as physicalBoss rather than assuming the third array index.

The reviewed origin/autonamous-robot branch contains reusable modules:

- mbot_ble/arena.py: AprilTag 36h11 tracking and four-corner homography calibration.
- mbot_ble/autonomy.py: direct pursuit steering toward a target.
- mbot_ble/autopilot.py: overhead capture, BLE updates, manual arming, and stops.
- mbot_ble/motor_firmware/: W/A/S/D/X commands and a 500 ms command watchdog.

That branch takes player coordinates from the old Python demo and predates the
headless web-game integration. Bring reusable rover modules into a branch based
on current main; do not restore its older gesture_control launcher or discarded
Hugging Face integration. Its ESP32-CAM files are not needed for this design.

## Components and ownership boundaries

1. The browser owns the authoritative player position, level, arena geometry,
   pause/terminal state, and collision-response policy. Send the position after
   movement and collision constraints have been applied. Never integrate gesture
   velocity separately to guess where the player is.
2. The Node relay forwards typed browser game-state messages to the Python rover
   process and typed rover messages back to browsers. Existing gesture forwarding
   remains compatible.
3. The overhead vision worker owns camera acquisition, AprilTag detection,
   coordinate calibration, rover heading, frame age, and detection validity.
4. The pursuit controller owns the requested motor command. It consumes fresh
   player and rover state and remains independent of browser rendering.
5. The BLE transport owns connection, motor heartbeat, stop-on-disconnect, and
   explicit arming. Retain the existing firmware watchdog.
6. A collision function compares measured rover/player footprints and emits a
   contact event. It does not directly change health or advance levels.

Keep these boundaries explicit because the game team is developing other features
concurrently. Agree on the messages below before either side edits the relay or
game loop. Do not overwrite unrelated work or require another agent to replace
their features with this design. Coordinate changes to shared files separately.

## Shared coordinates and projection calibration

Use millimetres in a board coordinate system: origin at the physical board's
top-left, x right, y down, heading in radians measured from +x toward +y.

914.4 by 508 mm describes the physical board, not necessarily the entire projected
image. Measure the usable projected arena and its placement on the board. Express
the arena as a board-space rectangle; the game's screen HUD and window borders
are not part of the playable region.

The browser maps its current world/maze coordinates into normalized arena u/v,
then into the configured board-space rectangle. Its geometry and renderer must
use the same conversion, including orientation and aspect ratio. Calibration is
invalidated if projector alignment, browser scale/fullscreen layout, camera pose,
arena placement, or board dimensions change. Use a calibration ID in messages
and block arming when the game and tracker disagree.

Mount the overhead webcam rigidly so the complete physical board and tag remain
visible. Use a different camera from hand tracking; configure each device
explicitly so camera indices are not assumed stable.

A tabletop homography alone is insufficient for an approximately 177.8 mm high
marker. The design requires camera intrinsics/distortion calibration and a board
pose estimated from known board points. Undistort marker points and intersect
their viewing rays with the measured tag-height plane. Obtain planar tag position
and heading, then apply the measured horizontal tag-to-rover-centre offset. This
avoids interpreting the raised marker as if it were on the table surface.

The marker should be flat, rigid, centred when possible, and oriented with its
top edge toward the rover's front. Use a known AprilTag 36h11 ID. Configure the
measured tag height and mounting offset; do not arm using the nominal rover height
without verifying the actual mounting. Validate position at the centre and near
all corners of the usable arena with measured reference locations. The test must
also cover projector light, shadows, rover rotation, and motion blur.

## Proposed versioned messages

All coordinate values below use board millimetres. Node/Python/browser clocks
are not assumed interchangeable: receivers age data with their own monotonic
clock. Sequence numbers reject out-of-order messages; new sessions reset sequence
tracking and disarm. Source freshness must also be checked before publication.

Browser to relay to rover, approximately 20 updates per second:

```json
{
  "type": "game_state", "version": 1, "session_id": "example-session",
  "seq": 1, "calibration_id": "example-calibration", "level_id": "boss-arena",
  "physical_boss": true, "active": true, "terminal": false,
  "player": {"x_mm": 400, "y_mm": 220, "radius_mm": 12},
  "arena": {"x_mm": 0, "y_mm": 0, "width_mm": 914.4, "height_mm": 508}
}
```

Player radius in this example is illustrative; derive the configured footprint
from the game's rendered/collision scale. active means this level is started,
unpaused, and nonterminal, not that a hand gesture is currently moving the player.

Rover to relay to browser, approximately 20 updates per second when available:

```json
{
  "type": "rover_state", "version": 1, "session_id": "example-session",
  "seq": 1, "calibration_id": "example-calibration", "valid": true, "armed": false,
  "pose": {"x_mm": 300, "y_mm": 220, "heading_rad": 0},
  "footprint": {"length_mm": 177.8, "width_mm": 177.8},
  "frame_age_ms": 40, "status": "disarmed"
}
```

Invalid/lost pose updates set valid false and never masquerade as a new measured
position. Contact events carry type rover_contact, version, session_id, level_id,
calibration_id, and a unique event_id. The game handles each event once. The
initial response is a configurable collision policy named end_level. Alternative
responses can be added without changing tracking, pursuit, or the BLE protocol.

Use an explicitly identified game-state publisher for each armed session. Other
connected browser tabs must not be able to overwrite the active target feed.
Validate message types, ranges, finite numbers, required fields, and freshness.
No motor command is accepted directly from an arbitrary browser message.

## Pursuit and contact behavior

No A* is needed: calculate the angle from measured rover position to the player's
current position. Turn toward that heading, drive forward once aligned, and stop
within the footprint-based contact region. Apply a heading deadband and distinct
turn-entry/turn-exit thresholds to reduce left/right chatter. Use the existing
discrete W/A/D/X command transport first; variable wheel-speed steering would
require a separately agreed firmware/protocol change.

Existing firmware has fixed motor speed. Start hardware checks with a reduced
firmware speed configured for this small board. Do not claim the Python controller
can smoothly slow the motors unless the firmware is updated to support that.
Determine physical stopping distance from measured tests at the selected speed.

Use an oriented rover rectangle and the player's board-space footprint for
collision. Detect contact using fresh valid state, stop the rover immediately,
and emit one event. Contact is latched until the game acknowledges it or the
session is explicitly reset. This prevents repeated motor drive or duplicate
defeat events if the acknowledgement is delayed. The browser remains responsible
for displaying defeat and selecting its configurable outcome policy.

The rover replaces or disables conflicting virtual-boss attacks in the physical
boss level unless the game team explicitly chooses a combined encounter.

## Operational stops and boundaries

Pursuit starts disarmed. Manual arming is possible only with a valid calibration,
fresh tracked pose, fresh active final-level state, BLE connection, and the rover
inside the permitted physical region. Entering the final level does not itself
arm motors. Leaving it, ending it, changing session, or losing the motor connection
disarms; resuming after tracking/feed loss requires an explicit re-arm.

Initial limits: overhead source-image age at most 250 ms, game feed age at most
500 ms, and BLE command heartbeat every 100 ms. These values are configurable and
must be checked against measured capture/inference/network latency. A separate
freshness/heartbeat task must keep issuing stops even if capture or detection
blocks; do not run blocking camera work in the BLE heartbeat loop. If Python or
BLE updates cease entirely, the existing 500 ms firmware watchdog stops motors.

Maintain a physical board-edge guard even though the virtual player is bounded.
Clearance includes the rover's oriented footprint, measured stopping distance,
calibration error, and a margin. Stop and disarm when clearance is insufficient;
do not attempt to steer inward while continuing toward an out-of-range target.
The playable player area should keep valid pursuit/contact targets reachable
within this permitted region. Physical board boundaries and projected arena
boundaries are distinct configuration values.

Manual stop overrides all inputs. Motor arming occurs only during an explicitly
authorized hardware test; software integration tests use a fake motor transport.

## Validation and acceptance

- The first two levels never issue drive commands. The final level only drives
  after explicit arming and receipt of valid fresh state.
- Browser coordinates correspond to the projected sprite after movement/collision
  handling; resizing/reprojection invalidates calibration rather than shifting
  targets silently.
- Measured raised-tag position matches reference points across the board; quantify
  error and use it in collision/edge margins.
- Geometry tests cover pursuit headings, threshold jitter, footprint contact,
  edge clearance, invalid numbers, and unreachable targets.
- Integration tests cover browser state through the relay, rover telemetry back
  to the browser, session ownership, event deduplication, and end-level response.
- Tag disappearance, camera stall, stale game state, paused/terminal game,
  disconnect, and manual stop all issue stop commands and require explicit re-arm.
- Test motor direction and watchdog with wheels raised before low-speed pursuit
  on the board. Measure stopping distance before enabling edge-adjacent movement.
- Keep the existing hand-control and game tests passing; verify concurrent hand
  GPU tracking and overhead tracking without introducing unacceptable latency.
- Actual camera, projection, BLE, current draw, and motor performance are hardware
  checks; a passing mocked test does not establish them.

## Next handoff

Review and approve this written spec before writing an implementation plan.
Before implementation, confirm measured tag height/offset, usable projected arena
placement, and the game agent's current final-level interface. The configurable
collision response is intentionally provisional; all default behavior above is
specified so the initial implementation can be evaluated concretely.

## Implementation verification notes
Updated 2026-10-11 at the user's request: only one AprilTag on the rover is
required. Fixed reference tags and automatic camera-motion detection are removed
because additional tags cannot be printed before the deadline. Camera/projector
mounts must remain fixed after calibration; movement requires manual stop,
browser I invalidation, and fresh board calibration/validation. Tag-loss,
freshness, table-edge and explicit-arming checks remain.
Rover telemetry carries run_id to separate process generations. A process restart
pauses the browser encounter and requires explicit recovery/arming. Dry-run prints
pose, heading, capture age and valid/stale status even when disarmed.
Hardware acceptance remains pending until actual measurements and motor tests.
