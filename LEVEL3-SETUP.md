# Level 3: T.K.'s Last Stand

Level 3 is the final, entirely virtual boss battle. Lenny must survive 30 seconds. TK locks a red attack cone on Lenny for one second, fires a red laser, then pursues during a two-second recovery. Three hits end the run. The level starts automatically after the Corrupted Grove, or can be opened directly for testing.

From the repository root, serve the game:

```powershell
python -m http.server 8001 --directory game/fight
```

Open `http://localhost:8001/debug.html?level=3` to start the boss immediately. A projector can display this browser page in full screen; the battle does not require AprilTags, the board camera, or mBot motor control.

Use **WASD** to move, **R** to retry, and **3** to restart level 3. Lenny's hand gestures still use the existing Python controller and local WebSocket relay described in [README.md](README.md). If that controller is not running, WASD works as the fallback.

The TK character illustration in `game/fight/assets/tk_boss.png` was generated from the supplied character reference sheet for this game. Gameplay geometry and hit detection are independent of the image.
