#!/usr/bin/env python3
"""Card-size copies (640px wide) of every cover, for the local blog page only.
Webflow makes its own responsive sizes, so these never get uploaded."""
import json, os, concurrent.futures
from PIL import Image, ImageOps, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True  # two WordPress originals are cut short; keep what is there
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = json.load(open(os.path.join(ROOT, 'data/import/writings-all.json')))
def thumb(rel):
    src = os.path.join(ROOT, rel)
    dst = os.path.join(ROOT, rel.replace('assets/wp-import/', 'assets/wp-thumbs/', 1))
    dst = os.path.splitext(dst)[0] + '.jpg'
    if os.path.exists(dst):
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im).convert('RGB')
            im.thumbnail((640, 1400), Image.LANCZOS)
            im.save(dst, 'JPEG', quality=78, optimize=True, progressive=True)
    except Exception as e:
        print('fail', rel, e)
covers = {r['images_local'][r['cover']] for r in R if r['cover'] and r['cover'] in r['images_local']}
with concurrent.futures.ThreadPoolExecutor(6) as ex:
    list(ex.map(thumb, sorted(covers)))
print('thumbs', len(covers))
