#!/usr/bin/env python3
"""Exercise tools/import_writings.py end to end against a fake Webflow API.

  python3 tests/test_importer.py

The fake checks every request the way Webflow does (fields, slug rules, 100-item
cap), throws one 429 to prove the retry, stores items, and serves an S3-style
upload target for --images local. Nothing touches the real Webflow site.
"""
import json, os, re, shutil, subprocess, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLL = '6ac15c0141820496aa6fb3e6'
SITE = '6ac1539dd172eb63b02331f3'
STORE = {'items': [], 'assets': 0, 'uploads': 0, 'calls': [], 'throttled': False}
REQUIRED = {'name', 'slug', 'excerpt', 'published-on-2'}


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def reply(self, code, obj=None):
        body = json.dumps(obj or {}).encode()
        self.send_response(code)
        self.send_header('content-type', 'application/json')
        if code == 429:
            self.send_header('Retry-After', '1')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        STORE['calls'].append(('GET', self.path))
        m = re.match(rf'/v2/collections/{COLL}/items\?limit=(\d+)&offset=(\d+)', self.path)
        if not m:
            return self.reply(404, {'msg': 'unknown path'})
        lim, off = int(m.group(1)), int(m.group(2))
        self.reply(200, {'items': STORE['items'][off:off + lim], 'pagination': {'total': len(STORE['items'])}})

    def do_POST(self):
        n = int(self.headers.get('content-length', 0))
        raw = self.rfile.read(n)
        STORE['calls'].append(('POST', self.path))
        if self.path == '/s3':
            STORE['uploads'] += 1
            ok = b'name="file"' in raw and b'name="Policy"' in raw and b'name="X-Amz-Signature"' in raw
            return self.reply(201 if ok else 400)
        if self.headers.get('Authorization') != 'Bearer test-token':
            return self.reply(401, {'msg': 'bad token'})
        body = json.loads(raw)
        if self.path == f'/v2/sites/{SITE}/assets':
            STORE['assets'] += 1
            assert re.fullmatch(r'[0-9a-f]{32}', body['fileHash']) and len(body['fileName']) < 100
            port = self.server.server_address[1]
            return self.reply(200, {'uploadUrl': f'http://127.0.0.1:{port}/s3', 'hostedUrl': f'https://cdn.example/{STORE["assets"]}_{body["fileName"]}',
                                    'uploadDetails': {'acl': 'public-read', 'bucket': 'b', 'key': 'k', 'policy': 'p', 'xAmzAlgorithm': 'a',
                                                      'xAmzCredential': 'c', 'xAmzDate': 'd', 'xAmzSignature': 's', 'successActionStatus': '201',
                                                      'contentType': 'image/jpeg', 'cacheControl': 'max-age=1'}})
        if self.path in (f'/v2/collections/{COLL}/items', f'/v2/collections/{COLL}/items/live'):
            if not STORE['throttled']:
                STORE['throttled'] = True
                return self.reply(429, {'msg': 'slow down'})
            items = body.get('items')
            if not items or len(items) > 100 or 'fieldData' in body:
                return self.reply(400, {'msg': 'bad shape'})
            slugs = {i['fieldData']['slug'] for i in STORE['items']}
            out = []
            for it in items:
                fd = it['fieldData']
                missing = REQUIRED - {k for k, v in fd.items() if v not in (None, '')}
                if missing or not re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)*', fd['slug']) or fd['slug'] in slugs or len(fd['name']) > 256:
                    return self.reply(400, {'msg': f'validation failed for {fd.get("slug")}: missing {missing}'})
                if 'cover-image' in fd and not fd['cover-image'].get('url', '').startswith(('http://', 'https://')):
                    return self.reply(400, {'msg': 'image url'})
                slugs.add(fd['slug'])
                rec = {'id': f'item{len(STORE["items"]) + 1}', 'isDraft': it['isDraft'], 'live': self.path.endswith('/live'), 'fieldData': fd}
                STORE['items'].append(rec)
                out.append(rec)
            return self.reply(200, {'items': out})
        self.reply(404, {'msg': 'unknown path'})


def run(*args, token='test-token'):
    env = dict(os.environ, WEBFLOW_API_BASE=f'http://127.0.0.1:{PORT}/v2', WEBFLOW_TOKEN=token)
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools/import_writings.py'), *args], capture_output=True, text=True, env=env, timeout=900)
    return r.returncode, r.stdout + r.stderr


def check(ok, msg):
    print(('PASS ' if ok else 'FAIL ') + msg)
    if not ok:
        FAILS.append(msg)


FAILS = []
server = ThreadingHTTPServer(('127.0.0.1', 0), Fake)
PORT = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()

state = os.path.join(ROOT, 'data/import/state.json')
backup = state + '.bak'
if os.path.exists(state):
    shutil.move(state, backup)
try:
    records = json.load(open(os.path.join(ROOT, 'data/import/writings-all.json')))

    code, out = run('--since', '2024-01-01')
    check(code == 0 and 'Dry run only' in out and not STORE['calls'], 'dry run sends nothing to Webflow')

    code, out = run('--since', '2025-01-01', '--go', token='')
    check(code != 0 and 'Set WEBFLOW_TOKEN' in out, 'refuses to run without a token')

    # 1. real run: the 2024+ posts, duplicates skipped, small batches so batching + the 429 retry are exercised
    code, out = run('--since', '2024-01-01', '--skip-duplicates', '--strip-hashtags', '--strip-signature', '--batch', '7', '--go')
    expect = [r for r in records if r['published_on'] >= '2024' and not r['in_webflow'] and not r['duplicate_of'] and 'EMPTY post' not in r['flags']]
    check(code == 0, f'import run exits cleanly{"" if code == 0 else ": " + out[-600:]}')
    check(len(STORE['items']) == len(expect), f'created {len(STORE["items"])} items, expected {len(expect)}')
    check('waiting 1s and retrying' in out, 'a 429 is retried, not fatal')
    # cleanup options, checked on the posts that actually have hashtag / signature lines (all years)
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import import_writings as iw
    class Opts: strip_hashtags = True; strip_signature = True
    tag_line = re.compile(r'(<p>|<br>)\s*(#[\w’\']+[\s,.]*)+\s*(</p>|<br>)')
    sig_line = re.compile(r'(<p>|<br>)\s*(www\.)?thetaoblog\.com\.?\s*(</p>|<br>)', re.I)
    tagged = [r for r in records if tag_line.search(r['body'])]
    signed = [r for r in records if sig_line.search(r['body'])]
    after = [iw.build_item(r, Opts, lambda s: s)['body'] for r in tagged + signed]
    check(len(tagged) > 0 and len(signed) > 0 and not any(tag_line.search(b) or sig_line.search(b) for b in after),
          f'--strip-hashtags / --strip-signature clean all {len(tagged)} hashtag and {len(signed)} signature posts')
    check(not any(re.search(r'(<p>|<br>)\s*[.\-–—]\s*(</p>|<br>)', r['body']) for r in records), 'no Instagram spacer lines left in any post')
    check(all(i['fieldData']['featured'] is False and i['isDraft'] is False and not i['live'] for i in STORE['items']), 'staged (not live), not draft, never featured')
    ids = json.load(open(os.path.join(ROOT, 'webflow-ids.json')))['topic_options']
    want = {r['slug']: r['topics'] for r in records}
    ok = all([ids[f].get(n) for f, n in zip(['topic-1', 'topic-2', 'topic-3'], want[i['fieldData']['slug']])] ==
             [i['fieldData'].get(f) for f in ['topic-1', 'topic-2', 'topic-3']][:len(want[i['fieldData']['slug']])] for i in STORE['items'])
    check(ok and any('topic-1' in i['fieldData'] for i in STORE['items']), 'each post carries its topics as dropdown option ids')

    # 2. same command again: nothing new
    before = len(STORE['items'])
    code, out = run('--since', '2024-01-01', '--skip-duplicates', '--strip-hashtags', '--strip-signature', '--go')
    check(code == 0 and len(STORE['items']) == before and 'importing 0' in out, 'running the same command twice imports nothing new')

    # 3. lost state file: still no duplicates, because existing slugs are read from the collection first
    os.remove(state)
    code, out = run('--since', '2024-01-01', '--skip-duplicates', '--go')
    check(code == 0 and len(STORE['items']) == before, 'with the state file deleted, slugs already in Webflow are still skipped')

    # 4. local images: 3 posts from 2023, published live
    code, out = run('--since', '2023-06-01', '--until', '2023-12-31', '--newest', '3', '--images', 'local', '--live', '--go')
    new = STORE['items'][before:]
    check(code == 0 and len(new) == 3, f'--newest 3 with local images creates 3 items{"" if code == 0 else ": " + out[-600:]}')
    imgs = [i['fieldData'].get('cover-image', {}).get('url', '') for i in new] + re.findall(r'src="([^"]+)"', ' '.join(i['fieldData']['body'] for i in new))
    check(imgs and all(u.startswith('https://cdn.example/') for u in imgs), f'every image points at an uploaded copy ({len(imgs)} refs, {STORE["uploads"]} uploads)')
    check(all(i['live'] for i in new), '--live uses the live endpoint')
finally:
    server.shutdown()
    if os.path.exists(state):
        os.remove(state)
    if os.path.exists(backup):
        shutil.move(backup, state)
    for f in os.listdir(os.path.join(ROOT, 'data/import')):
        if f.startswith('import-log-'):
            os.remove(os.path.join(ROOT, 'data/import', f))

print(f'\n{"ALL PASS" if not FAILS else str(len(FAILS)) + " FAILED"}')
sys.exit(1 if FAILS else 0)
