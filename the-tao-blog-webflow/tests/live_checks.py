#!/usr/bin/env python3
"""Behaviour checks against a running build (local or Webflow staging).

  python3 tests/live_checks.py <base> [--submit-form]

Mobile menu, FAQ (mouse + keyboard), hover states, horizontal overflow at every
width, every internal link + PDF resolves, axe accessibility scan, JS errors.
--submit-form sends ONE clearly-labelled test message through the contact form.
"""
import sys, urllib.request, urllib.parse
from playwright.sync_api import sync_playwright

BASE = sys.argv[1].rstrip('/')
SUBMIT = '--submit-form' in sys.argv
PAGES = ['/', '/writings', '/articles', '/courses', '/events', '/about', '/faq', '/contact',
         '/writings/taoist-calm-a-systems-level-orientation', '/writings/what-is-taoism']
WIDTHS = [1440, 1280, 900, 600, 390]
AXE = 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js'
fails, notes = [], []


def check(ok, msg):
    (notes if ok else fails).append(('PASS ' if ok else 'FAIL ') + msg)


def url(path):
    # local serves /about/, Webflow serves /about
    return BASE + (path if path == '/' or 'localhost' not in BASE else path + '/')


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context()
    pg = ctx.new_page()
    errors = []
    pg.on('pageerror', lambda e: errors.append(f'{pg.url}: {e}'))

    # 1. horizontal overflow, every page x width
    for path in PAGES:
        for w in WIDTHS:
            pg.set_viewport_size({'width': w, 'height': 900})
            pg.goto(url(path), wait_until='load')
            sw = pg.evaluate('document.documentElement.scrollWidth')
            if sw > w:
                check(False, f'overflow {path} @{w}: scrollWidth {sw}')
    check(not any(f.startswith('FAIL overflow') for f in fails), 'no horizontal overflow on 10 pages x 5 widths')

    # 2. mobile menu
    pg.set_viewport_size({'width': 390, 'height': 800})
    pg.goto(url('/'), wait_until='load')
    burger = pg.locator('.burger')
    check(burger.is_visible(), 'burger visible at 390')
    burger.click(); pg.wait_for_timeout(700)
    top = pg.evaluate("document.querySelector('.mobile-menu').getBoundingClientRect().top")
    check(pg.evaluate("document.querySelector('.mobile-menu').classList.contains('open')") and top >= 0,
          f'burger opens menu (menu top={top:.0f})')
    check(burger.get_attribute('aria-expanded') == 'true', 'burger aria-expanded=true when open')
    pg.locator('.mobile-menu a', has_text='About').first.click(); pg.wait_for_load_state('load')
    check('/about' in pg.url, f'menu link navigates ({pg.url})')
    pg.goto(url('/'), wait_until='load')
    pg.locator('.burger').focus(); pg.keyboard.press('Enter'); pg.wait_for_timeout(600)
    check(pg.evaluate("document.querySelector('.mobile-menu').classList.contains('open')"), 'burger opens with keyboard (Enter)')

    # 3. FAQ
    pg.set_viewport_size({'width': 1280, 'height': 900})
    pg.goto(url('/faq'), wait_until='load')
    q = pg.locator('.qa-q').first
    h0 = pg.evaluate("document.querySelector('.qa-a').getBoundingClientRect().height")
    q.click(); pg.wait_for_timeout(700)
    h1 = pg.evaluate("document.querySelector('.qa-a').getBoundingClientRect().height")
    check(h0 < 2 and h1 > 20, f'FAQ answer collapsed then opens on click ({h0:.0f}px -> {h1:.0f}px)')
    check(q.get_attribute('aria-expanded') == 'true', 'FAQ aria-expanded=true when open')
    q2 = pg.locator('.qa-q').nth(1); q2.focus(); pg.keyboard.press('Enter'); pg.wait_for_timeout(700)
    h2 = pg.evaluate("document.querySelectorAll('.qa-a')[1].getBoundingClientRect().height")
    check(h2 > 20, f'FAQ opens with keyboard ({h2:.0f}px)')

    # 4. hover states change something visible
    pg.goto(url('/'), wait_until='load')
    for sel in ['.btn-primary', '.btn-outline', '.nav-link', '.post', '.feature']:
        el = pg.locator(sel).first
        if not el.count():
            continue
        el.scroll_into_view_if_needed()
        props = "e => { const s=getComputedStyle(e); return [s.backgroundColor,s.color,s.transform,s.boxShadow,s.borderColor,s.translate,s.paddingLeft].join('|') }"
        pg.mouse.move(0, 0); pg.wait_for_timeout(500)
        before = el.evaluate(props)
        el.hover(); pg.wait_for_timeout(700)
        after = el.evaluate(props)
        check(before != after, f'hover changes {sel}')

    # 5. links: every internal href + PDF on every page resolves
    seen = {}
    for path in PAGES:
        pg.goto(url(path), wait_until='load')
        for h in pg.eval_on_selector_all('a[href]', 'els => els.map(e => e.href)'):
            u = urllib.parse.urlsplit(h)
            if u.scheme not in ('http', 'https') or (u.netloc != urllib.parse.urlsplit(BASE).netloc and 'website-files.com' not in u.netloc):
                continue
            key = h.split('#')[0]
            if key in seen:
                continue
            try:
                seen[key] = urllib.request.urlopen(urllib.request.Request(key, method='GET'), timeout=20).status
            except Exception as e:
                seen[key] = str(e)
    bad = {k: v for k, v in seen.items() if v != 200}
    check(not bad, f'{len(seen)} unique internal links + files resolve' + (f' -- broken: {bad}' if bad else ''))
    dead = []
    for path in PAGES:
        pg.goto(url(path), wait_until='load')
        dead += [f'{path}: {t}' for t in pg.eval_on_selector_all('a', "els => els.filter(e => !e.getAttribute('href') || e.getAttribute('href') === '#').map(e => e.className)")]
    check(not dead, 'no "#" or empty links' + (f' -- {dead[:6]}' if dead else ''))

    # 6. axe
    worst = {}
    for path in PAGES:
        pg.goto(url(path), wait_until='load')
        pg.add_script_tag(url=AXE)
        res = pg.evaluate("async () => (await axe.run(document, {runOnly: ['wcag2a','wcag2aa','wcag21aa']})).violations.map(v => [v.id, v.impact, v.nodes.length])")
        for vid, imp, n in res:
            worst.setdefault(vid, [imp, 0, []]); worst[vid][1] += n; worst[vid][2].append(path)
    check(not worst, 'axe WCAG 2.1 AA: no violations' if not worst else
          'axe violations: ' + '; '.join(f'{k} ({v[0]}, {v[1]} nodes on {sorted(set(v[2]))})' for k, v in worst.items()))

    # 7. form (opt-in: sends a real submission)
    if SUBMIT:
        pg.goto(url('/contact'), wait_until='load')
        pg.fill('#name', 'Lena QA test')
        pg.fill('#email', 'qa-test@example.com')
        pg.select_option('#topic', index=1)
        pg.fill('#message', 'Staging check from Lena (Hands-On Analytics). Safe to delete.')
        pg.locator('input[type=submit], button[type=submit]').first.click()
        pg.wait_for_selector('.w-form-done', state='visible', timeout=15000)
        check(pg.locator('.w-form-done').is_visible(), 'contact form submits and shows the success message')

    check(not errors, 'no JS errors' + (f' -- {errors}' if errors else ''))
    b.close()

print('\n'.join(notes + fails))
print(f'\n{len(notes)} pass, {len(fails)} fail')
sys.exit(1 if fails else 0)
