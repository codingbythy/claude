# Scene video tools

Shared by every scene (`cozy-cabin/`, `lighthouse-room/`, ...). Each scene page exposes the same
`window.__render` hook, so one pipeline renders any of them.

1. Serve the scene folder, e.g. `python3 -m http.server 8766` inside `lighthouse-room/`.
2. `node render-scene.js http://localhost:8766/index.html <work-dir> 180 4` renders 3 min + 4 s, frame by frame, with sound.
3. `./make-loop.sh <work-dir>` crossfades it into a seamless loop (`loopv.mp4`, `loop.wav`).
4. `python3 make-music.py <seed> <transpose> music.wav <any.wav>` makes a 12-minute music loop. Same piano and pads for every scene; a new seed and key give each scene its own tune.
5. `node make-title.js title.png "First line" "Accent line" "Subtitle" "#accent"` makes the title card.
6. `./build-kit.sh <work-dir>/loopv.mp4 <work-dir>/loop.wav music.wav title.png ../<scene>/video-kit` writes the kit.

The kit's `build.sh` (copied from `kit-build.sh`) assembles the long video; the Colab notebook in
`video-kit/` runs it in Google's cloud and saves the result to Google Drive.
