#!/usr/bin/env python3
"""Turn fragments into WHTML builder actions.

  python3 wf_payload.py <parent_component> <parent_element> <position> <fragment> [<fragment> ...]

Emits a JSON list of actions (max 5). CSS for a class is included only the
FIRST time the class is used (tracked in created-classes.json; a run writes
created-classes.pending.json, and `wf_payload.py --commit` promotes it only
after the payload was actually sent), so Webflow
never sees a class twice and never mints a "-1" duplicate. Border shorthands
are expanded to longhands (a var() inside a shorthand silently kills the
payload) and local asset URLs are swapped for Webflow CDN URLs.
"""
import json, os, re, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
CDN = json.load(open(os.path.join(ROOT, 'asset-cdn.json')))
TRACK = os.path.join(ROOT, 'created-classes.json')
created = set(json.load(open(TRACK))) if os.path.exists(TRACK) else set()

css = re.sub(r'/\*.*?\*/', '', open(os.path.join(ROOT, 'tao.css')).read(), flags=re.S)
base, media = {}, {}
def rules(text):
    return re.findall(r'\.([a-z0-9-]+)\s*\{([^{}]*)\}', text)
body = re.sub(r'@media[^{]+\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}', '', css)
for c, d in rules(body):
    base[c] = d.strip()
for m in re.finditer(r'@media screen and \(max-width: (\d+)px\)\s*\{((?:[^{}]*\{[^{}]*\})*)[^{}]*\}', css):
    for c, d in rules(m.group(2)):
        media.setdefault(m.group(1), {})[c] = d.strip()

def norm(decl):
    out = []
    for part in [p.strip() for p in decl.split(';') if p.strip()]:
        k, v = part.split(':', 1); k = k.strip(); v = v.strip()
        mm = re.fullmatch(r'border-(top|bottom|left|right)', k)
        if mm and v not in ('none', '0'):
            w, s, col = v.split(' ', 2)
            side = mm.group(1)
            out += [f'border-{side}-width:{w}', f'border-{side}-style:{s}', f'border-{side}-color:{col}']
            continue
        for local, url in CDN.items():
            v = v.replace(f'url("{local}")', f'url("{url}")')
        out.append(f'{k}:{v}')
    return '; '.join(out) + ';'

def css_for(classes):
    parts = [f'.{c} {{ {norm(base[c])} }}' for c in classes if c in base]
    for bp in ('991', '767', '479'):
        mq = [f'.{c} {{ {norm(media[bp][c])} }}' for c in classes if c in media.get(bp, {})]
        if mq:
            parts.append(f'@media screen and (max-width: {bp}px) {{ ' + ' '.join(mq) + ' }')
    return '\n'.join(parts)

if sys.argv[1] == '--commit':
    pend = os.path.join(ROOT, 'created-classes.pending.json')
    os.replace(pend, TRACK); print('committed'); sys.exit(0)
pc, pe, pos = sys.argv[1:4]
actions = []
for frag in sys.argv[4:]:
    html = open(frag).read().strip()
    used = []
    for cl in re.findall(r'class="([^"]*)"', html):
        for c in cl.split():
            if c.startswith('w-') or c == 'w--current' or c in used:
                continue
            used.append(c)
    missing = [c for c in used if c not in base]
    if missing:
        sys.exit(f'undefined classes in {frag}: {missing}')
    new = [c for c in used if c not in created]
    created.update(new)
    a = {'build_label': os.path.basename(frag), 'parent_element_id': {'component': pc, 'element': pe},
         'creation_position': pos, 'html': html}
    c = css_for(new)
    if c:
        a['css'] = c
    actions.append(a)
json.dump(sorted(created), open(os.path.join(ROOT, 'created-classes.pending.json'), 'w'))
print(json.dumps(actions, ensure_ascii=False))
