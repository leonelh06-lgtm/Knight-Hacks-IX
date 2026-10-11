# Project Context: Mystical Forest Hand Rehabilitation Game

## Purpose

Build a game aimed at helping stroke survivors practice hand motor exercises. Players perform hand movements that a camera-based gesture detection model translates into controls for a playable character. The character must avoid an enemy within a confined map themed as a mystical forest.

This document captures the team's initial concept and constraints. Exercise selection, gesture mappings, and gameplay parameters remain design decisions to validate with appropriate rehabilitation expertise and user feedback. Therapeutic effectiveness has not been established.

## Core Gameplay Concept

- The player controls a character inside a bounded mystical forest arena.
- Lenny and all enemies are rendered in the projected game; the final level is a virtual boss arena.
- Hand exercises serve as the game's input rather than a conventional controller.
- The visual setting should evoke an enchanted forest through trees, foliage, magical lighting, and forest scenery.
- The experience should accommodate different levels of hand movement ability. Exact calibration, difficulty, and accessibility behavior have not yet been defined.

The intended interaction loop is: perform a hand movement, detect the gesture, translate it into a game action, and see the character respond on the projected board.

## Physical Setup

- A projector is attached to a table mount and projects the game onto a board.
- Cameras capture the player's hand movements for gesture detection.
- An NVIDIA Jetson Orin Nano will run the gesture detection model and be configured with JetPack.
- The preferred deployment is to run the complete system, including gesture detection and the game, on the Jetson Orin Nano connected to the projector.
- The preferred power arrangement is a power bank supplying both the Jetson and projector, if feasible.

The projection board is 36 by 20 inches. One hand-facing camera supplies gesture input; projector and power-bank specifications remain to be recorded.

## Proposed System Flow

```text
Hand exercises
      |
      v
Camera capture
      |
      v
Gesture detection on Jetson Orin Nano
      |
      v
Gesture-to-game control mapping
      |
      v
Game: character avoids an enemy in a confined forest map
      |
      v
Projector displays the game on the board
```

The initial gesture prototype uses Python, MediaPipe Hand Landmarker for local inference with selectable CPU or GPU execution, OpenCV camera capture, and a Pygame top-down forest demo. The player faces their palm toward a camera in front of the hand. The primary mapping is: open palm moves up, a comfortable closed fist moves down, index-thumb pinch moves left, and pinkie-thumb pinch moves right. For a pinch, the other fingers should remain reasonably open so it can be distinguished from a fist. Partially relaxed fingers, ambiguous gestures, simultaneous index/pinkie pinches, tracking loss, and manual pause stop movement. Hand position and wrist angle do not control movement. Calibration has three steps: relaxed fingers, comfortable fist, and open hand. Failed calibration retries preserve successful recordings. A separate legacy four-finger pinch mode remains available. These are image-based gameplay features, not clinical measurements. Optional local UDP JSON output allows another game process to consume normalized movement commands. These choices are for the prototype and can change after Jetson performance testing.

The team's reported target environment is JetPack 7.2.1-b49, Python 3.12.3, aarch64, and glibc 2.39. Jetson camera operation and performance have not yet been verified. Setup and usage are documented in `README.md`.

## Team

| Member | Current responsibility |
| --- | --- |
| Leo | Jetson implementation, including the device setup and deployment work |
| Marc | Responsibility to be assigned |
| Ethan | Responsibility to be assigned |
| Diego | Responsibility to be assigned |

## Current Prototype Scope

The current hand-controlled prototype includes:

1. Capture hand movement from a camera connected to the Jetson.
2. Detect a small set of agreed hand gestures or exercise movements.
3. Map those detections to responsive character controls.
4. Render three mystical forest levels: The Hedge Maze, The Corrupted Grove, and Boss Arena.
5. Display the playable game through the projector onto the board.
6. Measure whether the Jetson can run capture, inference, and rendering together at usable performance.
7. Evaluate the proposed portable power setup using the actual devices' requirements.

## Open Design Questions

- Which hand exercises are appropriate for the intended users, and who will validate them?
- Which gestures control movement, and how should limited range of motion be accommodated?
- Will input use one hand or both hands?
- What camera positions provide reliable detection without obstructing the projection or the player's movement?
- What happens when gesture detection is uncertain or loses the hand?
- How will players pause, rest, or stop the session?
- How should enemy speed, movement demands, and session length be adjusted?
- Which game engine and gesture model work with the selected JetPack environment?
- How will Marc, Ethan, and Diego divide gameplay, gesture detection, art, and physical integration work?

## Technical Feasibility Checks

The following are requirements to investigate, not confirmed capabilities of the assembled system:

- Verify compatibility among the exact Jetson hardware, JetPack version, camera drivers, gesture model runtime, and game engine.
- Measure end-to-end latency from hand movement to projected character response.
- Test gesture detection under projector illumination, shadows, and the planned camera angles.
- Confirm the projector's video connection is compatible with the Jetson's output and any required adapter.
- Check the Jetson and projector's required voltages, connectors, power delivery behavior, and combined power draw before selecting a power bank.
- Test sustained operation for thermal behavior, stable power, and practical battery runtime.
- Confirm that the complete application can start and operate locally on the Jetson without another computer.

## Prototype Success Criteria

The initial prototype succeeds when a player can perform the selected hand movements, see the character respond reliably on the projected forest map, and interact with the enemy avoidance challenge. The team should separately record input reliability, response latency, comfort, accessibility feedback, and hardware stability.

Running the entire application on the Jetson and powering both devices from a portable battery are preferred outcomes that remain subject to testing. A working gameplay demonstration does not establish rehabilitation benefit.
