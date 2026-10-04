#!/usr/bin/env python3
"""tao-behavior.css -> behavior-embed.html (the <style> block inside the Site Header's Code Embed).
Comments and blank lines go; everything else is kept as written. Fails if a var() slipped in:
Webflow renames its variables, so the embed must use literal values."""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
css = open(os.path.join(ROOT, 'tao-behavior.css')).read()
css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
lines = [l.strip() for l in css.split('\n') if l.strip()]
out = '<style>\n' + '\n'.join(lines) + '\n</style>'
if 'var(--' in out:
    sys.exit('var() in the embed: ' + ', '.join(sorted(set(re.findall(r'var\(--[a-z0-9-]+\)', out)))))
open(os.path.join(ROOT, 'behavior-embed.html'), 'w').write(out)
print(len(out), 'chars')
