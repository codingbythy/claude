# Fox scenes (prototypes)

The next episodes: two foxes asleep somewhere sheltered, with the weather outside a window. Nothing here touches the three
live videos or their folders.

| Folder | Title | Sound |
|---|---|---|
| `toymaker/` | Christmas Snowfall at the Toymaker's Workshop | lo-fi music over a hearth fire and soft snow |
| `stationmaster/` | Blizzard at the Stationmaster's Waiting Room | ambient: blizzard wind, stove, clock. No music |
| `shepherd/` | Winter Wind at the Shepherd's Hut | ambient: moor wind and a wood stove. No music |
| `observatory/` | Starry Night at the Stargazer's Observatory | settings only, not yet previewed (the style-reference painting) |

## How a scene is put together

Every scene uses the same page, `scene.html?s=<folder>`. Everything specific to a scene is in its `scene.json`:

- `image`: the painting (`room.webp`, 1920×1080). `painting-1280.png` is the generated original.
- `glass` and `mask`: where the window glass is, so weather is only drawn there (`tools/make-mask.py <folder>` rebuilds the mask).
- `weather`, `stars`, `twinkles`, `glows`, `flames`, `sparks`, `steam`: what moves.
- `breathe`: where each fox is, so it rises and falls as it sleeps.
- `sound`: the wind, fire, clock and other sounds, all generated (nothing recorded or licensed).
- `mix`: `ambient` (weather only) or `lofi` (music on top, weather a set distance underneath), and the loudness target.
- `hours`: the video length. The thumbnail badge is made from this number, so the two cannot disagree.
- `thumbnail`: the two lines of the scene name and the accent colour.

## Making a preview

```bash
cd fox-scenes && python3 -m http.server 8791 --bind 127.0.0.1
```

```bash
python3 fox-scenes/tools/preview.py toymaker 60
```

This renders 60 seconds of picture and sound into `fox-scenes/work/toymaker/` and prints a sound report. Each scene is held to
three rules, and the report says pass or fail for each:

1. Full level from the first second: no fade-in, no silence, no title card.
2. Loudness on target (-16 LUFS) with peaks under -1 dBFS.
3. Still clearly there on a phone speaker: no more than 7 dB lost through a small-speaker filter.

Thumbnails: `node tools/still.js "http://127.0.0.1:8791/scene.html?s=toymaker" frame.jpg 12`, then
`node tools/thumb.js toymaker frame.jpg <out-dir>` writes the 1280×720 thumbnail and a 320×180 copy for judging it at feed size.

## Not built yet

The two-hour build (seamless 3-minute picture loop, a longer weather cycle, the Colab notebook) comes after the prototypes are
approved. The older scenes' loop and kit scripts in `/tools` expect mono sound; these scenes are stereo, so that step needs a small
update rather than a new pipeline.
