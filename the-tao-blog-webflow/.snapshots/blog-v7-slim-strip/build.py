#!/usr/bin/env python3
"""Build the Webflow-shaped Tao Blog.

One source of markup, two outputs:
  python3 build.py            -> site/  (local preview, served at /)
  python3 build.py --fragments -> fragments/<page>/<section>.html (what gets
                                  handed to Webflow's WHTML builder, with
                                  Webflow asset URLs substituted from
                                  asset-map.json)

Every element carries at most ONE class (Webflow-flat). Repeating content
(writings, articles) renders from data/*.json in the same DOM shape Webflow's
CMS Collection List produces, so the local site and the Webflow site can be
checked against each other with one test suite.
"""
import html, json, os, shutil, sys
from urllib.parse import quote as urlquote
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, 'site')
FRAG = os.path.join(ROOT, 'fragments')
FRAGMENTS = '--fragments' in sys.argv

ASSET_MAP = {}
if FRAGMENTS and os.path.exists(os.path.join(ROOT, 'asset-map.json')):
    ASSET_MAP = json.load(open(os.path.join(ROOT, 'asset-map.json')))


def A(path):
    """Asset URL: local root path, or the Webflow CDN URL in fragment mode."""
    p = '/' + path.lstrip('/')
    return ASSET_MAP.get(p, p) if FRAGMENTS else p


def esc(s):
    return html.escape(s, quote=True)


def fmt_date(iso):
    d = datetime.strptime(iso[:10], '%Y-%m-%d')
    return d.strftime('%B ') + str(d.day) + d.strftime(', %Y')  # Webflow's default date format


WRITINGS = json.load(open(os.path.join(ROOT, 'data/writings.json')))
ARTICLES = json.load(open(os.path.join(ROOT, 'data/articles.json')))
WRITINGS.sort(key=lambda w: w['published-on'], reverse=True)
FEATURED = [w for w in WRITINGS if w.get('featured')][:1]
REST = [w for w in WRITINGS if not w.get('featured')]
ARTICLES.sort(key=lambda a: a['display-order'])

# Andrew's video store (Vimeo OTT); the WordPress "Learn More" buttons open these in a new tab
STORE = {'The Inner Smile': 'https://fullbodyenlightenment.vhx.tv/products/the-inner-smile',
         'The Six Healing Sounds': 'https://fullbodyenlightenment.vhx.tv/products/the-six-healing-sounds',
         'The Microcosmic Orbit': 'https://fullbodyenlightenment.vhx.tv/products/the-microcosmic-orbit'}

BLOG_TOPICS = ['Organs', 'Tao Te Ching', 'Chi', 'Tai chi & qigong', 'Verses', 'Meditation', 'Breath',
               'Stress & sleep', 'Emotions', 'Healing practices', 'Seasons', 'Letting go']


def load_blog():
    """Every WordPress post for the blog page: exact copies and empty posts left out. The 20 already in
    Webflow keep their curated text and covers; the rest point at the downloaded images."""
    path = os.path.join(ROOT, 'data/import/writings-all.json')
    if not os.path.exists(path):
        return []
    curated = {w['wp-slug']: w for w in WRITINGS}
    out = []
    for r in json.load(open(path)):
        if r['duplicate_of'] or 'EMPTY post' in r['flags']:
            continue
        if r['wp_slug'] in curated:
            w = dict(curated[r['wp_slug']])
            w['thumb'] = w.get('cover-image')
        else:
            body = r['body']
            for u, rel in r['images_local'].items():
                body = body.replace(f'src="{html.escape(u)}"', f'src="/{rel}"')
            cover = r['images_local'].get(r['cover']) if r['cover'] else None
            thumb = None
            if cover:
                t = os.path.splitext(cover.replace('assets/wp-import/', 'assets/wp-thumbs/', 1))[0] + '.jpg'
                thumb = t if os.path.exists(os.path.join(ROOT, t)) else cover
            w = {'name': r['name'], 'slug': r['slug'], 'published-on': r['published_on'], 'excerpt': r['excerpt'],
                 'kind': r['kind'], 'featured': False, 'cover-image': cover, 'cover-alt': '', 'body': body, 'thumb': thumb}
        w['topics'] = r['topics']
        out.append(w)
    out.sort(key=lambda w: w['published-on'], reverse=True)
    return out


BLOG = load_blog()
TOPICS_BY_SLUG = {w['slug']: w['topics'] for w in BLOG}

NAV_ITEMS = [('Blog', '/blog'), ('Articles', '/articles'), ('Courses', '/courses'),
             ('Events', '/events'), ('About', '/about'), ('FAQ', '/faq')]

# ------------------------------------------------------------------ partials

def site_header(current=None):
    links = ''.join(
        f'<li class="nav-item"><a href="{href}" class="nav-link{" w--current" if href == current else ""}">{label}</a></li>'
        for label, href in NAV_ITEMS)
    mobile = ''.join(f'<a href="{href}" class="mobile-link">{label}</a>' for label, href in NAV_ITEMS)
    return f'''<div class="nav-shell">
<nav class="nav">
  <div class="nav-wrap">
    <a href="/" class="brand"><div class="brand-mark"></div><div>The Tao Blog</div></a>
    <ul role="list" class="nav-links">{links}</ul>
    <div class="nav-actions">
      <a href="/contact#contact" class="btn-nav">Get in touch</a>
      <div class="burger" role="button" tabindex="0" aria-label="Open menu" aria-expanded="false"><div class="burger-line"></div><div class="burger-line"></div><div class="burger-line"></div></div>
    </div>
  </div>
</nav>
<div class="mobile-menu">{mobile}<a href="/contact#contact" class="mobile-cta">Get in touch</a></div>
</div>'''


def site_footer():
    return '''<footer class="footer">
  <div class="wrap">
    <div class="foot-grid">
      <div class="foot-brand">
        <a href="/" class="foot-brand-link"><div class="brand-mark"></div><div>The Tao Blog</div></a>
        <p class="foot-text">Welcome to the present moment. Writings and practices on Taoist meditation, the nervous system, and calm energy in modern life.</p>
      </div>
      <div>
        <h4 class="foot-head">Explore</h4>
        <ul role="list" class="foot-list">
          <li class="foot-item"><a href="/blog" class="foot-link">Blog</a></li>
          <li class="foot-item"><a href="/articles" class="foot-link">Articles</a></li>
          <li class="foot-item"><a href="/courses" class="foot-link">Courses</a></li>
          <li class="foot-item"><a href="/events" class="foot-link">Events</a></li>
        </ul>
      </div>
      <div>
        <h4 class="foot-head">Connect</h4>
        <ul role="list" class="foot-list">
          <li class="foot-item"><a href="/about" class="foot-link">About Andrew</a></li>
          <li class="foot-item"><a href="/faq" class="foot-link">FAQ</a></li>
          <li class="foot-item"><a href="/contact#contact" class="foot-link">Get in touch</a></li>
          <li class="foot-item"><a href="mailto:mccartandrew@gmail.com" class="foot-link">Email</a></li>
        </ul>
      </div>
    </div>
    <div class="legal"><div>&copy; 2026 The Tao Blog. All rights reserved.</div><div>Andrew McCart, PhD &middot; Senior Instructor, Healing Tao</div></div>
  </div>
</footer>'''


def page_hero(eyebrow, title, lede, crumb, title_class='page-title'):
    return f'''<header class="page-hero">
  <div class="page-hero-bg"></div>
  <div class="wrap">
    <div class="eyebrow-page"><div class="eyebrow-line-light"></div><div>{eyebrow}</div></div>
    <h1 class="{title_class}">{title}</h1>
    <p class="page-lede">{lede}</p>
    <div class="crumbs"><a href="/" class="crumb-link">Home</a> / {crumb}</div>
  </div>
</header>'''


def cta_band(title, text, label, href, alt=False, reveal=True):
    sec = 'sec-alt' if alt else 'sec'
    r = ' data-reveal="0"' if reveal else ''
    return f'''<section class="{sec}">
  <div class="wrap">
    <div class="cta-band"{r}>
      <h2 class="cta-title">{title}</h2>
      <p class="cta-text">{text}</p>
      <a href="{href}" class="btn-primary">{label}</a>
    </div>
  </div>
</section>'''


STARS = lambda: f'<img src="{A("assets/icons/stars.svg")}" alt="Five out of five" class="stars"/>'
CHECK = lambda: f'<img src="{A("assets/icons/check.svg")}" alt="" class="ck-icon"/>'


def voice_cards(third_text):
    data = [
        ("I was diagnosed with ADHD and dyslexia. Doctors said even a 45 minute class would be too long for me. Andrew's classes are three hours, yet his teaching style holds my attention the entire session. I leave feeling like I retained it all, and still hungry for more.", 'DG', 'Dan G.', 'Student', '0'),
        ("Andrew's courses teach the student to first lead themselves. He helps you start within and then work your way out, eventually leading others and your community. He leads by example, teaching students to blaze their own trail.", 'MM', 'Mary M.', 'Student', '1'),
        (third_text, 'SC', 'A student', 'Leadership course', '2'),
    ]
    return ''.join(f'''<div class="voice" data-reveal="{d}">{STARS()}<p class="voice-text">{esc(t)}</p><div class="who"><div class="avatar">{i}</div><div><div class="who-name">{n}</div><div class="who-role">{r}</div></div></div></div>'''
                   for t, i, n, r, d in data)


def trust(last_num, last_text):
    return f'''<section class="trust">
  <div class="wrap">
    <div class="trust-grid">
      <div data-reveal="0"><div class="stat-num">20<span class="stat-unit">+</span></div><p class="stat-text">Years studying Taoism in depth</p></div>
      <div data-reveal="1"><div class="stat-num">12</div><p class="stat-text">Healing Tao Senior Instructors studied under</p></div>
      <div data-reveal="2"><div class="stat-num">3</div><p class="stat-text">Continents of study and practice</p></div>
      <div data-reveal="3"><div class="stat-num">{last_num}</div><p class="stat-text">{last_text}</p></div>
    </div>
  </div>
</section>'''

# ------------------------------------------------------------------ CMS item renderers
# These mirror the Webflow Collection List DOM: w-dyn-list > w-dyn-items > w-dyn-item.

SHELL = '--shell' in sys.argv


def cms_list(items_html, list_class='', item_class=''):
    if SHELL:
        return ''
    lc = f' class="{list_class} w-dyn-items"' if list_class else ' class="w-dyn-items"'
    return f'<div class="w-dyn-list"><div role="list"{lc}>' + ''.join(
        f'<div role="listitem" class="{item_class + " " if item_class else ""}w-dyn-item">{h}</div>' for h in items_html) + '</div></div>'


def feature_card(w, cls, tag_text):
    img = A(w['cover-image']) if w.get('cover-image') else ''
    return f'''<a href="/writings/{w['slug']}" class="{cls}" data-reveal="0"><img src="{img}" alt="{esc(w.get('cover-alt') or '')}" loading="lazy" class="feature-img"/><div class="feature-shade"></div><div class="feature-body"><div class="tag">{tag_text}</div><h3 class="feature-title">{esc(w['name'])}</h3><p class="feature-text">{esc(w['excerpt'])}</p></div></a>'''


def post_row(w):
    return f'''<a href="/writings/{w['slug']}" class="post" data-reveal="1"><div class="post-num"></div><div><h3 class="post-title">{esc(w['name'])}</h3><div class="post-meta"><div>{esc(w['kind'])}</div><div class="post-dot"></div><div>{fmt_date(w['published-on'])}</div></div><p class="post-excerpt">{esc(w['excerpt'])}</p></div></a>'''


def idx_writing(w):
    return f'''<a href="/writings/{w['slug']}" class="idx-item" data-reveal="0"><div class="idx-num"></div><div><h3 class="idx-title">{esc(w['name'])}</h3><p class="idx-text">{esc(w['excerpt'])}</p><div class="idx-meta"><div>{esc(w['kind'])}</div><div>&middot;</div><div>{fmt_date(w['published-on'])}</div></div></div></a>'''


def idx_article(a):
    return f'''<a href="{A(a['pdf'])}" class="idx-item" data-reveal="0" data-new-tab="true"><div class="idx-num"></div><div><h3 class="idx-title">{esc(a['name'])}</h3><p class="idx-text">{esc(a['summary'])}</p><div class="idx-meta"><div>{esc(a['kind'])}</div></div></div></a>'''

def short_date(iso):
    d = datetime.strptime(iso[:10], '%Y-%m-%d')
    return d.strftime('%b ') + str(d.day) + d.strftime(', %Y')


def bcard(w):
    img = f'<img src="{A(w["thumb"])}" alt="" loading="lazy" class="bcard-img"/>' if w.get('thumb') else ''
    return (f'<a href="/writings/{w["slug"]}" class="bcard" data-date="{w["published-on"][:10]}" data-kind="{esc(w["kind"])}" '
            f'data-topics="{esc(", ".join(w.get("topics") or []))}">{img}<div class="bcard-body">'
            f'<div class="bcard-kicker"><div>{esc(w["kind"])}</div><div>&middot;</div><div>{short_date(w["published-on"])}</div></div>'
            f'<h3 class="bcard-title">{esc(w["name"])}</h3><p class="bcard-excerpt">{esc(w["excerpt"])}</p></div></a>')


def blog_page():
    n = len(BLOG)
    years = sorted({w['published-on'][:4] for w in BLOG})
    yrs = ''.join(f'<a href="/blog?year={y}" class="blog-year" data-year="{y}"><span class="blog-year-bar"></span><span class="blog-year-label">&rsquo;{y[2:]}</span></a>' for y in years)
    topics = ''.join(f'<a href="/blog?topic={urlquote(t)}" class="side-item" data-topic="{esc(t)}"><span>{esc(t)}</span><span class="side-n"></span></a>' for t in BLOG_TOPICS)
    kinds = ''.join(f'<a href="/blog{q}" class="side-item" data-kind="{k}"><span>{label}</span><span class="side-n"></span></a>' for k, label, q in
                    [('', 'Everything', ''), ('Essay', 'Essays', '?kind=Essay'), ('Reflection', 'Reflections', '?kind=Reflection')])
    sorts = ('<a href="/blog" class="side-item" data-sort="newest"><span>Newest first</span></a>'
             '<a href="/blog?sort=oldest" class="side-item" data-sort="oldest"><span>Oldest first</span></a>')
    pick = next((w for w in BLOG if w.get('featured')), BLOG[0] if BLOG else None)
    pick_img = A(pick['thumb']) if pick and pick.get('thumb') else ''
    chunks = [BLOG[i:i + 100] for i in range(0, len(BLOG), 100)]     # Webflow shows at most 100 per list
    source = ''.join(cms_list([bcard(w) for w in c], 'blog-source-list', 'blog-source-item') for c in chunks)
    chev = '<span class="side-chev">&#8964;</span>'
    def group(title, body, key):
        return (f'<div class="side-group" data-side-group="{key}"><a href="#" class="side-head" aria-expanded="true">'
                f'<span>{title}</span>{chev}</a><div class="side-body">{body}</div></div>')
    return [
        ('pick', f'''<section class="pick-sec" data-nav="light">
  <div class="wrap">
    <div class="blog-pick" data-blog-pick="true"><img src="{pick_img}" alt="" class="blog-pick-img"/><div class="blog-pick-body"><div class="blog-pick-label"><span>A thought for right now</span><span class="blog-pick-date">{fmt_date(pick['published-on']) if pick else ''}</span></div><a href="/writings/{pick['slug'] if pick else ''}" class="blog-pick-title">{esc(pick['name']) if pick else ''}</a><p class="blog-pick-text">{esc(pick['excerpt']) if pick else ''}</p></div><a href="/blog" class="blog-again" aria-label="Show another one"><span class="blog-again-dot"></span><span class="blog-again-text">Another one</span></a></div>
  </div>
</section>'''),
        ('river', f'''<section class="river" data-river="true" data-fold="river">
  <div class="wrap">
    <div class="river-head">
      <div>
        <div class="blog-label"><div class="eyebrow-line"></div><div>The blog &middot; {n:,} posts</div></div>
        <h1 class="river-title">Walk through the years.</h1>
      </div>
      <div class="river-side">
        <div class="blog-years" aria-label="Posts per year">{yrs}</div>
        <a href="#" class="fold-toggle" data-fold-toggle="river">Show the years</a>
      </div>
    </div>
  </div>
  <div class="fold-body">
    <div class="river-stage">
      <a href="#" class="river-btn" data-river-prev="true" aria-label="Earlier years">&larr;</a>
      <div class="river-track" data-river-track="true"><div class="river-inner" data-river-inner="true"><div class="river-line"></div></div></div>
      <a href="#" class="river-btn" data-river-next="true" aria-label="Later years">&rarr;</a>
    </div>
  </div>
</section>'''),
        ('library', f'''<section class="lib-sec" id="browse">
  <div class="wrap">
    <div class="lib">
      <div class="lib-scrim" data-lib-close="true"></div>
      <aside class="lib-side" data-lib-side="true" aria-label="Search and filter">
        <div class="lib-side-top"><div class="side-title">Find a post</div><a href="#" class="lib-close" data-lib-close="true" aria-label="Close">&times;</a></div>
        <div class="side-search"><img src="{A('assets/icons/search.svg')}" alt="" class="side-search-icon"/><input type="search" class="side-search-input" placeholder="Try breath, sleep..." aria-label="Search the blog" autocomplete="off" data-blog-search="true"/></div>
        <div class="side-hint">Press / to search from anywhere</div>
        {group('Topics', topics, 'topics')}
        {group('Type', kinds, 'type')}
        {group('Order', sorts, 'order')}
        <a href="/blog" class="side-clear" data-blog-clear="true">Clear everything</a>
      </aside>
      <div class="lib-main">
        <div class="lib-top"><a href="#" class="lib-burger" data-lib-open="true" aria-label="Search and filter"><span class="lib-burger-line"></span><span class="lib-burger-line"></span><span class="lib-burger-line"></span></a><div class="lib-count" data-blog-count="true">All {n:,} posts</div><div class="lib-pills" data-blog-pills="true"></div></div>
        <div class="blog-results" data-blog-results="true"></div>
        <div class="blog-empty" data-blog-empty="true">Nothing matches that yet. Try another word, or pick a topic.</div>
        <div class="blog-more-row"><a href="#browse" class="btn-outline" data-blog-more="true">Show more</a></div>
      </div>
    </div>
    <div class="blog-source" data-blog-source="true">{source}</div>
  </div>
</section>'''),
    ]


# ------------------------------------------------------------------ pages

def home():
    feat = cms_list([feature_card(w, 'feature', '<div>Featured essay</div>') for w in FEATURED])
    posts = cms_list([post_row(w) for w in REST[:4]], 'post-items', 'post-item')
    return [
        ('hero', f'''<header class="hero">
  <div class="hero-bg"></div>
  <div class="breath"><div class="breath-core"></div></div>
  <div class="wrap">
    <div class="hero-content">
      <div class="eyebrow-hero" data-reveal="0"><div class="eyebrow-line-light"></div><div>Healing Tao &middot; Meditation</div></div>
      <h1 class="hero-title" data-reveal="1">Welcome to the <span class="hero-em">present moment.</span></h1>
      <p class="hero-sub" data-reveal="2">Writings and guided practices on Taoist meditation, the nervous system, and living with calm energy in a restless modern world.</p>
      <div class="hero-cta" data-reveal="3"><a href="/blog" class="btn-primary">Read the blog</a><a href="/courses" class="btn-ghost">Explore the practices</a></div>
    </div>
  </div>
</header>'''),
        ('manifesto', '''<section class="sec">
  <div class="wrap">
    <div class="manifesto-grid">
      <blockquote class="manifesto-block" data-reveal="0"><div class="manifesto-quote">Taoist calm is not the absence of stress. It is the presence of <span class="manifesto-hl">coherence.</span></div></blockquote>
      <div data-reveal="1">
        <p class="para">Modern life trains the nervous system toward constant stimulation. Notifications, deadlines, and noise leave little room for stillness, and the body rarely returns to rest.</p>
        <p class="para">Taoism offers another way. By staying within the body and following the pattern of nature, we can rebuild a calmer relationship with attention, emotion, and daily rhythm.</p>
        <div class="manifesto-cite">The Tao Blog &middot; A systems-level orientation</div>
      </div>
    </div>
  </div>
</section>'''),
        ('writings', f'''<section class="sec">
  <div class="wrap">
    <div class="sec-head"><h2 class="sec-title" data-reveal="0">Recent writings on stillness and the body</h2><p class="sec-lede" data-reveal="1">Short essays bridging Taoist tradition and modern physiology, published from the practice.</p></div>
    <div class="writings-grid">
      {feat}
      <div class="post-list">{posts}<div class="btn-row" data-reveal="3"><a href="/blog" class="btn-outline">Browse the blog</a></div></div>
    </div>
  </div>
</section>'''),
        ('practices', '''<section class="sec-alt">
  <div class="wrap">
    <div class="sec-head"><h2 class="sec-title" data-reveal="0">Guided practices from Full Body Enlightenment</h2><p class="sec-lede" data-reveal="1">Video series that take the fundamentals off the page and into the body. One hour of content each.</p></div>
    <div class="row-list">''' + ''.join(f'''<div class="offer-row" data-reveal="{d}"><div><div class="offer-idx"><span class="offer-small">{n}</span> {t}</div></div><div><h3 class="offer-title">{t}</h3><p class="offer-text">{x}</p></div><div class="offer-side"><div class="offer-price">$15</div><div class="offer-unit">one hour of content</div><a href="{STORE[t]}" target="_blank" rel="noopener" class="btn-outline">Learn more</a></div></div>''' for n, t, x, d in [
            ('01', 'The Inner Smile', 'A practice for turning attention inward and expressing gratitude to the organs for the work they do all day, every day. The foundation everything else builds on.', '0'),
            ('02', 'The Six Healing Sounds', 'Breathing exercises focused on the major vital organs, releasing trapped heat, trapped cold, and stuck energy. An ancient technique taught in a variety of ways.', '1'),
            ('03', 'The Microcosmic Orbit', "An ancient Taoist exercise long kept from the general public. Circulate energy through the body's central channels to settle the mind and root the attention.", '2')]) + '''</div>
  </div>
</section>'''),
        ('trust', trust('3', 'Martial arts held to black belt')),
        ('about', f'''<section class="sec">
  <div class="wrap">
    <div class="about-grid">
      <div class="about-photo" data-reveal="0"><img src="{A('assets/img/taichi.jpg')}" alt="Andrew practicing tai chi in a green field" loading="lazy" class="about-img"/><div class="badge"><div class="badge-name">Andrew McCart, PhD</div><div class="badge-role">Senior Instructor, Healing Tao Association of the Americas</div></div></div>
      <div>
        <div class="eyebrow" data-reveal="0"><div class="eyebrow-line"></div><div>The teacher</div></div>
        <h2 class="about-title" data-reveal="1">Two decades of practice, taught in plain terms</h2>
        <p class="about-lead" data-reveal="1">Andrew has studied Taoism in depth for more than twenty years with numerous teachers, including twelve Healing Tao Senior Instructors across three continents.</p>
        <p class="para" data-reveal="2">He is a professor of Healthcare Leadership at the University of Louisville and holds a PhD in Public Health. His teaching keeps the work simple: stay within the body, connect to the organs, and breathe back and forth to the earth.</p>
        <ul role="list" class="ck" data-reveal="2">''' + ''.join(f'<li class="ck-item">{CHECK()}<div>{t}</div></li>' for t in ['Chi Nei Tsang and Medical Chi Kung', 'Reiki and Acupressure', 'Cosmic Healing Chi Kung', "Author of The Alchemist's Tao Te Ching"]) + '''</ul>
        <div class="btn-row-lg" data-reveal="3"><a href="/about" class="btn-outline">More about Andrew</a></div>
      </div>
    </div>
  </div>
</section>'''),
        ('voices', '''<section class="sec-alt">
  <div class="wrap">
    <div class="sec-head"><h2 class="sec-title" data-reveal="0">What students say</h2><p class="sec-lede" data-reveal="1">Notes from people who have sat, breathed, and practiced in Andrew's classes.</p></div>
    <div class="voices-grid">''' + voice_cards("Andrew's style lets students gain confidence, and it opens up interaction among classmates because no one worries about knowing the right answer. That confidence carries into every area of life, and the leadership shown here is contagious throughout our community.") + '''</div>
  </div>
</section>'''),
        ('cta', cta_band('Begin where you are', 'Questions about the practices, the courses, or where to start? Send a note and we will get back to you as soon as we can.', 'Get in touch', '/contact#contact')),
    ]


def writings_page():
    feat = cms_list([feature_card(w, 'feature-wide', '<div>Latest &middot;</div><div>' + fmt_date(w['published-on']) + '</div>') for w in FEATURED])
    lst = cms_list([idx_writing(w) for w in REST], 'index-list-from2', 'idx-cell')
    return [
        ('hero', page_hero('The blog', 'Writings', 'Short essays bridging Taoist tradition and modern physiology. New pieces are published from the practice.', 'Writings')),
        ('list', f'''<section class="sec">
  <div class="wrap">
    {feat}
    {lst}
  </div>
</section>'''),
    ]


def articles_page():
    lst = cms_list([idx_article(a) for a in ARTICLES], 'index-list', 'idx-cell')
    return [
        ('hero', page_hero('Long-form', 'Articles', 'Deeper pieces on stress, rest, and the practice of calm, gathered in one place.', 'Articles')),
        ('list', f'<section class="sec"><div class="wrap">{lst}</div></section>'),
        ('cta', cta_band('Prefer to practice?', 'Reading is a fine place to start. When you are ready to feel it in the body, the video series take you step by step.', 'See the courses', '/courses', alt=True)),
    ]


def courses_page():
    rows = ''.join(f'''<div class="offer-row" data-reveal="{d}"><div><div class="offer-idx"><span class="offer-small">{n}</span></div></div><div><h3 class="offer-title">{t}</h3><p class="offer-text">{x}</p></div><div class="offer-side"><div class="offer-price">$15</div><div class="offer-unit">one hour of content</div><a href="{STORE[t]}" target="_blank" rel="noopener" class="btn-outline">Learn more</a></div></div>''' for n, t, x, d in [
        ('01', 'The Inner Smile', 'The fundamental practice: turning attention inward and expressing gratitude to the organs for all they do all day, every day. Everything else builds on this.', '0'),
        ('02', 'The Six Healing Sounds', 'Breathing exercises focused on the major vital organs, releasing trapped heat, trapped cold, and stuck energy. Taught through moving and standing postures.', '1'),
        ('03', 'The Microcosmic Orbit', 'Connect the two major energy channels that run up the spine and down the center of the torso. Learn to circulate, balance, and safely store the energy.', '2')])
    return [
        ('hero', page_hero('Learn the practice', 'Courses', 'Video series, private lessons, and healing sessions. Ways to engage at any level of interest.', 'Courses')),
        ('series', f'''<section class="sec">
  <div class="wrap">
    <div class="sec-head"><h2 class="sec-title" data-reveal="0">Video series from Full Body Enlightenment</h2><p class="sec-lede" data-reveal="1">Each series is one hour of content and $15. Learn the fundamentals at your own pace.</p></div>
    <div class="row-list">{rows}</div>
  </div>
</section>'''),
        ('lessons', f'''<section class="sec-alt">
  <div class="wrap">
    <div class="sec-head"><h2 class="sec-title" data-reveal="0">Lessons and healing sessions</h2><p class="sec-lede" data-reveal="1">Prefer to work one to one, or in person? There are options for that too.</p></div>
    <div class="cards">
      <div class="card" data-reveal="0"><img src="{A('assets/img/meditation.jpg')}" alt="Andrew seated in meditation in white robes" loading="lazy" class="card-thumb"/><div class="card-kicker">Private lessons</div><h3 class="card-title">Tai Chi and Chi Kung</h3><p class="card-text">Learn practices or philosophy in a private setting. Andrew teaches individuals, small groups, and corporate parties chi kung, tai chi, meditation, or philosophy.</p><a href="/contact#contact" class="btn-outline">Ask about lessons</a></div>
      <div class="card" data-reveal="1"><img src="{A('assets/img/chineitsang.jpg')}" alt="Illustration of a Chi Nei Tsang abdominal healing session" loading="lazy" class="card-thumb"/><div class="card-kicker">Healing sessions</div><h3 class="card-title">Modalities and bodywork</h3><p class="card-text">Reiki, Chi Nei Tsang abdominal massage, Acupressure, and Cosmic Healing Chi Kung. Andrew is building case studies for Chi Nei Tsang, so ask about free treatments.</p><a href="/contact#contact" class="btn-outline">Enquire</a></div>
    </div>
  </div>
</section>'''),
        ('books', f'''<section class="sec">
  <div class="wrap">
    <div class="sec-head"><h2 class="sec-title" data-reveal="0">Books by Andrew McCart</h2><p class="sec-lede" data-reveal="1">Read at your own pace, on the page.</p></div>
    <div class="cards">
      <div class="card" data-reveal="0"><img src="{A('assets/img/book-taoteching.jpg')}" alt="Cover of The Alchemist's Tao Te Ching by Andrew L. McCart" loading="lazy" class="card-cover"/><div class="card-kicker">200 pages</div><h3 class="card-title">The Alchemist's Tao Te Ching</h3><p class="card-text">A fresh approach to the Tao Te Ching, focused on leadership, relationships, and finding peace in everyday life. Its 81 verses are paired with 81 practices and 81 haiku.</p><div class="card-price">$12</div></div>
      <div class="card" data-reveal="1"><img src="{A('assets/img/book-workforce.jpg')}" alt="Cover of Growing a Healthy Workforce by Andrew L. McCart" loading="lazy" class="card-cover"/><div class="card-kicker">Leadership</div><h3 class="card-title">Growing a Healthy Workforce</h3><p class="card-text">Leading in the eight dimensions of organizational wellness. Practical, la carte options and an overall plan for leaders working to reduce growing health related costs.</p><div class="card-price">Paperback</div></div>
    </div>
  </div>
</section>'''),
    ]


def events_page():
    tls = ''.join(f'<div class="tl"><div class="tl-dot"></div><div class="tl-yr">{y}</div><h4 class="tl-title">Taught by Andrew McCart</h4><p class="tl-text">{t}</p></div>' for y, t in [
        ('Summer 2017', 'Fusion 2 and 3 Macro-Orbit, Iron Shirt 2 and 3 Bone Marrow Washing, plus Tao Yin and Primordial Qigong.'),
        ('Summer 2016', 'Fusion of the Five Elements 1 with Iron Shirt 1 Rooting, and Fusion 2 and 3 Macro-Orbit with Iron Shirt 2 and 3.'),
        ('Summer 2015', 'Chinese Yoga Tao-Yin with the Inner Smile and Chi Self Massage, and Iron Shirt Qigong 2 and 3, Tendon and Bone Marrow Washing.'),
        ('Summer 2014', 'Chinese Yoga Tao-Yin, and Fusion 2 and 3 Macrocosmic Orbit with Iron Shirt 2 and 3.'),
        ('Summer 2013', 'Fusion of the Five Elements 1 and 2 with Iron Shirt 1, Tai Chi Chi Kung, and Chinese Yoga Tao-Yin.')])
    return [
        ('hero', page_hero('Workshops and retreats', 'Past Events', 'Private sessions, weekend workshops, and years of Healing Tao summer retreats.', 'Past Events')),
        ('online', '''<section class="sec">
  <div class="wrap">
    <div class="about-grid-top">
      <div data-reveal="0">
        <div class="eyebrow"><div class="eyebrow-line"></div><div>Online</div></div>
        <h2 class="side-title">Private and group video sessions</h2>
        <p class="para-muted">Private lessons on Zoom, Skype, Teams, or FaceTime can include conversation, consultation, question and answer, chi kung, inner alchemy, Taoist yoga, or Taoist meditation.</p>
      </div>
      <div class="card" data-reveal="1">
        <div class="card-kicker">Booking</div>
        <h3 class="card-title">How it works</h3>
        <p class="card-text">Best times are Saturday afternoon, Sunday morning, and weekday evenings. Payment can be exchanged over PayPal.</p>
        <p class="para-ink"><strong>$1 per minute</strong>, 30 minute minimum please.</p>
        <a href="/contact#contact" class="btn-primary">Request a session</a>
      </div>
    </div>
  </div>
</section>'''),
        ('workshops', f'''<section class="sec-alt">
  <div class="wrap">
    <div class="sec-head"><h2 class="sec-title" data-reveal="0">Weekend workshops</h2><p class="sec-lede" data-reveal="1">Held at the Purdue Technology Center, 3000 Technology Way, New Albany, IN 47150.</p></div>
    <div class="cards">
      <div class="card" data-reveal="0"><img src="{A('assets/img/events-meditation.jpg')}" alt="Healing Tao Basics meditation workshop flyer" loading="lazy" class="card-thumb"/><div class="card-kicker">Two-day intensive</div><h3 class="card-title">Healing Tao Basics</h3><p class="card-text">An overview of the Inner Smile, the Six Healing Sounds, the Microcosmic Orbit, and Basic Chi Kung. Learn to feel and move energy through the major organs of the body.</p><p class="para-ink"><strong>$88</strong> both days &middot; $50 for one day<br/><span class="small-muted">Saturday 12 to 6 PM, Sunday 9 to 1 PM</span></p><a href="/contact#contact" class="btn-outline">RSVP or ask</a></div>
      <div class="card" data-reveal="1"><img src="{A('assets/img/events-ironshirt.jpg')}" alt="Iron Shirt Chi Kung workshop flyer" loading="lazy" class="card-thumb"/><div class="card-kicker">Two-day intensive</div><h3 class="card-title">Iron Shirt Chi Kung</h3><p class="card-text">Standing practices that strengthen the fascia, root the feet into the earth, and align the spine. Later levels rejuvenate the tendons and open the bones and bone marrow.</p><p class="para-ink"><strong>$88</strong> both days &middot; $50 for one day<br/><span class="small-muted">Saturday 1 to 7 PM, Sunday 9 to 1 PM</span></p><a href="/contact#contact" class="btn-outline">RSVP or ask</a></div>
    </div>
  </div>
</section>'''),
        ('retreats', f'''<section class="sec">
  <div class="wrap">
    <div class="sec-head"><h2 class="sec-title" data-reveal="0">Healing Tao summer retreats</h2><p class="sec-lede" data-reveal="1">Andrew has taught at the Healing Tao USA summer retreats for many years alongside senior instructors.</p></div>
    <div class="timeline" data-reveal="0">{tls}</div>
  </div>
</section>'''),
    ]


def about_page():
    return [
        ('hero', page_hero('The teacher', 'About Andrew McCart', 'Twenty years of Taoist practice across three continents, taught in plain and simple terms.', 'About')),
        ('bio', f'''<section class="sec">
  <div class="wrap">
    <div class="about-grid">
      <div class="about-photo" data-reveal="0"><img src="{A('assets/img/taichi.jpg')}" alt="Andrew practicing tai chi in a green field" loading="lazy" class="about-img"/><div class="badge"><div class="badge-name">Andrew McCart, PhD</div><div class="badge-role">Senior Instructor, Healing Tao Association of the Americas</div></div></div>
      <div>
        <h2 class="about-title" data-reveal="0">A student, and a teacher</h2>
        <p class="about-lead" data-reveal="1">Over the last twenty years, Andrew has studied Taoism in depth with numerous teachers, including twelve Healing Tao Senior Instructors on three different continents.</p>
        <p class="para" data-reveal="1">He holds black belts in three martial arts and is a student of multiple healing modalities, including Chi Nei Tsang, Reiki, Acupressure, Cosmic Healing Chi Kung, and Medical Chi Kung. He is a professor of Healthcare Leadership and Health Administration at the University of Louisville and holds a PhD in Public Health.</p>
        <ul role="list" class="ck" data-reveal="2">''' + ''.join(f'<li class="ck-item">{CHECK()}<div>{t}</div></li>' for t in ['Senior Instructor, Healing Tao', 'PhD in Public Health', 'Black belts in three martial arts', 'Chi Nei Tsang and Cosmic Healing Chi Kung']) + '''</ul>
      </div>
    </div>
  </div>
</section>'''),
        ('quote', '''<section class="sec-alt">
  <div class="wrap">
    <div class="quote-stack">
      <blockquote class="manifesto-block-wide" data-reveal="0"><div class="manifesto-quote-lg">Stay within the body. <span class="manifesto-hl">Breathe back and forth to the earth.</span></div></blockquote>
      <div data-reveal="1"><p class="para">Andrew keeps the teaching simple. Connect to your organs and bones, ground deeply, and let awareness return to the present moment. The ancient Taoist masters meditated in secret, often in natural settings, hoping to find one willing student to carry the knowledge on.</p><p class="para">The invitation is the same today: learn what you like, and pass it on.</p></div>
    </div>
  </div>
</section>'''),
        ('trust', trust('2', 'Books published on Tao and leadership')),
        ('voices', '''<section class="sec">
  <div class="wrap">
    <div class="sec-head"><h2 class="sec-title" data-reveal="0">Testimonials from students</h2><p class="sec-lede" data-reveal="1">In their own words.</p></div>
    <div class="voices-grid">''' + voice_cards("Andrew's style lets students gain confidence, and it opens interaction among classmates because no one worries about knowing the right answer. That confidence carries into every area of life, and the leadership shown here is contagious throughout our community.") + '''</div>
  </div>
</section>'''),
    ]


FAQ = [
    ('I am just starting in meditation. What is the best advice for a beginner?', 'Keep it very simple. Stay within the body, connect to your organs and bones, and breathe back and forth to the earth through the bottoms of your feet. A few grounding exercises help settle any excess energy that feels new, strange, or uncomfortable at first.'),
    ('What time of day should I practice these meditations?', 'Use variety. If practicing at 9 pm wakes you at three in the morning, try the orbit during the day and the inner smile or healing sounds at night as you drift off. The best time to do it is when you actually do it.'),
    ('Can I practice in a lying down position?', 'Meditation is great lying down, especially drifting off to sleep. When you are learning a new technique it is easier sitting up, so you do not fall asleep before you learn it. Just before sleep, bone breathing and waking up the bone marrow is a wonderful practice.'),
    ('How should I end my meditation?', 'The navel and kidney massage is a great practice to keep energy out of the head and heart. It is recommended to store the energy in the navel when you finish a session.'),
    ('Can you tell me more about the Six Healing Sounds?', 'I like to keep it very simple. Perform each sound and exhalation three to six times, taking a break between each one to smile to that particular organ. An order that works well for me: lungs, kidneys, liver, heart, spleen, triple warmer.'),
    ('What is the essence of the Microcosmic Orbit practice?', 'Go point by point, starting at the navel and building awareness before moving to the next point. Warm the stove first by massaging the kidneys and navel, and afterward store the energy safely by spiraling it in the navel or kidneys.'),
    ('How do I balance star and planet energy in the orbit?', 'Balance it with at least as much grounding earth energy, or more. The more earth energy you absorb, the more star and planet energy you can actually hold. Grounding deep into the organs, bones, and tendons lets you receive far more, safely.'),
    ('Any tips for moving the energy upward?', 'First take the energy to the lower tan tien, where it can be stored safely and nourish the vital organs. The orbit will not circulate on its own if it is blocked, so gentle practice, and using the hands to massage the points, helps open the pathway.'),
]


def faq_page():
    qas = ''.join(f'''<div class="qa" data-reveal="0"><div class="qa-q" role="button" tabindex="0" aria-expanded="false"><div>{esc(q)}</div><div class="qa-ico"><img src="{A('assets/icons/plus.svg')}" alt="" class="qa-plus"/></div></div><div class="qa-a"><div class="qa-a-inner"><p class="para">{esc(a)}</p></div></div></div>''' for q, a in FAQ)
    return [
        ('hero', page_hero('Common questions', 'Frequently Asked Questions', 'Practical answers on getting started, timing, and the core practices. Keep it simple and stay in the body.', 'FAQ')),
        ('list', f'''<section class="sec">
  <div class="wrap">
    <div class="faq-list">{qas}</div>
    <div class="faq-foot" data-reveal="0"><p class="para-muted">Still curious? Andrew is happy to help you find a starting point.</p><a href="/contact#contact" class="btn-primary">Ask a question</a></div>
  </div>
</section>'''),
    ]


def contact_page():
    details = [('mail.svg', 'Email', '<a href="mailto:mccartandrew@gmail.com" class="detail-value">mccartandrew@gmail.com</a>', 'detail'),
               ('pin.svg', 'Workshops', '<div class="detail-value">Purdue Technology Center, New Albany, IN</div>', 'detail'),
               ('clock.svg', 'Private sessions', '<div class="detail-value">$1 per minute, 30 minute minimum, over PayPal</div>', 'detail'),
               ('frame.svg', 'Teaching', '<div class="detail-value">Healing Tao Association of the Americas</div>', 'detail-last')]
    drows = ''.join(f'<div class="{c}"><div class="detail-ic"><img src="{A("assets/icons/" + i)}" alt="" class="detail-icon"/></div><div><div class="detail-label">{l}</div>{v}</div></div>' for i, l, v, c in details)
    topics = ''.join(f'<option value="{t}">{t}</option>' for t in ['Getting started with meditation', 'Video series and courses', 'Private lessons', 'Healing sessions', 'Workshops and events', 'Something else'])
    return [
        ('hero', page_hero('Get in touch', 'Begin where you are', 'Questions about the practices, the courses, or where to start? Send a note and we will reply as soon as we can.', 'Contact')),
        ('contact', f'''<section id="contact" class="contact-sec" data-glide-on-load="true">
  <div class="wrap">
    <div class="contact-grid">
      <div>
        <div class="eyebrow" data-reveal="0"><div class="eyebrow-line"></div><div>Contact</div></div>
        <h2 class="side-title" data-reveal="1">We look forward to hearing from you</h2>
        <p class="contact-intro" data-reveal="1">Reach out about lessons, workshops, healing sessions, or simply where to begin.</p>
        <div data-reveal="2">{drows}</div>
      </div>
      <div class="form-block w-form">
        <form name="contact" data-name="Contact" method="get" class="contact-form">
          <div class="field-pair">
            <div class="field"><label for="name" class="form-label">Name</label><input id="name" name="name" type="text" placeholder="Your name" autocomplete="name" required class="form-input"/></div>
            <div class="field"><label for="email" class="form-label">Email</label><input id="email" name="email" type="email" placeholder="you@example.com" autocomplete="email" required class="form-input"/></div>
          </div>
          <div class="field"><label for="topic" class="form-label">I am interested in</label><select id="topic" name="topic" class="form-select">{topics}</select></div>
          <div class="field"><label for="message" class="form-label">Message</label><textarea id="message" name="message" placeholder="What would you like to know?" required class="form-textarea"></textarea></div>
          <input type="submit" value="Send message" class="btn-submit"/>
          <p class="form-note">We usually reply within a couple of days.</p>
        </form>
        <div class="form-done w-form-done"><div>Thank you. We look forward to hearing from you.</div></div>
        <div class="form-fail w-form-fail"><div>Something went wrong sending your message. Please try again, or email mccartandrew@gmail.com.</div></div>
      </div>
    </div>
  </div>
</section>'''),
    ]


def writing_item(w):
    cover = ''
    if w.get('cover-image'):
        cover = f'<img src="{A(w["cover-image"])}" alt="{esc(w.get("cover-alt") or "")}" class="post-cover"/>'
    else:
        cover = '<img src="" alt="" class="post-cover w-dyn-bind-empty"/>'
    return [
        ('hero', page_hero(f'<div class="meta-inline"><div>{esc(w["kind"])}</div><div>&middot;</div><div>{fmt_date(w["published-on"])}</div></div>', esc(w['name']), esc(w['excerpt']), '<a href="/blog" class="crumb-link">Blog</a>', 'post-hero-title')),
        ('article', f'''<section class="sec">
  <div class="wrap">
    <article class="post-article">
      {cover}
      {'' if SHELL else '<div class="post-body w-richtext">' + w['body'] + '</div>'}
      <div class="post-end">
        <div class="pause"><div class="pause-core"></div></div>
        <p class="pause-text">Pause here for a breath before you go on.</p>
        <div class="byline"><div class="avatar">AM</div><div><div class="byline-name">Andrew McCart, PhD</div><div class="byline-role">Senior Instructor, Healing Tao</div></div></div>
        <div class="post-topics" data-topics="{esc(', '.join(w.get('topics') or TOPICS_BY_SLUG.get(w['slug'], [])))}"></div>
        <a href="/blog" class="btn-outline">Back to the blog</a>
      </div>
    </article>
  </div>
</section>'''),
        ('cta', cta_band('Begin where you are', 'Questions about the practices, the courses, or where to start? Send a note and we will get back to you as soon as we can.', 'Get in touch', '/contact#contact', alt=True)),
    ]


def article_item(a):
    return [
        ('hero', page_hero(esc(a['kind']), esc(a['name']), esc(a['summary']), '<a href="/articles" class="crumb-link">Articles</a>', 'post-hero-title')),
        ('article', f'''<section class="sec">
  <div class="wrap">
    <div class="article-card">
      <div class="card-kicker">Long-form article</div>
      <h2 class="card-title">Read the full piece</h2>
      <p class="card-text">The complete article is a PDF. It opens in a new tab so you can read, save, or print it.</p>
      <a href="{A(a['pdf'])}" class="btn-primary" data-new-tab="true">Open the PDF</a>
    </div>
  </div>
</section>'''),
        ('cta', cta_band('Prefer to practice?', 'Reading is a fine place to start. When you are ready to feel it in the body, the video series take you step by step.', 'See the courses', '/courses', alt=True)),
    ]


PAGES = [
    # path, title, description, nav current, sections
    ('index.html', 'The Tao Blog &middot; Welcome to the Present Moment', 'Writings and guided practices on Taoist meditation, the nervous system, and calm energy in modern life. By Andrew McCart, Senior Instructor of the Healing Tao.', None, home),
    ('writings/index.html', 'Writings &middot; The Tao Blog', 'Short essays bridging Taoist tradition and modern physiology, by Andrew McCart.', '/writings', writings_page),
    ('blog/index.html', 'Blog &middot; The Tao Blog', 'Search nine years of reflections and essays on Taoist practice by Andrew McCart.', '/blog', blog_page),
    ('articles/index.html', 'Articles &middot; The Tao Blog', 'Deeper pieces on stress, rest, and the practice of calm, by Andrew McCart.', '/articles', articles_page),
    ('courses/index.html', 'Courses &middot; The Tao Blog', 'Video series, private lessons, and healing sessions with Andrew McCart.', '/courses', courses_page),
    ('events/index.html', 'Past Events &middot; The Tao Blog', 'Private sessions, weekend workshops, and Healing Tao summer retreats with Andrew McCart.', '/events', events_page),
    ('about/index.html', 'About &middot; The Tao Blog', 'Andrew McCart, PhD: twenty years of Taoist practice across three continents.', '/about', about_page),
    ('faq/index.html', 'FAQ &middot; The Tao Blog', 'Practical answers on getting started with Taoist meditation.', '/faq', faq_page),
    ('contact/index.html', 'Contact &middot; The Tao Blog', 'Get in touch with Andrew McCart about lessons, workshops, and healing sessions.', None, contact_page),
]


def doc(title, desc, current, body):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title}</title>
<meta name="description" content="{desc}"/>
<link rel="stylesheet" href="/webflow-base.css"/>
<link rel="stylesheet" href="/fonts.css"/>
<link rel="stylesheet" href="/tao.css"/>
<link rel="stylesheet" href="/tao-states.css"/>
<link rel="stylesheet" href="/tao-behavior.css"/>
<script src="/tao.js"></script>
</head>
<body>
<div class="page-body">
{site_header(current)}
{body}
{site_footer()}
</div>
</body>
</html>
'''


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w').write(text)


def main():
    if FRAGMENTS:
        if os.path.isdir(FRAG):
            shutil.rmtree(FRAG)
        for path, title, desc, current, fn in PAGES:
            key = path.split('/')[0].replace('.html', '')
            for i, (name, h) in enumerate(fn()):
                write(os.path.join(FRAG, key, f'{i:02d}-{name}.html'), h)
        write(os.path.join(FRAG, '_shared', 'site-header.html'), site_header())
        w0, a0 = (FEATURED or WRITINGS)[0], ARTICLES[0]
        write(os.path.join(FRAG, '_items', 'feature.html'), feature_card(w0, 'feature', '<div>Featured essay</div>'))
        write(os.path.join(FRAG, '_items', 'feature-wide.html'), feature_card(w0, 'feature-wide', '<div>Latest &middot;</div><div>' + fmt_date(w0['published-on']) + '</div>'))
        write(os.path.join(FRAG, '_items', 'post-row.html'), post_row(REST[0]))
        write(os.path.join(FRAG, '_items', 'idx-writing.html'), idx_writing(REST[0]))
        write(os.path.join(FRAG, '_items', 'idx-article.html'), idx_article(a0))
        write(os.path.join(FRAG, '_shared', 'site-footer.html'), site_footer())
        for i, (name, h) in enumerate(writing_item(WRITINGS[0])):
            write(os.path.join(FRAG, '_writing-template', f'{i:02d}-{name}.html'), h)
        for i, (name, h) in enumerate(article_item(ARTICLES[0])):
            write(os.path.join(FRAG, '_article-template', f'{i:02d}-{name}.html'), h)
        print('fragments ->', FRAG)
        return
    if os.path.isdir(SITE):
        shutil.rmtree(SITE)
    os.makedirs(SITE)
    for f in ['webflow-base.css', 'fonts.css', 'tao.css', 'tao-states.css', 'tao-behavior.css', 'tao.js']:
        shutil.copy(os.path.join(ROOT, f), SITE)
    os.symlink(os.path.join(ROOT, 'assets'), os.path.join(SITE, 'assets'))
    for path, title, desc, current, fn in PAGES:
        write(os.path.join(SITE, path), doc(title, desc, current, '\n'.join(h for _, h in fn())))
    for w in {w['slug']: w for w in WRITINGS + BLOG}.values():
        write(os.path.join(SITE, 'writings', w['slug'], 'index.html'),
              doc(f'{esc(w["name"])} &middot; The Tao Blog', esc(w['excerpt']), None, '\n'.join(h for _, h in writing_item(w))))
    for a in ARTICLES:
        write(os.path.join(SITE, 'articles', a['slug'], 'index.html'),
              doc(f'{esc(a["name"])} &middot; The Tao Blog', esc(a['summary']), None, '\n'.join(h for _, h in article_item(a))))
    print('site ->', SITE, '|', len(PAGES), 'pages,', len(WRITINGS), 'writings,', len(ARTICLES), 'articles')


if __name__ == '__main__':
    main()
