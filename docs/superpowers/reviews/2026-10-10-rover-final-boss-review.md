# Rover boss review and acceptance record

Current scope update (2026-10-11): the user has only one AprilTag and requested
removal of stationary tags before the deadline. The fixed-reference camera guard
is removed from vision, loader and calibration. Camera/projector stability is
now an operator responsibility; stop and recalibrate after either moves.
Single-tag verification: 70 Python tests and 23 Node tests passed; a focused
independent review found no Critical or Important issues. The review below records
the earlier three-tag design, not current requirements.

Reviewed range: 4a14d63..33d0d67, by an independent fresh-context reviewer.
The reviewer required three functional fixes; this branch implements all three.

- Camera guard: replace local pixel displacement with two spatially separated
  fixed references and current camera pose estimation. Check induced error over
  the board at tabletop and raised tag height; reject over 4 mm and add the
  allowed drift to stopping clearance. Camera roll and depth-change regressions pass.
- Runtime restart: add run_id generations, reject retired generations, reset
  telemetry sequencing, pause the browser and require explicit recovery.
  A 12000 -> 0 -> 1 sequence across generations is covered.
- Setup diagnostics: show pose, heading, source-image age, validity, intent and
  arm status at least once per second, including unverified/disarmed mode.

Verification after the fix pass: **72 Python tests and 12 Node tests passed**.
This includes real WebSocket/UDP integration with synthetic vision/injected fake
BLE, a real headless gesture-to-relay smoke test, and 500 maze physics simulations.
The actual browser displayed both the earlier maze and final calibration-wait map.
The reviewer could not finish its own suites; these totals are the executor's
fresh complete runs, not an inferred reviewer approval.

Deferred minor: Python protocol validation still accepts boolean true for version
1 and raises AttributeError for certain malformed nested objects. JS rejects
these messages; the Python runtime catches malformed nested inputs and disarms.
Strict validator parity should be tightened later. This does not enable motors
from malformed nested state.

## Decisions recorded during implementation

1. Shared immutable Pose/PoseSample live in rover/types.py; calibration commands
   are dispatched from the runtime. Cost if wrong: adjust imports/CLI plumbing.
2. Turning and target reach use a circumscribed footprint. Cost: conservative
   edge reach, intentionally leaving some projected targets unreachable.
3. BLE faults terminate instead of reconnecting automatically. Cost: restart
   the process and explicitly re-arm after a fault.
4. Expose window.physicalRoverBoss.finish for the game team to supply victory;
   physicalBoss=0 preserves the virtual final boss for software-only play.
   Cost: the physical encounter needs the team's win condition.
5. An initial single fixed camera tag was replaced after review by two tags
   beside opposite board corners, because one small local reference can miss
   rotation causing a large error elsewhere. Cost: two fixed references at
   tabletop height, visible throughout play, plus a 4 mm clearance allowance.
6. Add python -m game.serve for consistent JavaScript MIME types on Windows.
   Cost: use the new server command.
7. Real camera accuracy, motor directions, stopping distance, current draw and
   concurrent Jetson performance remain pending. Cost: hardware acceptance is
   required before claiming tabletop pursuit works.
8. Projector movement uses manual I invalidation and recalibration; resizing
   automatically invalidates. Cost: the operator must invalidate when moving
   the projector because no projector-pose sensor was specified.

See rover/README.md for the commands and the pending hardware acceptance table.
