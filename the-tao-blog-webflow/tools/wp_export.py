#!/usr/bin/env python3
"""Export every WordPress post on thetaoblog.com into one CMS-ready file.

  python3 tools/wp_export.py [--refetch] [--no-images]

Reads the raw REST dump in data/wordpress/ (fetched with --refetch), cleans each
post body down to what Webflow Rich Text holds, downloads every image so the
import never depends on WordPress being online, and writes:

  data/import/writings-all.json   one record per post (the import file)
  data/import/redirects.csv       old WordPress path -> new Webflow path
  data/import/report.md           counts, duplicates, and everything flagged

Nothing here talks to Webflow. tools/import_writings.py does the import.
"""
import argparse, collections, concurrent.futures, csv, glob, hashlib, html, io, json, os, re, subprocess, sys, unicodedata
from urllib.parse import unquote, urlparse, parse_qs

import lxml.html
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'data/wordpress')
OUT = os.path.join(ROOT, 'data/import')
IMG = os.path.join(ROOT, 'assets/wp-import')
API = 'http://thetaoblog.com/wp-json/wp/v2/posts?per_page=100&page={}&_embed=wp:featuredmedia,wp:term&orderby=date&order=desc'

ESSAY_WORDS = 300          # posts at or over this many words are "Essay", shorter ones "Reflection"
EXCERPT_CHARS = 180
RENAME = {'h1': 'h2', 'b': 'strong', 'i': 'em'}
BLOCK = {'p', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'ul', 'ol'}
SIZE_SUFFIX = re.compile(r'-\d+x\d+(?=\.(?:jpe?g|png|gif|webp)$)', re.I)
IMAGE_EXT = re.compile(r'\.(jpe?g|png|gif|webp)$', re.I)


# Topics: WordPress has none (every post is "Uncategorized"), so they are derived from the text.
# A topic counts when its words appear twice in the text or once in the title; at most 3 per post.
TOPICS = {
    'Breath': r'\bbreath\w*|\binhal\w*|\bexhal\w*',
    'Meditation': r'\bmeditat\w*|\bstillness',
    'Organs': r'\bkidneys?\b|\bliver\b|\blungs?\b|\bspleen\b|\bstomach\b|\borgans?\b|\bbladder\b',
    'Chi': r'\bchi\b|\bqi\b|\bmeridians?\b|\bdan ?tien\b|\btan ?tien\b|\blife force\b',
    'Tai chi & qigong': r'tai chi|qigong|chi kung|\btao yin\b|\biron shirt\b|\bba duan jin\b|\bmartial',
    'Seasons': r'\bspring\b|\bsummer\b|\bautumn\b|\bwinter\b|\bseasons?\b|\bequinox\b|\bsolstice\b',
    'Emotions': r'\banger\b|\bfear\b|\bgrief\b|\bsadness\b|\bworry\b|\banxiety\b|\bemotions?\b|\bemotional\b',
    'Stress & sleep': r'\bstress\w*|\bsleep\w*|\bnervous system\b|\bfatigue\b|\bexhaust\w*',
    'Letting go': r'\blet go\b|\bletting go\b|\bnon-?doing\b|\bwu wei\b|\bsurrender\w*|\bsimplicity\b|\byield\w*',
    'Healing practices': r'inner smile|microcosmic|healing sounds|chi nei tsang|\breiki\b|\bacupressure\b',
    'Tao Te Ching': r'tao te ching|lao tzu|laozi|chuang tzu|zhuangzi|\bthe sage\b',
}


def topics_for(title, body_html, words):
    body = re.sub(r'<[^>]+>', ' ', body_html).lower()
    t = title.lower()
    score = {k: len(re.findall(rx, body)) + 3 * len(re.findall(rx, t)) for k, rx in TOPICS.items()}
    if re.search(r"alchemist.{0,3}s tao te ching", body):      # the plug for Andrew's own Tao Te Ching book
        score['Tao Te Ching'] += 2
    out = [k for k, v in sorted(score.items(), key=lambda x: -x[1]) if v >= 2][:3]
    lines = body_html.count('<br>') + body_html.count('<p>')
    if words < 150 and lines >= 6 and 'Verses' not in out:
        out = (out + ['Verses'])[:3] if len(out) < 3 else out[:2] + ['Verses']
    return out


# ---------- helpers ----------

def to_http(url):
    # thetaoblog.com's https certificate is not valid; the http URLs serve the same files
    return re.sub(r'^https://(www\.)?thetaoblog\.com', 'http://thetaoblog.com', url or '')


def fix_mojibake(s):
    """WordPress saved some posts' UTF-8 as Windows-1252 ('worldâ€™s'); undo that where it happened."""
    if not s or not re.search('[âÃÂ][\u0080-\u00ff\u0152-\u0192\u02c6-\u02dc\u2013-\u2122]', s):
        return s
    def fix(m):
        try:
            return m.group(0).encode('cp1252').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            return m.group(0)
    return re.sub('[âÃÂ][\u0080-\u00ff\u0152-\u0192\u02c6-\u02dc\u2013-\u2122]{1,2}', fix, s)


def clean_text(s):
    return re.sub(r'\s+', ' ', fix_mojibake(html.unescape(s or '')).replace('\xa0', ' ')).strip()


def norm(s):
    return re.sub(r'[^0-9a-z]+', '', clean_text(s).lower())


def slugify(s):
    s = unicodedata.normalize('NFKD', unquote(s)).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s[:200] or 'post'


def text_of(inner):
    return clean_text(re.sub(r'<[^>]+>', ' ', inner))


def esc(s):
    return html.escape(s, quote=False)


def image_url(img):
    """Full-size original: the wrapping <a href> when it points at an image, else src minus the size suffix."""
    a = img.getparent()
    if a is not None and a.tag == 'a' and IMAGE_EXT.search(a.get('href', '')):
        return to_http(a.get('href'))
    return to_http(SIZE_SUFFIX.sub('', img.get('src', '')))


def local_path(url):
    p = urlparse(url)
    m = re.search(r'/wp-content/uploads/(.+)$', p.path)
    rel = m.group(1) if m else p.netloc + '/' + p.path.lstrip('/')
    return os.path.join('assets/wp-import', unquote(rel))


# ---------- body conversion ----------

class Post:
    def __init__(self, raw, slug_map):
        self.raw, self.slug_map, self.flags, self.images = raw, slug_map, [], []

    def flag(self, msg):
        if msg not in self.flags:
            self.flags.append(msg)

    def link(self, href):
        href = to_http(href)
        p = urlparse(href)
        if p.netloc in ('thetaoblog.com', 'www.thetaoblog.com'):
            seg = [s for s in p.path.split('/') if s]
            if len(seg) == 1 and seg[0] in self.slug_map:
                self.flag('link to another post rewritten to its new address')
                return '/writings/' + self.slug_map[seg[0]]
            if seg and seg[0] == 'services':
                return '/courses'
            if seg and seg[0] == 'wp-content':
                self.flag('link to a WordPress file kept (will break when WordPress is retired): ' + href)
        return href

    def ser(self, el):
        parts = [esc(el.text or '')]
        for ch in el:
            if not isinstance(ch.tag, str):
                parts.append(esc(ch.tail or ''))
                continue
            tag = RENAME.get(ch.tag, ch.tag)
            if tag == 'br':
                parts.append('<br>')
            elif tag == 'a':
                if ch.find('.//img') is not None and not ch.text_content().strip():
                    parts.append(self.ser(ch))
                else:
                    inner = self.ser(ch)
                    href = ch.get('href', '')
                    if re.fullmatch(r'\s*(https?://|www\.)\S+\s*', html.unescape(re.sub(r'<[^>]+>', '', inner))):
                        host = urlparse(to_http(href)).netloc.replace('www.', '')     # a bare pasted URL as the link text
                        inner = 'Get the book on Amazon' if 'amazon.' in host else esc(host or 'Link')
                        self.flag('bare web address shown as a readable link')
                    parts.append(f'<a href="{html.escape(self.link(href))}">{inner}</a>' if href else inner)
            elif tag in ('strong', 'em', 'li', 'ul', 'ol'):
                parts.append(f'<{tag}>{self.ser(ch)}</{tag}>')
            else:
                parts.append(self.ser(ch))
            parts.append(esc(ch.tail or ''))
        return ''.join(parts)

    @staticmethod
    def tidy(s):
        s = re.sub(r'\s+', ' ', s.replace('\xa0', ' '))
        s = re.sub(r'\s*<br>\s*', '<br>', s)
        s = re.sub(r'<(strong|em)>\s+', r' <\1>', s)
        s = re.sub(r'\s+</(strong|em)>', r'</\1> ', s)
        s = re.sub(r'<(strong|em)></\1>', '', s)
        s = re.sub(r'\s*(</?(?:ul|ol|li)>)\s*', r'\1', s)
        s = re.sub(r' {2,}', ' ', s)
        return re.sub(r'^(<br>|\s)+|(<br>|\s)+$', '', s)

    def embed(self, el):
        """Iframes and WordPress embed blocks: YouTube becomes a Webflow video figure, the rest a plain link."""
        ifr = el if el.tag == 'iframe' else el.find('.//iframe')
        src = (ifr.get('src') if ifr is not None else None) or (el.find('.//a').get('href') if el.find('.//a') is not None else '')
        src = html.unescape(src or '')
        host = urlparse(src).netloc
        yt = re.search(r'(?:youtube\.com/embed/|youtu\.be/|v=)([\w-]{11})', src)
        if yt:
            vid = yt.group(1)
            self.flag('YouTube video kept as a Webflow video embed')
            return ('raw', f'<figure class="w-richtext-figure-type-video w-richtext-align-fullwidth"><div data-page-url="https://www.youtube.com/watch?v={vid}"><iframe src="https://www.youtube.com/embed/{vid}" allowfullscreen></iframe></div></figure>')
        if 'amazon' in host:
            q = parse_qs(urlparse(src).query)
            asin = (q.get('asin') or re.findall(r'/(?:dp|d)/([A-Z0-9]{10})', src) or [None])[0]
            self.flag('Kindle preview embed replaced by a link (Webflow cannot embed it)')
            url = f'https://www.amazon.com/dp/{asin}' if asin else src
            return ('p', f'<a href="{html.escape(url)}">Read a free sample on Kindle</a>')
        if src:
            self.flag(f'embedded page from {host} replaced by a link')
            return ('p', f'<a href="{html.escape(self.link(src))}">{esc(host or src)}</a>')
        self.flag('empty embed block removed')
        return None

    def convert(self):
        raw = self.raw
        content = fix_mojibake(re.sub(r'<!--.*?-->', '', raw['content']['rendered'], flags=re.S))
        if re.search(r'\[[a-z_]+[^\]]*\]', re.sub(r'<[^>]+>', '', content)):
            self.flag('possible WordPress shortcode left in the text')
        root = lxml.html.fromstring(f'<div>{content}</div>')
        for bad in root.xpath('.//script|.//style|.//noscript'):
            bad.drop_tree()

        tops = []
        def collect(el):
            for ch in el:
                if not isinstance(ch.tag, str):
                    continue
                if ch.tag == 'div' and 'wp-block-embed__wrapper' not in (ch.get('class') or ''):
                    collect(ch)
                else:
                    tops.append(ch)
        collect(root)

        blocks = []                                  # (kind, inner): kind p/h2../ul/ol/blockquote/img/raw
        for el in tops:
            tag = RENAME.get(el.tag, el.tag)
            cls = el.get('class') or ''
            if tag == 'iframe' or 'wp-block-embed' in cls or (tag == 'figure' and el.find('.//iframe') is not None):
                b = self.embed(el)
                if b:
                    blocks.append(b)
                continue
            if tag == 'table':
                self.flag('table flattened to paragraphs (Webflow Rich Text has no tables)')
                for tr in el.iter('tr'):
                    t = ' | '.join(clean_text(td.text_content()) for td in tr if isinstance(td.tag, str))
                    if t.strip(' |'):
                        blocks.append(('p', esc(t)))
                continue
            inner_embeds = []
            for ifr in el.findall('.//iframe'):           # embeds pasted inside a paragraph
                b = self.embed(ifr)
                if b:
                    inner_embeds.append(b)
                ifr.drop_tree()
            imgs = [el] if tag == 'img' else el.findall('.//img')
            for img in imgs:
                url = image_url(img)
                if not url:
                    continue
                if 's.w.org' in url:                 # WordPress emoji images -> drop (the text keeps the meaning)
                    self.flag('WordPress emoji image dropped')
                    img.drop_tree() if img is not el else None
                    continue
                self.images.append(url)
                blocks.append(('img', url))
                node = img
                while node is not el and node.getparent() is not el and node.getparent().tag == 'a' and not node.getparent().text_content().strip():
                    node = node.getparent()
                if node is not el:
                    node.drop_tree()
            if tag in ('figure', 'img'):
                cap = el.find('.//figcaption')
                if cap is not None and cap.text_content().strip():
                    blocks.append(('p', f'<em>{esc(clean_text(cap.text_content()))}</em>'))
                continue
            if tag not in BLOCK:
                tag = 'p'
            if inner_embeds:
                if text_of(self.ser(el)):
                    blocks.append(('p', self.tidy(self.ser(el))))
                blocks.extend(inner_embeds)
                continue
            if tag == 'p':
                for piece in re.split(r'(?:<br>[\s\xa0]*){2,}', self.ser(el)):
                    blocks.append(('p', self.tidy(piece)))
            else:
                if tag.startswith('h'):
                    self.flag('has subheadings')
                blocks.append((tag, self.tidy(self.ser(el))))

        # Instagram spacer lines ("." or "-" alone, used to fake blank lines) are formatting, not writing.
        spacer = re.compile(r'[.\-–—_•·*~…]+')
        cleaned = []
        for t, i in blocks:
            if t == 'p':
                lines = [l for l in i.split('<br>') if not spacer.fullmatch(text_of(l))]
                if len(lines) != len(i.split('<br>')):
                    self.flag('Instagram spacer lines removed')
                i = self.tidy('<br>'.join(lines))
            cleaned.append((t, i))
        blocks = [(t, i) for t, i in cleaned if t in ('img', 'raw') or text_of(i)]

        # Title repeated as the first line of text (Instagram-style captions do this constantly).
        title = clean_text(raw['title']['rendered'])
        tn = norm(title)
        for idx, (t, inner) in enumerate(blocks[:3]):
            if t == 'img':
                continue
            if t != 'p':
                break
            if tn and norm(text_of(inner)) == tn:
                blocks.pop(idx)
            else:
                first, sep, rest = inner.partition('<br>')
                if sep and tn and norm(text_of(first)) == tn:
                    blocks[idx] = (t, self.tidy(rest))
            break

        # The first image becomes the cover when it leads the post (the image IS the post for most of these).
        cover = None
        if blocks and blocks[0][0] == 'img':
            cover = blocks.pop(0)[1]
        return title, cover, blocks


def render(blocks):
    out = []
    for t, inner in blocks:
        if t == 'img':
            out.append(f'<figure><img src="{html.escape(inner)}" alt=""></figure>')
        elif t == 'raw':
            out.append(inner)
        else:
            out.append(f'<{t}>{inner}</{t}>')
    return '\n'.join(out)


# ---------- images ----------

def fetch(url):
    dest = os.path.join(ROOT, local_path(url))
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return url, dest, None
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    r = subprocess.run(['curl', '-sfL', '--max-time', '60', '-o', dest, url])
    if r.returncode != 0:
        if os.path.exists(dest):
            os.remove(dest)
        return url, None, f'download failed (curl {r.returncode})'
    try:
        with Image.open(dest) as im:
            im.verify()
    except Exception as e:
        os.remove(dest)
        return url, None, f'not a readable image ({e.__class__.__name__})'
    return url, dest, None


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--refetch', action='store_true', help='download the WordPress REST dump again first')
    ap.add_argument('--no-images', action='store_true', help='skip image downloads')
    a = ap.parse_args()

    if a.refetch or not glob.glob(os.path.join(RAW, 'posts-p*.json')):
        os.makedirs(RAW, exist_ok=True)
        page = 1
        while True:
            dest = os.path.join(RAW, f'posts-p{page:02d}.json')
            if subprocess.run(['curl', '-sf', '-o', dest, API.format(page)]).returncode != 0:
                if os.path.exists(dest):
                    os.remove(dest)
                break
            page += 1
    raws = [p for f in sorted(glob.glob(os.path.join(RAW, 'posts-p*.json'))) for p in json.load(open(f))]
    raws.sort(key=lambda p: p['date'])                      # oldest first: duplicates point at the original

    # Posts already in Webflow keep the slug they have there.
    existing = {w['wp-slug']: w['slug'] for w in json.load(open(os.path.join(ROOT, 'data/writings.json')))}
    taken = set(existing.values())
    slug_map = {}
    for p in raws:
        if p['slug'] in existing:
            slug_map[p['slug']] = existing[p['slug']]
    for p in raws:
        if p['slug'] in slug_map:
            continue
        s = slugify(p['slug'])
        base = re.sub(r'-[2-9]$', '', s)
        if base != s and norm(base) == norm(p['title']['rendered']) and base not in taken:
            s = base                                        # WordPress's "-2" de-dupe suffix is not needed here
        if s in taken:
            s = f"{s}-{p['date'][:4]}"
            n = 2
            while s in taken:
                s, n = f"{slugify(p['slug'])}-{p['date'][:4]}-{n}", n + 1
        taken.add(s)
        slug_map[p['slug']] = s

    records, all_images = [], set()
    for raw in raws:
        post = Post(raw, slug_map)
        title, cover, blocks = post.convert()
        body_text = ' '.join(text_of(i) for t, i in blocks if t not in ('img', 'raw'))
        words = len(body_text.split())
        if not title:
            first = next((text_of(i) for t, i in blocks if t == 'p' and text_of(i)), '')
            title = (first[:60].rsplit(' ', 1)[0] + '…') if len(first) > 60 else (first or 'Untitled reflection')
            post.flag('WordPress title was empty; title made from the first words')
        def headline(t):   # a short subtitle line ("Self-Development Through Taoist Practices") is not a summary
            return len(t.split()) < 8 and not re.search(r'[.?!:"\u201d]$', t.strip())
        lead = next((text_of(i) for t, i in blocks if t == 'p' and len(text_of(i)) > 20 and ' ' in text_of(i).strip() and not headline(text_of(i))
                     and not text_of(i).startswith('#') and not re.fullmatch(r'(Read a free sample on Kindle|Get the book on Amazon)', text_of(i))), '')
        excerpt = lead
        if len(lead) > EXCERPT_CHARS:
            cut = lead[:EXCERPT_CHARS + 1]
            end = max(cut.rfind('. '), cut.rfind('? '), cut.rfind('! '))
            excerpt = cut[:end + 1] if end >= 80 else cut.rsplit(' ', 1)[0].rstrip('.,;:—-') + '…'
        if not excerpt:
            excerpt = title
            post.flag('no text to make an excerpt from; excerpt = title')
        if re.search(r'#\w{3,}', body_text):
            post.flag('hashtags in the text')
        if re.search(r'\bthetaoblog\.com\b', body_text, re.I):
            post.flag('"TheTaoBlog.com" signature line')
        if words < 30 and not cover:
            post.flag('very short and no image')
        if not blocks and not cover:
            post.flag('EMPTY post')
        media = (raw.get('_embedded') or {}).get('wp:featuredmedia') or []
        if not cover and media and media[0].get('source_url'):
            cover = to_http(media[0]['source_url'])
            post.images.insert(0, cover)
        all_images.update(post.images)
        records.append({
            'wp_id': raw['id'], 'wp_url': to_http(raw['link']), 'wp_slug': raw['slug'],
            'slug': slug_map[raw['slug']], 'in_webflow': raw['slug'] in existing,
            'name': title[:256], 'published_on': raw['date'][:10] + 'T12:00:00.000Z',
            'kind': 'Essay' if words >= ESSAY_WORDS else 'Reflection', 'words': words,
            'excerpt': excerpt, 'cover': cover, 'cover_alt': '',
            'topics': topics_for(title, render(blocks), words),
            'body': render(blocks), 'images': post.images,
            'text_hash': hashlib.md5(norm(body_text).encode()).hexdigest(),
            'flags': post.flags,
        })

    # Repeats point at the oldest copy. duplicate_of = same text AND same image (a true copy);
    # text_repeat_of = same text posted again with a different image or title.
    def stem(u):
        return re.sub(r'(-\d+x\d+|-\d)$', '', os.path.splitext(os.path.basename(u))[0]).lower() if u else ''
    first_exact, first_text = {}, {}
    for r in records:
        r['duplicate_of'] = r['text_repeat_of'] = None
        if r['words'] >= 3:
            exact, text = (r['text_hash'], stem(r['cover'])), r['text_hash']
        elif r['cover']:
            exact = text = ('img', stem(r['cover']))
        else:
            continue
        if exact in first_exact:
            r['duplicate_of'] = first_exact[exact]
        elif text in first_text:
            r['text_repeat_of'] = first_text[text]
        first_exact.setdefault(exact, r['wp_id'])
        first_text.setdefault(text, r['wp_id'])
    title_counts = collections.Counter(norm(r['name']) for r in records)
    for r in records:
        r['same_title_count'] = title_counts[norm(r['name'])]
        del r['text_hash']

    # Images: download every one so the import does not need WordPress online.
    failed = {}
    if not a.no_images:
        with concurrent.futures.ThreadPoolExecutor(8) as ex:
            for url, dest, err in ex.map(fetch, sorted(all_images)):
                if err:
                    failed[url] = err
    for r in records:
        r['images_local'] = {u: local_path(u) for u in r['images'] if u not in failed}
        for u in r['images']:
            if u in failed:
                r['flags'].append(f'image could not be downloaded ({failed[u]}): {u}')

    os.makedirs(OUT, exist_ok=True)
    json.dump(records, open(os.path.join(OUT, 'writings-all.json'), 'w'), ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, 'redirects.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['old_path', 'new_path'])
        for r in records:
            w.writerow([urlparse(r['wp_url']).path, '/writings/' + r['slug']])
        w.writerow(['/blog/', '/writings'])
        w.writerow(['/services/', '/courses'])
        w.writerow(['/gallery/', '/articles'])
        w.writerow(['/about/', '/about'])
        w.writerow(['/faq/', '/faq'])
        w.writerow(['/contact/', '/contact'])
        w.writerow(['/events/', '/events'])

    # Report
    by_year = collections.Counter(r['published_on'][:4] for r in records)
    kinds = collections.Counter(r['kind'] for r in records)
    dups = [r for r in records if r['duplicate_of']]
    reps = [r for r in records if r['text_repeat_of']]
    flag_counts = collections.Counter(re.sub(r':\s.*$', '', re.sub(r'\(curl \d+\)|\(.*?\)', '', f)).strip() for r in records for f in r['flags'])
    size = sum(os.path.getsize(os.path.join(ROOT, p)) for r in records for p in r['images_local'].values() if os.path.exists(os.path.join(ROOT, p)))
    lines = [
        '# WordPress export: thetaoblog.com', '',
        f'- Posts: **{len(records)}** ({records[0]["published_on"][:10]} to {records[-1]["published_on"][:10]})',
        f'- Already in Webflow: {sum(r["in_webflow"] for r in records)} (the importer skips them)',
        f'- Kind: ' + ', '.join(f'{k} {v}' for k, v in kinds.most_common()) + f' (Essay = {ESSAY_WORDS}+ words)',
        f'- Exact duplicates (same text and image as an earlier post): **{len(dups)}** (`--skip-duplicates`)',
        f'- Text repeats (same words, new image or title): **{len(reps)}** (`--skip-repeats`)',
        f'- Distinct titles: {len({norm(r["name"]) for r in records})}',
        f'- With a cover image: {sum(1 for r in records if r["cover"])}; images downloaded: {len(all_images) - len(failed)} of {len(all_images)} ({size / 1e6:.0f} MB in assets/wp-import/)',
        f'- Image alt text: none in WordPress; every image imports with empty alt (decorative) until described',
        '', '## Topics (derived from the text; at most 3 per post)', '', '| Topic | Posts |', '|---|---|'] + [f'| {k} | {v} |' for k, v in collections.Counter(t for r in records for t in r['topics']).most_common()] + [
        f'| (none) | {sum(1 for r in records if not r["topics"])} |',
        '', '## Per year', '', '| Year | Posts |', '|---|---|'] + [f'| {y} | {n} |' for y, n in sorted(by_year.items())] + [
        '', '## Flags (posts affected)', '', '| Flag | Posts |', '|---|---|'] + [f'| {k} | {v} |' for k, v in flag_counts.most_common()] + [
        '', '## Failed image downloads', ''] + ([f'- {u}: {e}' for u, e in sorted(failed.items())] or ['None.'])
    open(os.path.join(OUT, 'report.md'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines[:12]))


if __name__ == '__main__':
    main()
