# Overhead-camera Rover Boss Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Execution method requires user selection before implementation.

**Goal:** Make the mBot pursue Ethan's projected player in the final open-field level using overhead AprilTag tracking and existing BLE firmware, with configurable contact outcomes.

**Architecture:** The browser publishes authoritative player state through the Node relay. A separate Jetson rover process estimates board-space rover pose and controls BLE pursuit; hand gestures continue through the existing headless MediaPipe GPU controller. Contact events return to the browser, which owns their gameplay consequence.

**Tech Stack:** Python 3.12, OpenCV contrib AprilTag 36h11 detection, NumPy, Bleak, existing mBot BLE firmware, Node.js/ws, browser JavaScript.

**Spec:** `docs/superpowers/specs/2026-10-10-rover-final-boss-design.md`

## Global Constraints

- Physical board: 914.4 by 508 mm; nominal rover: 177.8 by 177.8 by 177.8 mm. Actual footprint, tag height, mounting offset, stopping distance, and calibration error must be measured before arming.
- Coordinates: physical board top-left origin; x right, y down; radians from +x toward +y. Tag height is positive above the tabletop. Projection uses a separately configured board-space arena rectangle.
- Use direct pursuit on an open field; no A*, ESP32 camera, cloud inference, or Hugging Face integration.
- Keep existing BLE W/A/D/X commands and firmware's 500 ms watchdog. Do not upload firmware or arm motors without authorization for that hardware test.
- Initial limits: source-image age 250 ms; game-feed age 500 ms; BLE heartbeat 100 ms; browser/rover messages approximately 20 Hz.
- Earlier levels do not drive the rover. Contact latches motor stop and defaults to ending the final level; outcome belongs to a replaceable game policy.
- MediaPipe GPU and headless control remain compatible. Avoid touching another agent's active work without resolving overlapping files.
- Start execution in a managed worktree based on latest main via the worktree skill. Copy only needed rover modules from origin/autonamous-robot; do not merge its old launcher/history wholesale.

## Review Focus

- Projection resizing or a moved camera must invalidate calibration and prevent motor arming: Tasks 2, 3, 6.
- A second browser tab must not take over an armed rover's target: Task 2.
- Blocking camera detection or BLE writes must not leave a drive command held indefinitely: Tasks 4, 5, 7.
- Repeated or delayed contact events must not repeatedly apply defeat/damage: Tasks 4, 6.
- Nominal tag height and fixed-speed firmware must not be mistaken for measured physical calibration/stopping distance: Tasks 3, 4, 8.

## File responsibilities

- `rover/protocol.py` and `game/fight/rover_protocol.mjs`: versioned wire validation.
- `game/fight/relay.mjs`: existing gesture forwarding plus typed rover routing/session ownership.
- `rover/calibration.py`: intrinsics, board pose, raised-tag correction, persistent calibration ID.
- `rover/vision.py`: separate camera worker and immutable timestamped detections.
- `rover/geometry.py`: physical rectangles, clearance, and contact.
- `rover/pursuit.py`: steering, freshness, arming, stop/contact state machine.
- `rover/ble.py`: command heartbeat, connection, watchdog-compatible stop behavior.
- `rover/__main__.py`: runnable rover process and calibration/arming user interface.
- `game/fight/rover_client.mjs`: browser publishing and telemetry/event reception.
- `game/fight/rover_boss.mjs`: contact-response policy and boss-level adapter.
- Small hooks only in `game/fight/debug.html` and `levels.mjs`.
- `rover/README.md`: setup, measurements, dry-run, and authorized hardware procedure.

## Task 1: Define and test the versioned board-space contract

**Files:** Create `rover/__init__.py`, `rover/protocol.py`, `game/fight/rover_protocol.mjs`, `tests/test_rover_protocol.py`, `game/fight/rover_protocol.test.mjs`, `tests/fixtures/rover_messages.json`.

**Interfaces:** Python `validate_message(data: dict) -> dict`; JS `validateRoverMessage(data) -> object`; invalid inputs raise ValueError/TypeError. Both consume/produce the spec's game_state, rover_state, rover_contact and contact_ack messages. A contact_ack has version, session_id, event_id, calibration_id; an ack never arms motors. Frame-age and all sequence fields are validated.

- [ ] Write matching Python/Node tests using shared fixtures for accepted message types, malformed fields, NaN/Infinity, unknown version, oversized footprint, negative/overflow sequence, invalid arena, and missing session/calibration IDs. Assert browser clock values are never required for receiver freshness.
- [ ] Run `python -m unittest discover -s tests -p test_rover_protocol.py -v` and `node --test game/fight/rover_protocol.test.mjs`; confirm failure before implementation.
- [ ] Implement validators with exact spec field names/units; define contact_ack as above and document it alongside the existing schema.
- [ ] Run both commands; require all fixtures to behave identically. Commit only this task's files as `Define rover game-state protocol`.

## Task 2: Extend the existing relay without breaking gesture input

**Files:** Modify `game/fight/relay.mjs`; create `game/fight/rover_relay.mjs`, `game/fight/rover_relay.test.mjs`.

**Interfaces:** `createRoverRelay({wss, gameStatePort=8766, roverStatePort=8767, now}) -> {handleMessage(ws, data), close()}`. UDP game-state target is localhost:8766; rover telemetry listener is localhost:8767. Browser messages are validated by Task 1. A publisher claim is `{type:'claim_game', version:1, session_id}`; only one live owner exists, and unowned state/acks are rejected. Ownership is tied to the WebSocket and expires on disconnect. Claiming does not arm motors.

- [ ] Write integration tests with real local UDP/WebSocket sockets: gesture forwarding still works; owner's state is routed to 8766; rover state/contact returns to that owner; a second tab's state is rejected; disconnect clears ownership; invalid calibration IDs do not produce drive eligibility.
- [ ] Run `node --test game/fight/rover_relay.test.mjs`; confirm failure.
- [ ] Implement `createRoverRelay` and a small relay hook. Add import-safe startup/close behavior so test ports can be injected; preserve existing environment variables for gesture ports.
- [ ] Run new relay tests and the existing Python-to-gesture-relay smoke test. Verify clean port release. Commit as `Route browser and rover state through relay`.

## Task 3: Calibrate overhead vision for a raised AprilTag

**Files:** Create `rover/calibration.py`, `rover/vision.py`, `tests/test_rover_calibration.py`, `tests/test_rover_vision.py`, `rover/config.example.json`, `rover/requirements.txt`. Reuse detection ideas from branch `mbot_ble/arena.py`, not its uncorrected tabletop projection for the raised tag.

**Interfaces:** `BoardCalibration.load(path: Path) -> BoardCalibration`; `image_to_board(points_px: ndarray, height_mm: float) -> ndarray`; `tag_to_rover(corners_px: ndarray, tag_height_mm: float, centre_offset_mm: tuple[float,float]) -> Pose`. `Pose` contains x_mm, y_mm, heading_rad. `OverheadTracker(camera, tag_id, calibration, backend='auto')` exposes `start()`, `latest() -> PoseSample`, `close()`. `PoseSample` includes pose-or-None, captured_at, valid, error. All deadlines use source capture time.

- [ ] Write synthetic camera-geometry tests: a marker at z=177.8 mm reconstructs its known board position; tabletop-only mapping shows the offset; rotated/mounted-offset tags recover rover centre and heading. Reject singular/invalid calibration, points behind camera, duplicate matching tags, mismatched calibration IDs, and calibration configuration without verified tag height.
- [ ] Write a stalled-detector test proving `latest()` remains readable and the captured timestamp never becomes fresh merely because processing finished. Reject failed reads as invalid samples.
- [ ] Run `python -m unittest discover -s tests -p 'test_rover_calibration.py' -v` and the equivalent vision command; confirm failures.
- [ ] Implement pinhole-camera undistortion, planar board pose estimation, and ray intersection with the measured tag-height plane. Orient the tabletop normal toward the overhead camera; physical height must not silently use the opposite normal from the internal solvePnP coordinate convention. Persist camera/device identity, resolution, intrinsics/distortion, board pose, projection rectangle, measured tag mounting, and calibration ID. Use an OpenCV 36h11 detector in a separate capture/detection worker.
- [ ] Provide an intrinsics-calibration command using measured checkerboard dimensions and a board-corner selection command; reject ambiguous board pose using positive depth/reprojection checks. Require a later measured-reference validation record before arming.
- [ ] Run geometry/vision tests; document the commands and required measured fields in `rover/README.md`. Config examples use null for unverified measurements and `verified:false`, so copying an example cannot arm motors. Commit as `Add calibrated overhead AprilTag tracking`.

## Task 4: Implement pursuit, physical contact, and explicit arming

**Files:** Create `rover/geometry.py`, `rover/pursuit.py`, `tests/test_rover_pursuit.py`.

**Interfaces:** `PursuitController(config)` exposes `update_game(message, received_at)`, `update_pose(sample)`, `arm(now)->bool`, `disarm(reason)`, `ack_contact(event_id)`, and `tick(now)->Decision`. `Decision` contains command (W/A/D/X bytes), armed, status, contact_event-or-None. `footprints_overlap(pose, length_mm, width_mm, player)->bool` uses an oriented rover rectangle and player circle. `edge_clearance_mm(pose, footprint, board_size)->float` checks all rotated corners.

- [ ] Write tests asserting no movement in either earlier level, while inactive, with unverified measurements, or before arming. Test all pursuit heading quadrants and turn hysteresis: enter turns at absolute error above 0.30 rad; leave turns below 0.15 rad. Invalid state gives X.
- [ ] Write tests for game age above 0.5 s, source-image age above 0.25 s, session/calibration changes, and measured edge clearance below configured stop-distance/error margin: each stops and disarms. Recovery alone never re-arms.
- [ ] Write tests for rotated-corner collision, tangent player contact, impossible edge-adjacent targets, and duplicate contact detection. Assert contact emits one event, latches X even before acknowledgement, and only a new explicit encounter reset permits another contact.
- [ ] Run `python -m unittest discover -s tests -p test_rover_pursuit.py -v`; confirm failure.
- [ ] Implement direct pursuit and state machine from the spec. Clamp eligibility to physical safe region rather than blindly pursuing a player near the table edge. No path planner is added.
- [ ] Run tests and commit as `Implement guarded rover pursuit and contact events`.

## Task 5: Reuse BLE transport with an independent heartbeat

**Files:** Copy reviewed `mbot_ble/scan.py` and `mbot_ble/__init__.py` from the rover branch if absent on current main. Create `rover/ble.py`, `tests/test_rover_ble.py`; reference existing motor firmware without flashing/replacing it.

**Interfaces:** `MotorLink(name, decision_source)` exposes async `run(stop_event)` and `request_stop()`. decision_source is `Callable[[], Decision]` from Task 4; update it independently of capture. Production uses Bleak; tests inject a fake client/clock. Use verified FFE3 write characteristic `0000ffe3-0000-1000-8000-00805f9b34fb`, write without response, W/A/D/X bytes, 0.1 s heartbeat.

- [ ] Write fake-transport tests for disarmed X, repeated heartbeat, link loss, cancellation, cleanup X, timed-out writes, and delayed/stalled detection. A recovered connection requires explicit re-arm; never replay the last drive command automatically.
- [ ] Run `python -m unittest discover -s tests -p test_rover_ble.py -v`; confirm failure.
- [ ] Implement Bleak transport with a bounded write timeout of 0.2 s and separate heartbeat task. Track command intent updates locally; stale/failed controller intent gives X. If the link cannot send X, disconnect and rely on the retained firmware watchdog.
- [ ] Run transport/pursuit tests; document that fixed-speed firmware offers no software-controlled speed adjustment. Commit as `Add watchdog-compatible rover BLE transport`.

## Task 6: Add a browser boss adapter with configurable contact policy

**Files:** Create `game/fight/rover_client.mjs`, `game/fight/rover_boss.mjs`, `game/fight/rover_boss.test.mjs`. Modify `game/fight/levels.mjs` and a small adapter hook in `game/fight/debug.html` after checking the other agent's latest changes.

**Interfaces:** `createRoverClient({socket, sessionId, calibration, now}) -> {publishGame(state), acknowledgeContact(event), close()}` reuses the existing relay connection. `createRoverBoss({policy='end_level', onDefeat}) -> {handleContact(event), reset(sessionId), terminal}`. The final level has stable id `boss-arena` and physicalBoss true. Earlier entries have physicalBoss false. `toBoardPlayer(hero, room, arenaRect, radius)` maps the game's authoritative x/z to board x/y in millimetres.

- [ ] Write tests for scaled/aspect-preserving player mapping, shifted projected arena, actual post-collision position, level exit, terminal victory/defeat, pause, lost tab visibility, and projection resize invalidation. Assert active never means merely "gesture moving".
- [ ] Write contact tests: end_level calls onDefeat once; duplicates are acknowledged without repeating gameplay effects; wrong session/calibration is ignored; alternate injected policy handles contact without changes to tracker/transport code.
- [ ] Run `node --test game/fight/rover_boss.test.mjs`; confirm failure.
- [ ] Implement adapters, publish current state at 20 Hz, and return inactive state on pause/exit. Request ownership before publishing. On resize or changed projection configuration, invalidate calibration and require recalibration. Publish a reset/new session when restarting the physical encounter.
- [ ] Hook the final-level renderer/state into the adapter. Disable the virtual-boss attacks for physicalBoss encounters; leave the game team's victory rule intact. Expose a clearly named physical-boss override/configuration so other agent features can extend the encounter.
- [ ] Run all Node tests, verify earlier levels unchanged, and commit as `Connect physical rover boss to projected game`.

## Task 7: Assemble runnable rover process and dry-run integration

**Files:** Create `rover/__main__.py`, `tests/test_rover_integration.py`; update `rover/README.md`, `README.md`, and ignore rules only for generated rover calibration/test artifacts.

**Interfaces:** `python -m rover --camera 1 --tag-id 0 --config rover-config.json --calibration rover-calibration.json --dry-run`. Omit dry-run only for authorized hardware operation. CLI has `--calibrate-intrinsics`, `--calibrate-board`, `--validate-calibration`, and a camera-backend option; each uses Task 3. Existing firmware/gesture controller commands remain unchanged.

- [ ] Write an integration test with fake camera and fake BLE, actual relay sockets, and scripted browser states. Assert final-level ownership/state causes pursuit only after explicit arm, contact stops and reaches the browser, and stale data ends movement while camera work is stalled.
- [ ] Write error-exit tests: missing config, unknown tag, bad calibration, bind failure, BLE failure, interrupted startup, invalid game state, and terminal input closure all remain stopped and close resources. Dry-run cannot instantiate a production BLE client.
- [ ] Run `python -m unittest discover -s tests -p test_rover_integration.py -v`; confirm failure.
- [ ] Implement UDP receiver/sender with independent freshness checking and source timestamps. Provide startup progress, calibration prompts, pose/freshness/motor status, explicit arm/disarm/stop controls, and finite shutdown. Never run blocking OpenCV reads in the asyncio BLE task.
- [ ] Run all Python and Node tests plus real headless gesture-to-relay smoke checks. Add exact Jetson commands for hand camera, overhead camera, relay, web server, and rover process. Commit as `Add local rover boss runtime and dry-run setup`.

## Task 8: Hardware acceptance and handoff

**Files:** Update `rover/README.md` with an acceptance checklist and measured results only when hardware evidence exists. Do not modify the other agent's game features to make a hardware test pass.

- [ ] Record actual board/arena placement, rover length/width, tag height/offset, intrinsics, camera resolution, and calibration residual across the board. Require measured validation before setting verified true.
- [ ] In dry-run with the real overhead camera and browser, display measured rover pose and intended motor command; verify heading, map scale, contact, and table-edge stops. Motors remain unarmed.
- [ ] Ask for authorization for the concrete motor test only after the software/dry-run result is reviewable. Verify existing firmware/motor direction with wheels raised and check its 500 ms watchdog. Do not flash replacement firmware as an incidental step.
- [ ] In an authorized low-speed test, measure stopping distance and current draw, confirm stale-tag/game/manual stops, and enter the measured margins. If fixed firmware speed is too high, keep pursuit disarmed and propose a separate authorized firmware-speed change.
- [ ] Test simultaneous MediaPipe GPU hand control, rover vision, BLE, browser rendering, final-level defeat, level exit, and restart. Report hardware measurements separately from mocked tests.
- [ ] Complete a review against the approved spec. Preserve failures/limitations explicitly; do not claim actual pursuit validated without hardware evidence. Present the implementation branch for integration using the finishing-branch workflow.

## Execution handoff

This plan is proposed for review. Native execution in this session is recommended:
the browser, relay, calibration, and motor interfaces are tightly connected, and
another agent is already developing game features. Maintain one implementation
owner with an independent review at the end. Subagent-driven execution is an
alternative if the user prefers task-by-task independent review.

Before implementation, the user must approve this plan and select an execution
method. Unknown physical measurements are required runtime configuration, not
permission to invent values or enable motors. Software work can proceed using
synthetic geometry and fake transport while those measurements are collected.
