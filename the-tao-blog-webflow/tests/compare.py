#!/usr/bin/env python3
"""Pixel-compare Luke's original site against the Webflow-shaped copy.

  python3 tests/compare.py <orig_base> <copy_base> <out_dir> [page ...]

Reduced motion is emulated so every scroll-reveal element is visible and the
breathing circle holds still. Reports, per page and width: page heights and the
share of pixels that differ (channel delta > 24) in the overlapping area, and
writes orig/copy/diff PNGs so the differences can be LOOKED at.
"""
import os, sys
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

ORIG, COPY, OUT = sys.argv[1].rstrip('/'), sys.argv[2].rstrip('/'), sys.argv[3]
PAGES = {'home': ('index.html', '/'), 'writings': ('writings.html', '/writings/'), 'articles': ('articles.html', '/articles/'),
         'courses': ('courses.html', '/courses/'), 'events': ('events.html', '/events/'), 'about': ('about.html', '/about/'),
         'faq': ('faq.html', '/faq/'), 'contact': ('contact.html', '/contact/')}
only = sys.argv[4:] or list(PAGES)
WIDTHS = [1440, 1280, 900, 600, 390]
os.makedirs(OUT, exist_ok=True)


def shoot(page, url, path):
    page.goto(url, wait_until='load')
    page.evaluate('document.fonts.ready')
    page.wait_for_timeout(500)
    page.screenshot(path=path, full_page=True)


def diff(a, b, out):
    A, B = Image.open(a).convert('RGB'), Image.open(b).convert('RGB')
    h, w = min(A.height, B.height), min(A.width, B.width)
    d = ImageChops.difference(A.crop((0, 0, w, h)), B.crop((0, 0, w, h)))
    mask = d.convert('L').point(lambda v: 255 if v > 24 else 0)
    n = sum(1 for v in mask.getdata() if v)
    mask.save(out)
    first = None
    bbox = mask.getbbox()
    return A.height, B.height, 100.0 * n / (w * h), bbox


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(reduced_motion='reduce')
    pg = ctx.new_page()
    for key in only:
        o, c = PAGES[key]
        for wd in WIDTHS:
            pg.set_viewport_size({'width': wd, 'height': 900})
            fa, fb, fd = (os.path.join(OUT, f'{key}-{wd}-{s}.png') for s in ('orig', 'copy', 'diff'))
            shoot(pg, f'{ORIG}/{o}', fa)
            shoot(pg, f'{COPY}{c}', fb)
            ha, hb, pct, bbox = diff(fa, fb, fd)
            print(f'{key:9} {wd:5}  height orig={ha:5} copy={hb:5} (d={hb-ha:+d})  diff={pct:5.2f}%  first-diff-box={bbox}')
    b.close()
