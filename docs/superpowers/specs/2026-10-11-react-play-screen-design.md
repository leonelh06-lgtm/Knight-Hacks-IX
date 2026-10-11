# The Guiding Hands — player guide

## Intent and approved direction
Create an aesthetically appealing React and JavaScript companion display for the existing gesture-controlled game. Its purpose is to reduce confusion while players play and keep the character movement gestures easy to remember. Players see the live game, four persistent illustrated gesture reminders, and a small live camera window with the hand-tracking overlay. The UI does not control the game. The chosen default style is enchanted forest: deep greens, warm cream typography, restrained gold accents, subtle glow, and generous spacing.

## Player experience
- Desktop: a compact branded header; a large game panel on the left; a right sidebar with the live tracking preview and four gesture cards. Smaller screens stack the game, preview, and guide without horizontal scrolling.
- Use “The Guiding Hands” as the title and “Your hands lead the way” as supporting copy. Use the existing dragon asset sparingly as a visual accent.
- Show the existing live game in an embedded panel. The companion UI has no start, pause, reset, focus, fullscreen, calibration, or other game-control buttons, and sends no commands or keyboard events to the game or tracker. The existing game and controller remain responsible for gameplay. Keep all four gesture reminders visible throughout play rather than requiring a tutorial or navigation.
- Illustrations must visibly distinguish open palm, closed fist, index-thumb pinch, and pinky-thumb pinch. Use carefully drawn SVG hands with highlighted touch points and directional arrows, plus accessible descriptions. Each must be reviewed visually for correct anatomy and pose.
- Forward/up: open palm toward camera. Down: closed fist with wrist pointing down. Left: index touching thumb, remaining fingers extended. Right: pinky touching thumb, remaining fingers extended. Include a short note that a relaxed hand stops movement.
- The wrist-down pose is guidance, not a new recognition requirement. Preserve the existing controller's fist-based down detection.
- The preview displays actual camera frames with landmark points and skeleton connections, alongside tracking state and detected movement. Highlight the matching gesture card only when tracking data is fresh and the command is active.
- Display honest states for waiting for camera, loading model, calibrating, tracking, hand missing, paused, disconnected, and simulation. A missing preview must not affect gameplay. Never substitute fake camera footage or report a disconnected system as live.

## React integration
- Add a self-contained frontend directory using React, JavaScript, Vite, and CSS. Bundle dependencies for offline use after installation; no CDN dependency at runtime.
- Keep the game renderer in its existing page, embedded in an iframe for display. Do not rewrite simulation or gesture recognition. No control bridge or postMessage command interface is added. Tracking metadata is read only and solely supports the preview and guide highlights.
- Production build emits to a dedicated `game/fight/play/` directory. Ignore generated builds in Git and document the build step.
- Extend the existing Python game server so `/` opens the built React screen when available, retaining `/debug.html` for the original standalone game. If no build exists, serve a clear build instruction page at `/`.
- In development, Vite proxies the original game's required files and tracking endpoints so the iframe and preview use the same browser origin. Production serves built assets and proxies preview requests through the existing game server.
- Do not integrate the previously uploaded sounds in this change; the request here concerns the play interface.

## Camera-preview integration
- The existing Python tracker remains the sole camera owner. Its snapshots already contain RGB frames and normalized landmark coordinates.
- Add an opt-in `--web-preview-port` argument to headless mode; default off to preserve current launches. Document port 8766 for the React setup. Bind the preview service to loopback.
- Provide `GET /stream.mjpg` for a small annotated MJPEG stream and `GET /status` for tracking metadata. The game server exposes these as `/tracking/stream.mjpg` and `/tracking/status` using the configured preview port.
- Status fields: phase, command status, direction (`up`, `down`, `left`, `right`, or `stop`), active, handDetected, frameAgeMs, inferenceMs, simulated, paused, calibrating, and error. Derive command status from the actual session output, not hand appearance alone.
- Render frames at up to 10 FPS and at most 320 pixels wide, preserving aspect ratio. Encode in the preview worker only when viewers are connected; hold only the latest frame and do not queue historical images. Recognition and UDP movement must not wait for HTTP viewers or JPEG encoding.
- Annotate the snapshot that produced the image so landmarks align with its frame. Preserve the tracker’s mirror setting consistently for image and landmarks.
- Poll status at a modest rate; discard old state on connection failure or stale capture. Stop highlighting movement when the frame exceeds the controller’s configured stale timeout.
- Use bounded network timeouts, no-cache responses, and clean shutdown. If a requested preview port is occupied, report the error clearly while allowing gesture control to continue.
- No browser webcam capture, additional detector, recording, or remote streaming is introduced.

## Validation and acceptance
- React production build succeeds and assets resolve both through Vite and the Python production server.
- Verify desktop and narrow-screen layouts, readable contrast, accessible frame/image names, reduced-motion support, persistent gesture-card visibility, and the absence of game-control UI.
- Use fixtures for preview/status tests: annotated frames, fresh and stale landmarks, calibration, pause, simulation, unavailable service, reconnect, and shutdown. Verify down/left/right/up card highlights correspond to actual command output.
- Test preview service routes, content types, frame throttling, client disconnects, optional startup, and server proxy failures without hardware.
- Run the existing Python controller tests and JavaScript game tests to check that the UI and optional preview preserve gameplay.
- Inspect rendered screenshots and the four gesture illustrations. Test the real camera and GPU on the Jetson when available; otherwise explicitly report that hardware validation remains outstanding. Confirm the companion sends no gameplay or calibration commands and does not capture player key events to control the game.

## Delivery
Implement and validate locally after design review. Present the running UI and a concise result summary. Publishing these new changes to GitHub requires the user to request that step; the earlier upload authorization concerned the audio assets.
