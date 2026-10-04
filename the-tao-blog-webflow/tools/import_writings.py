#!/usr/bin/env python3
"""One-shot import of the WordPress posts into the Webflow "Writings" collection.

Reads data/import/writings-all.json (built by tools/wp_export.py). Dry run by
default: it prints what it WOULD import and checks every record. Add --go to
create the items. Safe to run again -- anything already in the collection (same
slug) is skipped, and progress is saved in data/import/state.json.

  export WEBFLOW_TOKEN=...            # Webflow > Site settings > Apps & integrations > API access
                                      # scopes: CMS read+write, Assets read+write
  python3 tools/import_writings.py --since 2023-01-01 --skip-duplicates          # look first
  python3 tools/import_writings.py --since 2023-01-01 --skip-duplicates --go     # then do it

Selection (combine freely; default = every post not already in Webflow):
  --since / --until YYYY-MM-DD   by publish date
  --kind Essay|Reflection        Essay = 300+ words, Reflection = shorter (image-led) posts
  --newest N                     only the N newest of what is left after the other filters
  --only FILE / --exclude FILE   one slug or old WordPress URL per line
  --skip-duplicates              leave out exact copies (same text and image as an earlier post)
  --skip-repeats                 also leave out the same text re-posted with a new image or title
Cleanup:
  --strip-hashtags               drop lines that are only hashtags
  --strip-signature              drop "TheTaoBlog.com" lines
Images:
  --images wordpress             (default) Webflow copies each image from thetaoblog.com
  --images local                 upload the downloaded copies in assets/wp-import/ first
                                 (use this once WordPress is switched off)
Run:
  --go                           actually import (otherwise: dry run)
  --live                         publish each post as it is created (default: staged --
                                 posts go live at the next site publish)
  --batch N                      posts per request (default 25, max 100)
Posts with no text and no image are always skipped. Imported posts are never featured.
"""
import argparse, datetime, hashlib, html, json, mimetypes, os, re, sys, time, uuid
import urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data/import/writings-all.json')
STATE = os.path.join(ROOT, 'data/import/state.json')
API = os.environ.get('WEBFLOW_API_BASE', 'https://api.webflow.com/v2')

SITE_ID = '6ac1539dd172eb63b02331f3'            # Andrew-Tao-Blog
COLLECTION_ID = '6ac15c0141820496aa6fb3e6'      # Writings
FREE_PLAN_ITEMS = 50                            # Webflow's free plan CMS item limit
FIELDS = {'name': 'name', 'slug': 'slug', 'excerpt': 'excerpt', 'body': 'body',
          'published_on': 'published-on-2', 'kind': 'kind', 'featured': 'featured', 'cover': 'cover-image'}
TOPIC_FIELDS = ['topic-1', 'topic-2', 'topic-3']   # dropdowns; each takes the option id of a topic name
TOPIC_OPTIONS = json.load(open(os.path.join(ROOT, 'webflow-ids.json'))).get('topic_options', {})
SLUG_RE = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
S3_FIELD = {'acl': 'acl', 'bucket': 'bucket', 'key': 'key', 'policy': 'Policy', 'xAmzAlgorithm': 'X-Amz-Algorithm',
            'xAmzCredential': 'X-Amz-Credential', 'xAmzDate': 'X-Amz-Date', 'xAmzSignature': 'X-Amz-Signature',
            'successActionStatus': 'success_action_status', 'contentType': 'Content-Type', 'cacheControl': 'Cache-Control'}


# ---------- Webflow API ----------

class Webflow:
    def __init__(self, token):
        self.token = token

    def call(self, method, path, body=None, attempt=0):
        req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                     headers={'Authorization': f'Bearer {self.token}', 'accept': 'application/json',
                                              'content-type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                time.sleep(1.1)                 # stay under 60 requests a minute
                raw = r.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors='replace')[:800]
            if (e.code == 429 or e.code >= 500) and attempt < 5:
                wait = int(e.headers.get('Retry-After') or 0) or [5, 15, 45, 60, 90][attempt]
                print(f'   Webflow said {e.code}; waiting {wait}s and retrying', flush=True)
                time.sleep(wait)
                return self.call(method, path, body, attempt + 1)
            raise SystemExit(f'\nWebflow refused {method} {path}: HTTP {e.code}\n{detail}\n'
                             'Nothing after this point was sent. Fix the cause and run the same command again; '
                             'finished posts are remembered and skipped.')

    def existing_slugs(self):
        slugs, offset = set(), 0
        while True:
            page = self.call('GET', f'/collections/{COLLECTION_ID}/items?limit=100&offset={offset}')
            items = page.get('items', [])
            slugs.update(i['fieldData']['slug'] for i in items)
            offset += len(items)
            if not items or offset >= page.get('pagination', {}).get('total', 0):
                return slugs

    def upload_asset(self, path):
        data = open(path, 'rb').read()
        name = os.path.basename(path)
        if len(name) > 90:
            stem, ext = os.path.splitext(name)
            name = stem[:80] + ext
        meta = self.call('POST', f'/sites/{SITE_ID}/assets', {'fileName': name, 'fileHash': hashlib.md5(data).hexdigest()})
        fields = {S3_FIELD.get(k, k): str(v) for k, v in meta['uploadDetails'].items()}
        boundary = uuid.uuid4().hex
        parts = [f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields.items()]
        ctype = fields.get('Content-Type') or mimetypes.guess_type(name)[0] or 'application/octet-stream'
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\nContent-Type: {ctype}\r\n\r\n'.encode()
                     + data + f'\r\n--{boundary}--\r\n'.encode())
        req = urllib.request.Request(meta['uploadUrl'], data=b''.join(parts), method='POST',
                                     headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
        with urllib.request.urlopen(req, timeout=180) as r:
            if r.status not in (200, 201, 204):
                raise SystemExit(f'Image upload failed for {path}: HTTP {r.status}')
        return meta['hostedUrl']


# ---------- selection and cleanup ----------

def read_list(path):
    out = set()
    for line in open(path):
        line = line.strip()
        if line and not line.startswith('#'):
            out.add(line.rstrip('/').split('/')[-1])     # a slug or a full old URL
    return out


def segments_filter(body, drop):
    """Remove whole lines (paragraphs, or <br>-separated lines inside one) that match drop(text)."""
    def fix_p(m):
        lines = re.split(r'<br>', m.group(1))
        keep = [l for l in lines if not drop(html.unescape(re.sub(r'<[^>]+>', '', l)).strip())]
        return f'<p>{"<br>".join(keep)}</p>' if ''.join(keep).strip() else ''
    out = re.sub(r'<p>(.*?)</p>', fix_p, body, flags=re.S)
    return re.sub(r'\n{2,}', '\n', out).strip()


def is_hashtags(t):
    return bool(t) and bool(re.fullmatch(r'(#[\w’\']+[\s,.]*)+', t))


def is_signature(t):
    return bool(re.fullmatch(r'(www\.)?thetaoblog\.com\.?', t, re.I))


def select(records, a):
    only = read_list(a.only) if a.only else None
    exclude = read_list(a.exclude) if a.exclude else set()
    out, why = [], {}
    def skip(r, reason):
        why[reason] = why.get(reason, 0) + 1
    for r in records:
        keys = {r['slug'], r['wp_slug']}
        if r['in_webflow']:
            skip(r, 'already in Webflow (imported earlier)')
        elif 'EMPTY post' in r['flags']:
            skip(r, 'empty (no text, no image)')
        elif only is not None and not keys & only:
            skip(r, 'not in --only list')
        elif keys & exclude:
            skip(r, 'in --exclude list')
        elif a.since and r['published_on'][:10] < a.since:
            skip(r, f'before --since {a.since}')
        elif a.until and r['published_on'][:10] > a.until:
            skip(r, f'after --until {a.until}')
        elif a.kind and r['kind'] != a.kind:
            skip(r, f'not --kind {a.kind}')
        elif a.skip_duplicates and r['duplicate_of']:
            skip(r, 'exact duplicate (--skip-duplicates)')
        elif a.skip_repeats and r['text_repeat_of']:
            skip(r, 'text repeat (--skip-repeats)')
        else:
            out.append(r)
    if a.newest and len(out) > a.newest:
        out.sort(key=lambda r: r['published_on'], reverse=True)
        why[f'beyond --newest {a.newest}'] = len(out) - a.newest
        out = out[:a.newest]
    out.sort(key=lambda r: r['published_on'])
    return out, why


def build_item(r, a, image_url):
    body = r['body']
    if a.strip_hashtags:
        body = segments_filter(body, is_hashtags)
    if a.strip_signature:
        body = segments_filter(body, is_signature)
    for src in r['images']:
        body = body.replace(f'src="{html.escape(src)}"', f'src="{html.escape(image_url(src))}"')
    fd = {FIELDS['name']: r['name'], FIELDS['slug']: r['slug'], FIELDS['excerpt']: r['excerpt'],
          FIELDS['body']: body, FIELDS['published_on']: r['published_on'], FIELDS['kind']: r['kind'],
          FIELDS['featured']: False}
    if r['cover']:
        fd[FIELDS['cover']] = {'url': image_url(r['cover']), 'alt': r.get('cover_alt') or ''}
    for field, name in zip(TOPIC_FIELDS, r.get('topics') or []):
        opt = TOPIC_OPTIONS.get(field, {}).get(name)
        if opt:
            fd[field] = opt
    return fd


def problems(fd, r):
    p = []
    if not fd['name'] or len(fd['name']) > 256:
        p.append('name missing or over 256 characters')
    if not SLUG_RE.match(fd['slug']) or len(fd['slug']) > 256:
        p.append(f'slug not valid: {fd["slug"]}')
    if not fd['excerpt'].strip():
        p.append('excerpt is empty (required in Webflow)')
    if not fd['body'].strip() and FIELDS['cover'] not in fd:
        p.append('no text and no image')
    try:
        datetime.datetime.strptime(fd[FIELDS['published_on']], '%Y-%m-%dT%H:%M:%S.000Z')
    except ValueError:
        p.append('bad date')
    return p


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--since'); ap.add_argument('--until')
    ap.add_argument('--kind', choices=['Essay', 'Reflection'])
    ap.add_argument('--newest', type=int)
    ap.add_argument('--only'); ap.add_argument('--exclude')
    ap.add_argument('--skip-duplicates', action='store_true'); ap.add_argument('--skip-repeats', action='store_true')
    ap.add_argument('--strip-hashtags', action='store_true'); ap.add_argument('--strip-signature', action='store_true')
    ap.add_argument('--images', choices=['wordpress', 'local'], default='wordpress')
    ap.add_argument('--go', action='store_true'); ap.add_argument('--live', action='store_true')
    ap.add_argument('--batch', type=int, default=25)
    a = ap.parse_args()
    a.batch = max(1, min(a.batch, 100))

    records = json.load(open(DATA))
    chosen, why = select(records, a)
    state = json.load(open(STATE)) if os.path.exists(STATE) else {'created': {}, 'assets': {}}

    missing_local = []
    if a.images == 'local':
        for r in chosen:
            for src in r['images']:
                rel = r['images_local'].get(src)
                if not rel or not os.path.exists(os.path.join(ROOT, rel)):
                    missing_local.append(src)

    def image_url_dry(src):
        return src
    items = [(r, build_item(r, a, image_url_dry)) for r in chosen]
    bad = [(r, p) for r, fd in items for p in [problems(fd, r)] if p]

    print(f'{len(records)} posts in the export file. Selected: {len(chosen)}.')
    for reason, n in sorted(why.items(), key=lambda x: -x[1]):
        print(f'   skipped {n:5}  {reason}')
    if chosen:
        print(f'   dates {chosen[0]["published_on"][:10]} to {chosen[-1]["published_on"][:10]}; '
              f'{sum(r["kind"] == "Essay" for r in chosen)} essays, {sum(r["kind"] == "Reflection" for r in chosen)} reflections; '
              f'{sum(len(r["images"]) for r in chosen)} images')
    print(f'   images come from: {"downloaded copies, uploaded to Webflow" if a.images == "local" else "thetaoblog.com (WordPress must still be online)"}')
    print(f'   posts go: {"LIVE immediately" if a.live else "staged; live at the next site publish"}')
    if missing_local:
        print(f'   !! {len(missing_local)} images have no downloaded copy; those images will be left out')
    if bad:
        print(f'   !! {len(bad)} posts fail validation and will be skipped:')
        for r, p in bad[:20]:
            print(f'      {r["slug"]}: {"; ".join(p)}')
    if not a.go:
        print('\nDry run only. Nothing was sent to Webflow. Add --go to import.')
        return

    token = os.environ.get('WEBFLOW_TOKEN')
    if not token:
        raise SystemExit('Set WEBFLOW_TOKEN first (Webflow > Site settings > Apps & integrations > API access).')
    wf = Webflow(token)
    have = wf.existing_slugs()
    todo = [(r, fd) for r, fd in items if not problems(fd, r) and r['slug'] not in have and str(r['wp_id']) not in state['created']]
    print(f'\nThe collection holds {len(have)} items. {len(chosen) - len(todo)} selected posts are already there or invalid; importing {len(todo)}.')
    if len(have) + len(todo) > FREE_PLAN_ITEMS:
        print(f'   Note: that makes {len(have) + len(todo)} items. Webflow\'s free plan holds {FREE_PLAN_ITEMS}; '
              'the site needs the CMS plan (2,000) or Webflow will refuse partway.')

    def image_url(src):
        if a.images == 'wordpress':
            return src
        rel = next((r['images_local'][src] for r in chosen if src in r['images_local']), None)
        if not rel:
            return src
        if rel not in state['assets']:
            state['assets'][rel] = wf.upload_asset(os.path.join(ROOT, rel))
            json.dump(state, open(STATE, 'w'), indent=1)
        return state['assets'][rel]

    log = open(os.path.join(ROOT, f'data/import/import-log-{datetime.datetime.now():%Y%m%d-%H%M%S}.jsonl'), 'w')
    done = 0
    path = f'/collections/{COLLECTION_ID}/items' + ('/live' if a.live else '')
    for i in range(0, len(todo), a.batch):
        chunk = todo[i:i + a.batch]
        payload = {'items': [{'isDraft': False, 'isArchived': False, 'fieldData': build_item(r, a, image_url)} for r, _ in chunk]}
        res = wf.call('POST', path, payload)
        created = res.get('items') or ([res] if res.get('id') else [])
        by_slug = {c['fieldData']['slug']: c['id'] for c in created if c.get('fieldData')}
        for r, _ in chunk:
            item_id = by_slug.get(r['slug'])
            if item_id:
                state['created'][str(r['wp_id'])] = item_id
                log.write(json.dumps({'wp_id': r['wp_id'], 'slug': r['slug'], 'item_id': item_id}) + '\n')
        json.dump(state, open(STATE, 'w'), indent=1)
        done += len(by_slug)
        print(f'   {done}/{len(todo)} imported', flush=True)
    log.close()
    print(f'\nDone: {done} posts imported. ' + ('They are live.' if a.live else 'Publish the site in Webflow to make them live.'))


if __name__ == '__main__':
    main()
