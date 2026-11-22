#!/usr/bin/env python3
"""Writes a scene's YouTube title, description, tags and pinned comment to <scene>/youtube/description.txt, ready to paste
into YouTube Studio.

Usage: youtube-text.py <scene> [<scene> ...]
The wording comes from the "youtube" block of the scene's scene.json; the number of hours comes from "hours", the same value
the thumbnail badge and the long-video build use, so the title can never promise a length the video does not have.
The description opens with one plain sentence saying what the video is (YouTube shows the first line in search results and
under the title), then the story, the sounds and the playlist link.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAYLIST = 'PASTE-YOUR-PLAYLIST-LINK-HERE'
for scene in sys.argv[1:]:
    C = json.load(open(f'{ROOT}/{scene}/scene.json')); Y = C['youtube']; h = C['hours']
    hours = f'{h} Hour' + ('' if h == 1 else 's')
    title = f'{C["title"]} | {Y["hook"]} | {hours}'
    tags = ', '.join(Y['tags'] + [hours.lower()])
    if len(title) > 100:
        sys.exit(f'{scene}: title is {len(title)} characters; YouTube allows 100')
    if len(tags) > 500:
        sys.exit(f'{scene}: tags are {len(tags)} characters; YouTube allows 500')
    text = '\n'.join([
        'TITLE', title, '',
        'DESCRIPTION', Y['lead'].replace('{hours}', hours.lower()), '', *Y['story'], '',
        f'What you will hear, for {hours.lower()}:', *('• ' + s for s in Y['sounds']), '',
        Y['good_for'], '',
        f'More places to shelter: {PLAYLIST}', '',
        'Somewhere Sheltered. Bad weather. Safe inside.', '',
        ' '.join(Y['hashtags']), '',
        'TAGS', tags, '',
        'PINNED COMMENT', Y['pinned'], '',
        'THUMBNAIL', f'Three versions are in this folder ({scene}-thumbnail-a, -b and -c). Upload all three with "Test & compare" in', 'YouTube Studio and let it pick the one that holds viewers best; if you only use one, use a.', ''])
    os.makedirs(f'{ROOT}/{scene}/youtube', exist_ok=True)
    open(f'{ROOT}/{scene}/youtube/description.txt', 'w').write(text)
    print(f'{scene}: title {len(title)} characters, tags {len(tags)} characters')
