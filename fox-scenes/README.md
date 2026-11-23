# Fox scenes (prototypes)

The next episodes: two foxes asleep somewhere sheltered, with the weather outside a window. Nothing here touches the three
live videos or their folders.

| Folder | Title | Made as | Kit |
|---|---|---|---|
| `toymaker/` | Christmas Snowfall at the Toymaker's Workshop | lo-fi (home) and ambience | yes |
| `stationmaster/` | Blizzard at the Stationmaster's Waiting Room | ambience (home) and lo-fi | yes |
| `shepherd/` | Winter Wind at the Shepherd's Hut | ambience | not yet |
| `observatory/` | Starry Night at the Stargazer's Observatory | lo-fi; settings only (the style-reference painting) | not yet |

Two types of video, both with the foxes:

- **lo-fi**: music composed for the whole length, with the scene's own sounds a set distance underneath it.
- **ambience**: the scene's own sounds only. No music.

A scene's picture and weather loop are the same for both; only the mix differs. Each scene has a home type, the one that suits
it best. On thumbnails lo-fi carries a warm badge reading LO-FI and ambience a cold one reading NO MUSIC.

## Where the paintings come from

Paintings are made outside this repository, in ChatGPT (Sora) or with Google's tools (Veo), with
`channel/style-reference/two-foxes-observatory.webp` attached so the foxes and the style stay the same. Each scene keeps the
prompt that made its painting in `painting-prompt.txt`. Do not use ElevenLabs for image generation.

## How a scene is put together

Every scene uses the same page, `scene.html?s=<folder>`. Everything specific to a scene is in its `scene.json`:

- `image`: the picture the scene page shows (`room.webp`). It is made from `painting-1280.png`, the painting as it arrived, by
  `tools/grade.py <folder>` using the `grade` settings: the room is relit (a warm pool of light over the foxes and around the
  fire and lamps, foreground furniture and clutter let fall into shadow, the window kept cold and clear), lamps and flames are
  given a soft glow, and the picture is snapped to a true pixel grid (640×360) with a limited palette.
- `glass` and `mask`: where the window glass is, so weather is only drawn there (`tools/make-mask.py <folder>` rebuilds the mask).
- `weather`, `stars`, `twinkles`, `glows`, `flames`, `sparks`, `steam`: what moves.
- `breathe`: where each fox is, so it rises and falls as it sleeps.
- `rig`: the foxes' heads and ears as separate pieces (outline, the point each turns about, and a soft joint at the neck or
  ear base). `tools/rig.py <folder>` cuts them out of the picture into `<folder>/rig/` and fills in the fur behind them. Run it
  again whenever the picture is regraded.
- `sound`: the wind, fire, clock and other sounds, all generated (nothing recorded or licensed).
- `mix`: the loudness target, the scene's home type, and the settings for each type it is made in (`lofi`: the music and how far
  under it the scene's sounds sit; `ambience`: nothing to set).
- `hours`: the video length. The thumbnail badge, the title and the build all read this number, so they cannot disagree.
- `thumbnail`: the two lines of the scene name, the closer framing, and which moment of the loop each type's thumbnail shows.
- `youtube`: the wording for titles and descriptions: the story of the place, then a block per type.

### What moves, and when

- **The foxes.** They sleep. Their bodies rise and fall as they breathe, and now and then an ear flicks: twice in the first
  second of the loop, so there is life on screen straight away, then every 10 to 40 seconds. Nothing else about them moves.
- **The weather.** Each three-minute loop starts with heavy snow, eases to a calm stretch in the middle and picks up again.
  The wind sound gets louder and higher exactly when the snow gets heavier, and the snow ticking on the glass follows too.
- **The fire.** It flares up and dies back. When it flares it crackles more, glows brighter and throws more sparks, and each
  loud pop in the sound throws a burst of sparks in the picture.

All of this repeats every 180 seconds, so the loop comes round without a jump. The timings live in `scene.html`
(`storm`, `fireLife` and `FLICKS`).

## Making a preview

```bash
cd fox-scenes && python3 -m http.server 8791 --bind 127.0.0.1
```

```bash
python3 fox-scenes/tools/preview.py toymaker 60 --type lofi
```

This renders 60 seconds of picture and sound into `fox-scenes/work/toymaker/` and prints a sound report. Preview clips are
not kept in the repository; the same command always rebuilds the same clip. Each scene is held to
three rules, and the report says pass or fail for each:

1. Full level from the first second: no fade-in, no silence, no title card.
2. Loudness on target (-14 LUFS, the level YouTube plays at) with peaks at or under -1 dBFS.
3. Still clearly there on a phone speaker: no more than 7 dB lost through a small-speaker filter.

Thumbnails: `node tools/still.js "http://127.0.0.1:8791/scene.html?s=toymaker" frame 36,97 --size 1920x1080`, then
`node tools/thumb.js toymaker lofi frame-97.png toymaker/youtube/lofi` (and the same with `ambience` and `frame-36.png`).
Each call writes three versions for YouTube's "Test & compare" (the whole scene with its name, closer with its name, closer
with no name), each at 1280×720 with a 320×180 copy for judging it at feed size. They are a little brighter and richer than
the video, on purpose. `python3 tools/youtube-text.py toymaker` writes `youtube/<type>/description.txt` for each type: title,
description, tags and pinned comment.

## Making the loop and the two-hour video

```bash
node fox-scenes/tools/render.js "http://127.0.0.1:8791/scene.html?s=toymaker" fox-scenes/work/toymaker/loop 184 --size 640x360
```

```bash
python3 fox-scenes/tools/make-loop.py fox-scenes/work/toymaker/loop
```

```bash
python3 fox-scenes/tools/make-kit.py toymaker
```

The first command renders the loop at the scene's own size, every pixel exact (about 8 minutes); the second blends the
loop's end into its start; the third writes `toymaker/video-kit/` (about 70 MB). The kit's `build.py` then makes the upload:

1. It enlarges the loop four times over to 2560×1440 with hard pixel edges, so it stays perfectly sharp, and encodes it once
   (H.264 High, 30 fps, BT.709, tagged). YouTube gives uploads above 1080p a higher-quality stream, and each of its smaller
   sizes (1080p, 720p) is a whole number of screen pixels per scene pixel.
2. It mixes the sound to -14 LUFS with peaks at -1 dBFS, 48 kHz stereo AAC at 384 kbps, full level from the first frame.
3. It joins the loop for as many hours as `hours` says, then 20 seconds fading out, without re-encoding.

`build.py --type lofi` or `--type ambience` chooses the type; with neither, it makes the scene's home type.

`make-video.ipynb` does the same in Google Colab (set `SCENE` and `TYPE`) and saves the result to Google Drive; it downloads the kit from this branch,
so the branch name is written in it. A two-hour file is about 3 to 4.5 GB. `python3 tools/check-video.py <file>` checks a built
video: the opening, every place the loop comes round, and the loudness.

Kits exist for `toymaker` and `stationmaster`. `shepherd` and `observatory` have scene settings only.
