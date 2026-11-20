#!/usr/bin/env python3
"""Writes a scene's YouTube title and description to <scene>/youtube/description.txt, ready to paste into YouTube Studio.

Usage: youtube-text.py <scene> [<scene> ...]
The wording comes from the "youtube" block of the scene's scene.json; the number of hours comes from "hours", the same value
the thumbnail badge and the long-video build use, so the title can never promise a length the video does not have.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAYLIST = 'PASTE-YOUR-PLAYLIST-LINK-HERE'
for scene in sys.argv[1:]:
    C = json.load(open(f'{ROOT}/{scene}/scene.json')); Y = C['youtube']; h = C['hours']
    hours = f'{h} Hour' + ('' if h == 1 else 's')
    title = f'{C["title"]} | {Y["hook"]} | {hours}'
    if len(title) > 100:
        sys.exit(f'{scene}: title is {len(title)} characters; YouTube allows 100')
    text = '\n'.join([
        'TITLE', title, '',
        'DESCRIPTION', *Y['story'], '',
        f'What you will hear, for {hours.lower()}:', *('• ' + s for s in Y['sounds']), '',
        Y['good_for'], '',
        f'More places to shelter: {PLAYLIST}', '',
        'Somewhere Sheltered. Bad weather. Safe inside.', '',
        ' '.join(Y['hashtags']), ''])
    os.makedirs(f'{ROOT}/{scene}/youtube', exist_ok=True)
    open(f'{ROOT}/{scene}/youtube/description.txt', 'w').write(text)
    print(f'{scene}: {len(title)} characters: {title}')
