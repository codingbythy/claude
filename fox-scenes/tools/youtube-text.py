#!/usr/bin/env python3
"""Writes a scene's YouTube title, description, tags and pinned comment, ready to paste into YouTube Studio: one file for each
type the scene is made in, at <scene>/youtube/<type>/description.txt (type is lofi or ambience).

Usage: youtube-text.py <scene> [<scene> ...]
The wording comes from the "youtube" block of the scene's scene.json: "story" (the place, shared by both types) and one block
per type. The number of hours comes from "hours", the same value the thumbnail badge and the long-video build use, so the title
can never promise a length the video does not have.
The description opens with one plain sentence saying what the video is (YouTube shows the first line in search results and
under the title), then the story, the sounds and the playlist link.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAYLIST = 'PASTE-YOUR-PLAYLIST-LINK-HERE'
NEED = ('hook', 'lead', 'sounds', 'good_for', 'hashtags', 'tags', 'pinned')
for scene in sys.argv[1:]:
    C = json.load(open(f'{ROOT}/{scene}/scene.json')); Y = C['youtube']; h = C['hours']
    hours = f'{h} Hour' + ('' if h == 1 else 's')
    for kind in ('lofi', 'ambience'):
        T = Y.get(kind)
        if not T:
            continue
        missing = [k for k in NEED if k not in T]
        if missing:
            print(f'{scene} {kind}: skipped, scene.json has no {", ".join(missing)} for it yet'); continue
        title = f'{C["title"]} | {T["hook"]} | {hours}'
        tags = ', '.join(T['tags'] + [hours.lower()])
        if len(title) > 100:
            sys.exit(f'{scene} {kind}: title is {len(title)} characters; YouTube allows 100')
        if len(tags) > 500:
            sys.exit(f'{scene} {kind}: tags are {len(tags)} characters; YouTube allows 500')
        text = '\n'.join([
            'TITLE', title, '',
            'DESCRIPTION', T['lead'].replace('{hours}', hours.lower()), '', *Y['story'], '',
            f'What you will hear, for {hours.lower()}:', *('• ' + s for s in T['sounds']), '',
            T['good_for'], '',
            f'More places to shelter: {PLAYLIST}', '',
            'Somewhere Sheltered. Bad weather. Safe inside.', '',
            ' '.join(T['hashtags']), '',
            'TAGS', tags, '',
            'PINNED COMMENT', T['pinned'], '',
            'THUMBNAIL', f'Three versions are in this folder ({scene}-{kind}-thumbnail-a, -b and -c). Upload all three with "Test & compare" in',
            'YouTube Studio and let it pick the one that holds viewers best; if you only use one, use a.', ''])
        os.makedirs(f'{ROOT}/{scene}/youtube/{kind}', exist_ok=True)
        open(f'{ROOT}/{scene}/youtube/{kind}/description.txt', 'w').write(text)
        print(f'{scene} {kind}: title {len(title)} characters, tags {len(tags)} characters')
