# Fox scenes (prototypes)

The next episodes: two foxes asleep somewhere sheltered, with the weather outside a window. Nothing here touches the three
live videos or their folders.

| Folder | Title | Sound |
|---|---|---|
| `toymaker/` | Christmas Snowfall at the Toymaker's Workshop | lo-fi music over a hearth fire and soft snow |
| `stationmaster/` | Blizzard at the Stationmaster's Waiting Room | ambient: blizzard wind, stove, clock. No music |
| `shepherd/` | Winter Wind at the Shepherd's Hut | ambient: moor wind and a wood stove. No music |
| `observatory/` | Starry Night at the Stargazer's Observatory | settings only, not yet previewed (the style-reference painting) |

## Where the paintings come from

Paintings are made outside this repository, in ChatGPT (Sora) or with Google's tools (Veo), with
`channel/style-reference/two-foxes-observatory.webp` attached so the foxes and the style stay the same. Each scene keeps the
prompt that made its painting in `painting-prompt.txt`. Do not use ElevenLabs for image generation.

## How a scene is put together

Every scene uses the same page, `scene.html?s=<folder>`. Everything specific to a scene is in its `scene.json`:

- `image`: the picture the scene page shows (`room.webp`). It is made from `painting-1280.png`, the painting as it arrived, by
  `tools/grade.py <folder>` using the `grade` settings (colour grade; for the toymaker also a true pixel grid and a limited palette).
- `glass` and `mask`: where the window glass is, so weather is only drawn there (`tools/make-mask.py <folder>` rebuilds the mask).
- `weather`, `stars`, `twinkles`, `glows`, `flames`, `sparks`, `steam`: what moves.
- `breathe`: where each fox is, so it rises and falls as it sleeps.
- `rig`: the foxes' heads and ears as separate pieces (outline, the point each turns about, and a soft joint at the neck or
  ear base). `tools/rig.py <folder>` cuts them out of the picture into `<folder>/rig/` and fills in the fur behind them.
- `cuddle`: where the bodies and the tail give a little when the foxes move.
- `sound`: the wind, fire, clock and other sounds, all generated (nothing recorded or licensed).
- `mix`: `ambient` (weather only) or `lofi` (music on top, weather a set distance underneath), and the loudness target.
- `hours`: the video length. The thumbnail badge, the title and the build all read this number, so they cannot disagree.
- `thumbnail`: the two lines of the scene name and the accent colour.

### What moves, and when

- **The foxes.** In the opening seconds the right-hand fox has its head up; it comes down and pushes in under the other's
  chin, the left-hand fox is nudged up and settles back on top, ears flick, the tail curls in, and both let out a long breath.
  After that they sleep: they breathe, an ear flicks now and then, once in each three-minute loop they nuzzle closer and sigh.
- **The weather.** Each three-minute loop starts with heavy snow, eases to a calm stretch in the middle and picks up again.
  The wind sound gets louder and higher exactly when the snow gets heavier, and the snow ticking on the glass follows too.
- **The fire.** It flares up and dies back. When it flares it crackles more, glows brighter and throws more sparks, and each
  loud pop in the sound throws a burst of sparks in the picture.

All of this repeats every 180 seconds, so the loop comes round without a jump. The timings live in `scene.html`
(`storm`, `fireLife` and `poseAt`).

## Making a preview

```bash
cd fox-scenes && python3 -m http.server 8791 --bind 127.0.0.1
```

```bash
python3 fox-scenes/tools/preview.py toymaker 60
```

This renders 60 seconds of picture and sound into `fox-scenes/work/toymaker/` and prints a sound report. Preview clips are
not kept in the repository; the same command always rebuilds the same clip. Each scene is held to
three rules, and the report says pass or fail for each:

1. Full level from the first second: no fade-in, no silence, no title card.
2. Loudness on target (-16 LUFS) with peaks under -1 dBFS.
3. Still clearly there on a phone speaker: no more than 7 dB lost through a small-speaker filter.

Thumbnails: `node tools/still.js "http://127.0.0.1:8791/scene.html?s=toymaker" frame.jpg 12`, then
`node tools/thumb.js toymaker frame.jpg <out-dir>` writes the 1280×720 thumbnail and a 320×180 copy for judging it at feed size.

## Making the loop and the two-hour video

```bash
node fox-scenes/tools/render.js "http://127.0.0.1:8791/scene.html?s=toymaker" fox-scenes/work/toymaker/loop 184
```

```bash
node fox-scenes/tools/render.js "http://127.0.0.1:8791/scene.html?s=toymaker&open=14" fox-scenes/work/toymaker/open 10
```

```bash
python3 fox-scenes/tools/make-loop.py fox-scenes/work/toymaker/loop
```

```bash
python3 fox-scenes/tools/make-kit.py toymaker
```

The first command renders the loop (about 25 minutes), the second the opening seconds with the foxes nestling in, the third
blends the loop's end into its start, and the fourth writes `toymaker/video-kit/`. The kit's `build.py` assembles the long
video: the opening, then the loop for as many hours as `hours` says, then a 20-second fade. `make-video.ipynb` does the same in
Google Colab and saves the result to Google Drive; it downloads the kit from this branch, so the branch name is written in it.

Kits exist for `toymaker` and `stationmaster`. `shepherd` and `observatory` have scene settings only.
