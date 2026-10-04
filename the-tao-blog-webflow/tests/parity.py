#!/usr/bin/env python3
"""Pixel-compare the local Webflow-shaped copy against the live Webflow build.

  python3 tests/parity.py <local_base> <webflow_base> <out_dir> [page ...]

Same method as compare.py (reduced motion, channel delta > 24), but both sides
use pretty URLs: local serves /about/, Webflow serves /about.
"""
import os, sys
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

LOCAL, WF, OUT = sys.argv[1].rstrip('/'), sys.argv[2].rstrip('/'), sys.argv[3]
PAGES = {'home': ('/', '/'), 'blog': ('/blog/', '/blog'), 'writings': ('/writings/', '/writings'), 'articles': ('/articles/', '/articles'),
         'courses': ('/courses/', '/courses'), 'events': ('/events/', '/events'), 'about': ('/about/', '/about'),
         'faq': ('/faq/', '/faq'), 'contact': ('/contact/', '/contact'),
         'post': ('/writings/taoist-calm-a-systems-level-orientation/', '/writings/taoist-calm-a-systems-level-orientation'),
         'post-nocover': ('/writings/what-is-taoism/', '/writings/what-is-taoism')}
only = sys.argv[4:] or list(PAGES)
WIDTHS = [1440, 1280, 900, 600, 390]
os.makedirs(OUT, exist_ok=True)


SCROLL = '''async () => { for (let y = 0; y < document.body.scrollHeight; y += 500) {
  window.scrollTo(0, y); await new Promise(r => setTimeout(r, 80)); } window.scrollTo(0, 0); }'''
# Webflow lazy-loads every image (a full-page shot alone misses them) and adds the
# free-plan badge; scroll first, and hide the badge so it is not counted as drift.
NO_BADGE = '.w-webflow-badge{display:none!important}'


def shoot(page, url, path):
    page.goto(url, wait_until='load')
    page.evaluate('document.fonts.ready')
    page.evaluate(SCROLL)
    page.add_style_tag(content=NO_BADGE)
    page.wait_for_timeout(800)
    page.screenshot(path=path, full_page=True)


def diff(a, b, out):
    A, B = Image.open(a).convert('RGB'), Image.open(b).convert('RGB')
    h, w = min(A.height, B.height), min(A.width, B.width)
    d = ImageChops.difference(A.crop((0, 0, w, h)), B.crop((0, 0, w, h)))
    mask = d.convert('L').point(lambda v: 255 if v > 24 else 0)
    n = mask.histogram()[255]
    mask.save(out)
    return A.height, B.height, 100.0 * n / (w * h), mask.getbbox()


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(reduced_motion='reduce')
    ctx.add_init_script('Math.random = function () { return 0.42; };')   # the Blog page's random pick, same on both sides
    pg = ctx.new_page()
    for key in only:
        lo, wf = PAGES[key]
        for wd in WIDTHS:
            pg.set_viewport_size({'width': wd, 'height': 900})
            fa, fb, fd = (os.path.join(OUT, f'{key}-{wd}-{s}.png') for s in ('local', 'wf', 'diff'))
            shoot(pg, LOCAL + lo, fa)
            shoot(pg, WF + wf, fb)
            ha, hb, pct, bbox = diff(fa, fb, fd)
            print(f'{key:12} {wd:5}  height local={ha:5} wf={hb:5} (d={hb-ha:+d})  diff={pct:5.2f}%  first-diff-box={bbox}', flush=True)
    b.close()
