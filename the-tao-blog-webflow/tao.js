/* The Tao Blog -- site behavior. Hosted as a Webflow asset and registered by
   URL (never pasted through the API). Loads in the page <head>. */
(function () {
  var d = document, html = d.documentElement;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var hasVT = 'startViewTransition' in d;
  html.classList.add('js-ready');
  if (!hasVT) html.classList.add('no-vt');
  if (!reduce && 'IntersectionObserver' in window) html.classList.add('js-reveal');

  function ready(fn) { if (d.readyState !== 'loading') fn(); else d.addEventListener('DOMContentLoaded', fn); }
  function each(sel, fn) { Array.prototype.forEach.call(d.querySelectorAll(sel), fn); }
  function pressable(el, fn) {
    el.addEventListener('click', function (e) { e.preventDefault(); fn(); });
    el.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fn(); }
    });
  }

  // ---------- Blog page. Every post sits in hidden CMS lists ([data-blog-source]); this reads them and runs
  // the side menu (search, topics, years, type, order) and the daily strip. ----------
  function blog() {
    var source = d.querySelector('[data-blog-source]'), results = d.querySelector('[data-blog-results]');
    if (!source || !results) return;
    var PAGE = 24, MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    var $ = function (sel) { return d.querySelector(sel); };
    var smooth = reduce ? 'auto' : 'smooth';
    function fold(s) {
      return (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[’']/g, '').replace(/[^a-z0-9]+/g, ' ').trim();
    }
    function parseDate(s) {
      var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s || '');
      if (m) return new Date(+m[1], +m[2] - 1, +m[3]);
      var t = Date.parse(s); return isNaN(t) ? new Date(0) : new Date(t);
    }
    function longDate(dt) { return MONTHS[dt.getMonth()] + ' ' + dt.getDate() + ', ' + dt.getFullYear(); }
    function text(el, sel) { var x = el.querySelector(sel); return x ? x.textContent.trim() : ''; }
    function plural(n, one, many) { return n.toLocaleString() + ' ' + (n === 1 ? one : many); }

    var posts = Array.prototype.map.call(source.querySelectorAll('.bcard'), function (el) {
      var img = el.querySelector('.bcard-img'), title = text(el, '.bcard-title'), ex = text(el, '.bcard-excerpt');
      var topics = ['data-topic1', 'data-topic2', 'data-topic3'].map(function (k) { return (el.getAttribute(k) || '').trim(); }).filter(Boolean);
      var date = parseDate(el.getAttribute('data-date'));
      return { el: el, title: title, excerpt: ex, topics: topics, kind: el.getAttribute('data-kind') || '', date: date,
               year: String(date.getFullYear()), href: el.getAttribute('href'),
               img: img && img.getAttribute('src') && !img.classList.contains('w-dyn-bind-empty') ? img.getAttribute('src') : '',
               hay: ' ' + fold(title + ' ' + ex + ' ' + topics.join(' ')), hayTitle: ' ' + fold(title) };
    });
    if (!posts.length) return;

    var qs = new URLSearchParams(location.search);
    var st = { q: qs.get('q') || '', topic: qs.get('topic') || '', kind: qs.get('kind') || '', year: qs.get('year') || '',
               sort: qs.get('sort') === 'oldest' ? 'oldest' : 'newest', shown: PAGE };
    var input = $('[data-blog-search]'), browse = $('#browse'), side = $('[data-lib-side]'), scrim = $('.lib-scrim');
    var countEl = $('[data-blog-count]'), pillsEl = $('[data-blog-pills]'), clearEl = $('[data-blog-clear]');
    var moreEl = $('[data-blog-more]'), emptyEl = $('[data-blog-empty]');
    if (input) input.value = st.q;

    function words() { return st.q ? fold(st.q).split(' ').filter(Boolean) : []; }
    function filtered() { return !!(st.q || st.topic || st.kind || st.year); }
    function matches(p, ignore) {
      if (st.kind && ignore !== 'kind' && p.kind !== st.kind) return false;
      if (st.topic && ignore !== 'topic' && p.topics.indexOf(st.topic) < 0) return false;
      if (st.year && ignore !== 'year' && p.year !== st.year) return false;
      var w = words();
      for (var i = 0; i < w.length; i++) if (p.hay.indexOf(' ' + w[i]) < 0) return false;   // word-prefix match
      return true;
    }
    function list() {
      var w = words(), out = posts.filter(function (p) { return matches(p); }), dir = st.sort === 'oldest' ? 1 : -1;
      out.sort(function (a, b) {
        if (w.length) {
          var sa = 0, sb = 0;
          w.forEach(function (x) { sa += a.hayTitle.indexOf(' ' + x) >= 0 ? 1 : 0; sb += b.hayTitle.indexOf(' ' + x) >= 0 ? 1 : 0; });
          if (sa !== sb) return sb - sa;                    // title hits first
        }
        return dir * (a.date - b.date);
      });
      return out;
    }
    function highlight(el) {
      var w = words(), t = el.querySelector('.bcard-title'); if (!w.length || !t) return;
      var parts = t.textContent.split(/(\s+)/); t.textContent = '';
      parts.forEach(function (part) {
        var f = fold(part), hit = f && w.some(function (x) { return f.indexOf(x) === 0; });
        if (hit) { var m = d.createElement('mark'); m.className = 'blog-hit'; m.textContent = part; t.appendChild(m); }
        else t.appendChild(d.createTextNode(part));
      });
    }

    var cols = [], current = [], placed = 0;
    function colCount() { var w = results.clientWidth || innerWidth; return w >= 820 ? 3 : w >= 500 ? 2 : 1; }
    function place(upto) {
      for (; placed < Math.min(upto, current.length); placed++) {
        var c = current[placed].el.cloneNode(true); highlight(c); cols[placed % cols.length].appendChild(c);
      }
    }
    function pill(label, key) {
      var a = d.createElement('a'); a.className = 'lib-pill'; a.href = '#'; a.setAttribute('aria-label', 'Remove ' + label);
      a.appendChild(d.createTextNode(label)); var x = d.createElement('span'); x.textContent = '×'; a.appendChild(x);
      a.addEventListener('click', function (e) { e.preventDefault(); if (key === 'q' && input) input.value = ''; set(key, ''); });
      return a;
    }

    // A post from a year the menu has no bar for (2027 and on) gets a bar automatically.
    var yearsDone = false;
    function ensureYears() {
      if (yearsDone) return; yearsDone = true;
      var box = $('.blog-years'), proto = box && box.querySelector('.blog-year'); if (!proto) return;
      var have = {}; each('.blog-year[data-year]', function (a) { have[a.getAttribute('data-year')] = 1; });
      Object.keys(posts.reduce(function (m, p) { m[p.year] = 1; return m; }, {})).sort().forEach(function (y) {
        if (have[y] || !/^\d{4}$/.test(y)) return;
        var a = proto.cloneNode(true); a.setAttribute('data-year', y); a.href = '/blog?year=' + y; a.classList.remove('is-on');
        var l = a.querySelector('.blog-year-label'); if (l) l.textContent = '\u2019' + y.slice(2);
        a.addEventListener('click', function (e) { e.preventDefault(); set('year', st.year === y ? '' : y); if (small()) drawer(false); });
        box.appendChild(a);
      });
    }

    function render(append) {
      if (!append) {
        current = list(); placed = 0; results.textContent = ''; cols = [];
        for (var c = 0, n = colCount(); c < n; c++) { var col = d.createElement('div'); col.className = 'blog-col'; results.appendChild(col); cols.push(col); }
      }
      place(st.shown);
      var noun = st.kind === 'Essay' ? ['essay', 'essays'] : st.kind === 'Reflection' ? ['reflection', 'reflections'] : ['post', 'posts'];
      var isF = filtered();
      if (countEl) countEl.textContent = (current.length > placed ? 'Showing ' + placed.toLocaleString() + ' of ' : '') + plural(current.length, noun[0], noun[1]);
      if (pillsEl) {
        pillsEl.textContent = '';
        if (st.q) pillsEl.appendChild(pill('“' + st.q.trim() + '”', 'q'));
        if (st.topic) pillsEl.appendChild(pill(st.topic, 'topic'));
        if (st.year) pillsEl.appendChild(pill(st.year, 'year'));
        if (st.kind) pillsEl.appendChild(pill(st.kind === 'Essay' ? 'Essays' : 'Reflections', 'kind'));
      }
      if (clearEl) clearEl.classList.toggle('is-on', isF);
      if (moreEl) moreEl.parentNode.style.display = placed < current.length ? '' : 'none';
      if (emptyEl) emptyEl.classList.toggle('is-on', !current.length);

      // counts and "on" states in the side menu
      each('.side-item[data-topic]', function (a) {
        var t = a.getAttribute('data-topic'), n = 0;
        posts.forEach(function (p) { if (p.topics.indexOf(t) >= 0 && matches(p, 'topic')) n++; });
        a.classList.toggle('is-on', st.topic === t); var nEl = a.querySelector('.side-n'); if (nEl) nEl.textContent = n.toLocaleString();
      });
      each('.side-item[data-kind]', function (a) {
        var k = a.getAttribute('data-kind'), n = 0; if (k === 'all') k = '';
        posts.forEach(function (p) { if ((!k || p.kind === k) && matches(p, 'kind')) n++; });
        a.classList.toggle('is-on', st.kind === k); var nEl = a.querySelector('.side-n'); if (nEl) nEl.textContent = n.toLocaleString();
      });
      each('.side-item[data-sort]', function (a) { a.classList.toggle('is-on', a.getAttribute('data-sort') === st.sort); });
      ensureYears();
      var yc = {}, max = 1;
      posts.forEach(function (p) { if (matches(p, 'year')) { yc[p.year] = (yc[p.year] || 0) + 1; max = Math.max(max, yc[p.year]); } });
      each('.blog-year[data-year]', function (a) {
        var y = a.getAttribute('data-year'), n = yc[y] || 0, bar = a.querySelector('.blog-year-bar');
        if (bar) bar.style.height = Math.max(3, Math.round(30 * n / max)) + 'px';
        a.classList.toggle('is-on', st.year === y);
        a.setAttribute('aria-label', y + ': ' + plural(n, 'post', 'posts')); a.title = y + ': ' + plural(n, 'post', 'posts');
      });


      var p = new URLSearchParams();
      ['q', 'topic', 'kind', 'year'].forEach(function (k) { if (st[k]) p.set(k, st[k].trim()); });
      if (st.sort === 'oldest') p.set('sort', 'oldest');
      history.replaceState(null, '', location.pathname + (p.toString() ? '?' + p.toString() : '') + location.hash);
    }
    function toTop() {
      if (browse && browse.getBoundingClientRect().top < 0) browse.scrollIntoView({ behavior: smooth, block: 'start' });
    }
    function set(k, v, scroll) {
      var before = filtered();
      st[k] = v; st.shown = PAGE; render();
      if (scroll || (!before && filtered())) browse && browse.scrollIntoView({ behavior: smooth, block: 'start' });
      else toTop();
    }

    // ----- side menu: drawer on small screens, folding groups, search, items
    function drawer(open) {
      if (!side) return;
      side.classList.toggle('is-open', open); if (scrim) scrim.classList.toggle('is-open', open);
      if (open && input) setTimeout(function () { input.focus(); }, 300);
    }
    each('[data-lib-open]', function (a) { a.addEventListener('click', function (e) { e.preventDefault(); drawer(true); }); });
    each('[data-lib-close]', function (a) { a.addEventListener('click', function (e) { e.preventDefault(); drawer(false); }); });
    d.addEventListener('keydown', function (e) { if (e.key === 'Escape') drawer(false); });
    var small = function () { return innerWidth < 992; };
    each('.side-head', function (h) {
      h.addEventListener('click', function (e) {
        e.preventDefault(); var g = h.closest('.side-group'), closed = g.classList.toggle('is-closed');
        h.setAttribute('aria-expanded', closed ? 'false' : 'true');
      });
    });
    var timer;
    if (input) {
      input.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(function () { set('q', input.value); }, 160); });
      input.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); clearTimeout(timer); set('q', input.value, true); if (small()) drawer(false); } });
      d.addEventListener('keydown', function (e) {
        var tag = (e.target.tagName || '').toLowerCase();
        if (e.key === '/' && tag !== 'input' && tag !== 'textarea' && !e.target.isContentEditable) {
          e.preventDefault(); if (small()) drawer(true); else { browse && browse.scrollIntoView({ behavior: smooth, block: 'start' }); input.focus(); }
        }
      });
    }
    each('.side-item[data-topic]', function (a) { a.addEventListener('click', function (e) { e.preventDefault(); var t = a.getAttribute('data-topic'); set('topic', st.topic === t ? '' : t); if (small()) drawer(false); }); });
    each('.side-item[data-kind]', function (a) { a.addEventListener('click', function (e) { e.preventDefault(); var k = a.getAttribute('data-kind'); set('kind', k === 'all' ? '' : k); if (small()) drawer(false); }); });
    each('.side-item[data-sort]', function (a) { a.addEventListener('click', function (e) { e.preventDefault(); set('sort', a.getAttribute('data-sort')); if (small()) drawer(false); }); });
    each('.blog-year[data-year]', function (a) { a.addEventListener('click', function (e) { e.preventDefault(); var y = a.getAttribute('data-year'); set('year', st.year === y ? '' : y); if (small()) drawer(false); }); });
    if (clearEl) clearEl.addEventListener('click', function (e) { e.preventDefault(); st.q = st.topic = st.kind = st.year = ''; if (input) input.value = ''; st.shown = PAGE; render(); if (small()) drawer(false); });
    if (moreEl) moreEl.addEventListener('click', function (e) { e.preventDefault(); st.shown += PAGE; render(true); });
    var lastCols = 0;
    window.addEventListener('resize', function () { var n = colCount(); if (n !== lastCols) { lastCols = n; render(); } });

    // ----- one for right now: a random image-led reflection; "Another one" draws again
    var pick = $('[data-blog-pick]');
    if (pick) {
      var pool = posts.filter(function (p) { return p.img && p.kind === 'Reflection'; }), last = -1;
      if (pool.length < 2) pool = posts.filter(function (p) { return p.img; });   // until the short image posts are imported
      var show = function (first) {
        if (!pool.length) return;
        var i; do { i = Math.floor(Math.random() * pool.length); } while (pool.length > 1 && i === last);
        last = i; var p = pool[i];
        var apply = function () {
          var im = pick.querySelector('.blog-pick-img'); if (im) { im.src = p.img; im.alt = ''; }
          var dt = pick.querySelector('.blog-pick-date'); if (dt) dt.textContent = longDate(p.date);
          var ti = pick.querySelector('.blog-pick-title'); if (ti) { ti.textContent = p.title; if (ti.tagName === 'A') ti.href = p.href; }
          var tx = pick.querySelector('.blog-pick-text'); if (tx) tx.textContent = p.excerpt;
          pick.classList.remove('is-swapping');
        };
        if (first || reduce) apply(); else { pick.classList.add('is-swapping'); setTimeout(apply, 320); }
      };
      var again = pick.querySelector('.blog-again');
      if (again) again.addEventListener('click', function (e) { e.preventDefault(); show(false); });
      show(true);
    }

    lastCols = colCount();
    render();
  }

  ready(function () {
    var nav = d.querySelector('.nav');
    if (nav) {
      var lightTop = !!d.querySelector('[data-nav="light"]');     // pages whose header is light, not a dark photo
      var onScroll = function () { nav.classList.toggle('scrolled', lightTop || window.scrollY > 40); };
      onScroll(); window.addEventListener('scroll', onScroll, { passive: true });
    }

    var burger = d.querySelector('.burger'), menu = d.querySelector('.mobile-menu');
    if (burger && menu) {
      pressable(burger, function () {
        var open = menu.classList.toggle('open');
        burger.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
      each('.mobile-menu a', function (a) {
        a.addEventListener('click', function () { menu.classList.remove('open'); burger.setAttribute('aria-expanded', 'false'); });
      });
    }

    each('.qa-q', function (q) {
      pressable(q, function () {
        var qa = q.closest('.qa'); var open = qa.classList.toggle('open');
        q.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
    });

    each('[data-new-tab]', function (a) { a.setAttribute('target', '_blank'); a.setAttribute('rel', 'noopener'); });

    // CMS cards carry their post's slug (bound in Webflow); the MCP cannot set a
    // "current item" link, so the card's href is built from it here.
    each('a[data-slug]', function (a) { if (a.dataset.slug) a.setAttribute('href', '/writings/' + a.dataset.slug); });

    if (!hasVT) {
      d.addEventListener('click', function (e) {
        var a = e.target.closest && e.target.closest('a'); if (!a) return;
        var href = a.getAttribute('href');
        if (!href || href.charAt(0) === '#' || a.target === '_blank' || /^(mailto:|tel:|https?:)/i.test(href) || e.metaKey || e.ctrlKey) return;
        e.preventDefault();
        if (reduce) { window.location.href = href; return; }
        d.body.classList.add('is-leaving');
        setTimeout(function () { window.location.href = href; }, 320);
      });
      window.addEventListener('pageshow', function () { d.body.classList.remove('is-leaving'); });
    }

    // Contact page: on every visit, glide from the top down to the form, once.
    var glide = d.querySelector('[data-glide-on-load]');
    if (glide) {
      var glided = false;
      var go = function () {
        if (glided) return; glided = true;
        window.scrollTo({ top: 0, behavior: 'instant' });
        requestAnimationFrame(function () { glide.scrollIntoView({ behavior: 'smooth', block: 'start' }); });
      };
      if (d.readyState === 'complete') requestAnimationFrame(function () { requestAnimationFrame(go); });
      else window.addEventListener('load', function () { requestAnimationFrame(function () { requestAnimationFrame(go); }); });
      window.addEventListener('pagereveal', function () { requestAnimationFrame(go); });
      window.addEventListener('pageshow', function (e) { if (e.persisted) { glided = false; go(); } });
    }

    blog();

    // Post pages: the Topic fields arrive as hidden carriers; turn each into a "More on ..." link
    each('.post-topics', function (box) {
      Array.prototype.forEach.call(box.querySelectorAll('.post-topic-src'), function (src) {
        var name = src.textContent.trim();
        if (name && !src.classList.contains('w-dyn-bind-empty')) {
          var a = d.createElement('a'); a.className = 'post-topic';
          a.href = '/blog?topic=' + encodeURIComponent(name); a.textContent = 'More on ' + name;
          box.appendChild(a);
        }
      });
    });

    var reveals = d.querySelectorAll('[data-reveal]');
    if (!html.classList.contains('js-reveal')) {
      Array.prototype.forEach.call(reveals, function (el) { el.classList.add('in'); });
    } else {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); } });
      }, { threshold: 0.14, rootMargin: '0px 0px -8% 0px' });
      Array.prototype.forEach.call(reveals, function (el) { io.observe(el); });
    }
  });
})();
