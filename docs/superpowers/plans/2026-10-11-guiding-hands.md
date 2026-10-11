# The Guiding Hands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for native execution, or superpowers:subagent-driven-development if the user selects delegated execution. Track steps with the checkboxes below.

**Goal:** Build an attractive React companion that keeps gesture instructions, the live game, and a small annotated tracking preview visible during play.

**Architecture:** React embeds the existing game without a control bridge. An optional Python preview service reads the existing tracker snapshots and session commands; the game server proxies its image and status endpoints. Vite provides development routing and bundles offline-ready production assets.

**Tech Stack:** React, JavaScript, Vite, CSS, Python standard-library HTTP/threading, existing OpenCV, existing unittest and Node tests, Vitest/React Testing Library for the UI.

**Spec:** `docs/superpowers/specs/2026-10-11-react-play-screen-design.md`

## Global Constraints
- Title: “The Guiding Hands”; supporting copy: “Your hands lead the way”. Knight Hacks IX black/purple/white colors and four persistent, accessible SVG hand illustrations.
- No start, pause, reset, focus, fullscreen, or calibration controls; no gameplay messages or injected keyboard events.
- Existing tracker owns the camera. Preview is optional, local, at most 320 pixels wide and 10 FPS, with no disk recording or fake footage.
- Preserve the standalone game, recognition rules, UDP output, and current launches without preview enabled.
- Build locally and present results; do not push this feature unless requested.

## Review Focus
- Stale, paused, or calibrating tracker state clears gesture highlights.
- Preview shutdown or an occupied port leaves the movement controller usable.
- Slow/disconnecting image viewers do not stall inference or UDP movement.
- Missing build or preview service yields an honest actionable state.
- Narrow screens retain all gesture instructions without horizontal overflow.

### Task 1: Optional tracker preview service
**Files:** Create `gesture_control/web_preview.py` and `tests/test_web_preview.py`; modify `gesture_control/headless.py`, `gesture_control/__main__.py`, and `tests/test_headless.py`.
**Interfaces:** `PreviewServer(host='127.0.0.1', port=8766)` exposes `start()`, `update(snapshot, command, *, paused, calibrating, simulated, stale_after)`, and `close()`. `update` only publishes references/metadata under a short lock; image encoding happens in HTTP worker threads.
- [ ] Add failing unittest cases for status and MJPEG routes, valid port parsing, old launch behavior, paused/calibrating/stale input, simulation without a camera image, occupied port, and clean shutdown. Verify a slow viewer does not block publishing snapshots or movement packets.
- [ ] Run `python3 -m unittest tests.test_web_preview tests.test_headless -v`; confirm the new cases fail for missing functionality.
- [ ] Add optional `--web-preview-port` (default None, valid 1–65535, headless only). Start once, update from each headless tick, close in finally. Report startup failure and keep controls running.
- [ ] Implement `/status` JSON: phase, status, direction, active, handDetected, frameAgeMs, staleAfterMs, inferenceMs, simulated, paused, calibrating, error. Unknown ages are null. Inactive/stale/paused/calibrating commands produce direction `stop`; simulated state is explicitly labeled. Compute frame age when serving the request.
- [ ] Implement `/stream.mjpg` using current RGB snapshots, normalized landmark points and hand skeleton connections; preserve orientation and aspect ratio. Encode JPEG lazily with OpenCV, reuse the latest encoded frame across clients, enforce 10 FPS, skip unchanged timestamps, and send multipart JPEG boundaries. No frame queue; missing frames wait with bounded shutdown checks; disconnect closes the worker.
- [ ] Run the Task 1 tests and full `python3 -m unittest discover -s tests -v`; verify existing movement behavior, then commit the isolated preview change.

### Task 2: Same-origin game and preview serving
**Files:** Modify `game/serve.py`; create `tests/test_game_server.py`.
**Interfaces:** `game_handler(preview_port=8766)` serves existing fight files, the React build, and `/tracking/status` plus `/tracking/stream.mjpg`. `--preview-port` selects the loopback upstream; original `--port` remains supported.
- [ ] Add failing integration tests using temporary HTTP servers: root redirects to `/play/` with a build, root returns build instructions without one, `/debug.html` still serves, JS MIME types remain correct, status/stream content types are forwarded, unavailable upstream returns 503, and disconnected downstream closes upstream.
- [ ] Run `python3 -m unittest tests.test_game_server -v`; verify new behavior fails before implementation.
- [ ] Implement exact-route loopback proxies using urllib with bounded connect/read timeouts, no-cache headers, streamed chunks, and cleanup on disconnect. Do not allow arbitrary proxy destinations. Serve a short “Build The Guiding Hands” page when the React build is absent.
- [ ] Run Task 2 tests plus the full Python suite, then commit the serving changes.

### Task 3: React player guide and illustrations
**Files:** Create `frontend/package.json`, lockfile, Vite config, `index.html`, and focused source modules: `src/App.jsx`, `src/GestureGuide.jsx`, `src/TrackingPreview.jsx`, `src/tracking.js`, `src/styles.css`, `src/main.jsx`, and UI tests. Modify `.gitignore` for frontend dependencies and `game/fight/play/`.
**Interfaces:** `useTrackingStatus()` polls `/tracking/status` sequentially within the freshness budget (one third of staleAfterMs, bounded to 25–150 ms), cancels requests on unmount, returns status and connection state, and clears old state on failure. `activeDirection(status)` returns a direction only for fresh, active, nonsimulated tracking outside pause/calibration. `GestureGuide({activeDirection})` and `TrackingPreview({status, connectionState})` read data only.
- [ ] Scaffold React/Vite with reproducible npm scripts: dev, build, and test. Configure production base `/play/` and build output `game/fight/play/`. Vite proxies `/debug.html` and its root-relative game dependencies (`*.mjs`, `*.js`, `intro.css`, assets, maps) to port 8000, and `/tracking/` through the game server. Preserve the iframe's relative module/image paths.
- [ ] Write failing UI tests: exact title and gesture descriptions, four always-visible cards, no game-control buttons, iframe `/debug.html`, real MJPEG source only when available, reconnect/abort behavior, stale or paused state clears highlighting, simulation label, and no commands sent to game/tracker. Run `npm test --prefix frontend` to establish failures.
- [ ] Implement the display and hook. Stream image source is `/tracking/stream.mjpg`; an error marks the preview unavailable and bounded retries follow status recovery. Use no webcam access, game event handlers, or control messages.
- [ ] Draw four separate SVG hands, with palm/fist outlines and unambiguous index/pinky thumb contact; add touch-point accents, directional arrows, readable text, and accessible image descriptions. Include relaxed-hand stop guidance. Wrist orientation remains instructional only.
- [ ] Style desktop as a large game panel plus a guide sidebar; place the small 4:3 camera panel above the cards. Use black backgrounds, white text, vivid purple/lavender accents, locally drawn crystal motifs and low-motion ambient details. Stack at narrow widths; keep all reminders visible and give the game panel useful height. Use local/system typography with no runtime external fetches.
- [ ] Run UI tests and `npm run build --prefix frontend`; verify offline bundled assets and commit frontend sources.

### Task 4: Integrated verification and player setup
**Files:** Update `README.md`; save review screenshots under the chat outputs directory.
- [ ] Document install/build (`npm ci --prefix frontend`, `npm run build --prefix frontend`), existing relay startup, headless tracker with `--web-preview-port 8766`, and `python3 -m game.serve`. Explain frontend development and preview failures without presenting developer setup inside the normal player interface.
- [ ] Run full Python tests, UI tests/build, and every existing `game/fight/*.test.mjs` test with Node's test runner. Fix only regressions related to this feature.
- [ ] Launch the built app through the Python server. Use browser inspection to verify all iframe modules/assets load; check desktop 1440×900 and narrow 390×844 layouts, guide visibility, focus accessibility, contrast, reduced motion, simulation/offline states, and absence of game controls. Capture screenshots.
- [ ] Inspect each gesture illustration for accurate finger contacts and distinct poses. Verify preview with controlled test fixtures; run actual Jetson camera/GPU validation only if that hardware is available, otherwise report it as outstanding.
- [ ] Verify clean source diff and no recorded camera files, commit final documentation/fixes, and present the local UI and verification summary without pushing.
