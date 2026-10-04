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

  // ---------- Blog page: every post sits in hidden CMS lists ([data-blog-source]); this reads them
  // and runs search, topics, years, sorting, "today in past years" and "one for right now". ----------
  function blog() {
    var source = d.querySelector('[data-blog-source]'), results = d.querySelector('[data-blog-results]');
    if (!source || !results) return;
    var PAGE = 24, MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    var $ = function (sel) { return d.querySelector(sel); };
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

    var posts = Array.prototype.map.call(source.querySelectorAll('.bcard'), function (el) {
      var img = el.querySelector('.bcard-img'), title = text(el, '.bcard-title'), ex = text(el, '.bcard-excerpt');
      var topics = (el.getAttribute('data-topics') || '').split(',').map(function (t) { return t.trim(); }).filter(Boolean);
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
    var input = $('[data-blog-search]'), now = $('.blog-now'), nowSec = now && now.closest('section');
    var browse = $('#browse'), countEl = $('[data-blog-count]'), clearEl = $('[data-blog-clear]');
    var moreEl = $('[data-blog-more]'), emptyEl = $('[data-blog-empty]'), sortEl = $('[data-blog-sort]');
    if (input) input.value = st.q;

    function words() { return st.q ? fold(st.q).split(' ').filter(Boolean) : []; }
    function matches(p, ignore) {
      if (st.kind && ignore !== 'kind' && p.kind !== st.kind) return false;
      if (st.topic && ignore !== 'topic' && p.topics.indexOf(st.topic) < 0) return false;
      if (st.year && ignore !== 'year' && p.year !== st.year) return false;
      var w = words();
      for (var i = 0; i < w.length; i++) if (p.hay.indexOf(' ' + w[i]) < 0) return false;   // word-prefix match
      return true;
    }
    function list() {
      var w = words(), out = posts.filter(function (p) { return matches(p); });
      var dir = st.sort === 'oldest' ? 1 : -1;
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
    function colCount() { return innerWidth >= 992 ? 3 : innerWidth >= 600 ? 2 : 1; }
    function place(upto) {
      for (; placed < Math.min(upto, current.length); placed++) {
        var c = current[placed].el.cloneNode(true);
        highlight(c);
        cols[placed % cols.length].appendChild(c);
      }
    }
    function plural(n, one, many) { return n.toLocaleString() + ' ' + (n === 1 ? one : many); }
    function render(append) {
      if (!append) {
        current = list(); placed = 0; results.textContent = ''; cols = [];
        for (var c = 0, n = colCount(); c < n; c++) { var col = d.createElement('div'); col.className = 'blog-col'; results.appendChild(col); cols.push(col); }
      }
      place(st.shown);
      var noun = st.kind === 'Essay' ? ['essay', 'essays'] : st.kind === 'Reflection' ? ['reflection', 'reflections'] : ['post', 'posts'];
      var bits = [plural(current.length, noun[0], noun[1])];
      if (st.topic) bits.push('on ' + st.topic);
      if (st.year) bits.push('from ' + st.year);
      if (st.q) bits.push('matching “' + st.q.trim() + '”');
      if (countEl) countEl.textContent = (current.length > placed ? 'Showing ' + placed.toLocaleString() + ' of ' : '') + bits.join(' ');
      var filtered = !!(st.q || st.topic || st.kind || st.year);
      if (clearEl) clearEl.style.display = filtered ? '' : 'none';
      if (moreEl) moreEl.parentNode.style.display = placed < current.length ? '' : 'none';
      if (emptyEl) emptyEl.classList.toggle('is-on', !current.length);
      if (nowSec) nowSec.style.display = st.q || st.topic ? 'none' : '';
      if (browse) browse.classList.toggle('is-filtered', !!(st.q || st.topic));
      if (sortEl) { sortEl.textContent = st.sort === 'oldest' ? 'Oldest first' : 'Newest first'; sortEl.href = '/blog?sort=' + (st.sort === 'oldest' ? 'newest' : 'oldest'); }
      each('.blog-chip[data-topic]', function (a) {
        var t = a.getAttribute('data-topic'), n = 0;
        posts.forEach(function (p) { if (p.topics.indexOf(t) >= 0 && matches(p, 'topic')) n++; });
        a.classList.toggle('is-on', st.topic === t);
        var nEl = a.querySelector('.blog-chip-n'); if (nEl) nEl.textContent = n;
      });
      var yc = {}, max = 1;
      posts.forEach(function (p) { if (matches(p, 'year')) { yc[p.year] = (yc[p.year] || 0) + 1; max = Math.max(max, yc[p.year]); } });
      each('.blog-year[data-year]', function (a) {
        var y = a.getAttribute('data-year'), n = yc[y] || 0, bar = a.querySelector('.blog-year-bar');
        if (bar) bar.style.height = Math.max(3, Math.round(30 * n / max)) + 'px';
        a.classList.toggle('is-on', st.year === y);
        a.setAttribute('aria-label', y + ': ' + plural(n, 'post', 'posts'));
        a.title = y + ': ' + plural(n, 'post', 'posts');
      });
      each('.blog-seg-btn', function (a) { a.classList.toggle('is-on', (a.getAttribute('data-kind') || '') === st.kind); });
      var p = new URLSearchParams();
      ['q', 'topic', 'kind', 'year'].forEach(function (k) { if (st[k]) p.set(k, st[k].trim()); });
      if (st.sort === 'oldest') p.set('sort', 'oldest');
      history.replaceState(null, '', location.pathname + (p.toString() ? '?' + p.toString() : '') + location.hash);
    }
    function toResults() {
      if (browse && results.getBoundingClientRect().top < 80) browse.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
    }
    function set(k, v, scroll) {
      st[k] = v; st.shown = PAGE; render();
      if (scroll && browse) browse.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
      else toResults();
    }

    var timer;
    if (input) {
      input.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(function () { st.q = input.value; st.shown = PAGE; render(); }, 140); });
      input.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); clearTimeout(timer); st.q = input.value; st.shown = PAGE; render(); browse && browse.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth' }); } });
      var box = input.closest('.blog-search'); if (box) box.addEventListener('click', function () { input.focus(); });
      d.addEventListener('keydown', function (e) {
        var tag = (e.target.tagName || '').toLowerCase();
        if (e.key === '/' && tag !== 'input' && tag !== 'textarea' && !e.target.isContentEditable) { e.preventDefault(); input.focus(); }
      });
    }
    each('.blog-chip[data-topic]', function (a) { a.addEventListener('click', function (e) { e.preventDefault(); var t = a.getAttribute('data-topic'); set('topic', st.topic === t ? '' : t, true); }); });
    each('.blog-year[data-year]', function (a) { a.addEventListener('click', function (e) { e.preventDefault(); var y = a.getAttribute('data-year'); set('year', st.year === y ? '' : y); }); });
    each('.blog-seg-btn', function (a) { a.addEventListener('click', function (e) { e.preventDefault(); set('kind', a.getAttribute('data-kind') || ''); }); });
    if (sortEl) sortEl.addEventListener('click', function (e) { e.preventDefault(); set('sort', st.sort === 'oldest' ? 'newest' : 'oldest'); });
    if (clearEl) clearEl.addEventListener('click', function (e) { e.preventDefault(); st.q = st.topic = st.kind = st.year = ''; if (input) input.value = ''; st.shown = PAGE; render(); });
    if (moreEl) moreEl.addEventListener('click', function (e) { e.preventDefault(); st.shown += PAGE; render(true); });
    var lastCols = colCount();
    window.addEventListener('resize', function () { var n = colCount(); if (n !== lastCols) { lastCols = n; render(); } });
    render();

    // Today in past years (widens to this week when the exact date is quiet)
    var todayBox = $('[data-blog-today]');
    if (todayBox) {
      var t0 = new Date(), m = t0.getMonth(), dd = t0.getDate(), label = $('[data-blog-today-label]');
      var past = posts.filter(function (p) { return p.date.getFullYear() < t0.getFullYear(); });
      var hits = past.filter(function (p) { return p.date.getMonth() === m && p.date.getDate() === dd; }), head = MONTHS[m] + ' ' + dd + ' in past years';
      if (hits.length < 2) {
        hits = past.filter(function (p) { return Math.abs(new Date(t0.getFullYear(), p.date.getMonth(), p.date.getDate()) - new Date(t0.getFullYear(), m, dd)) <= 3 * 864e5; });
        head = 'This week in past years';
      }
      var byYear = {};
      hits.sort(function (a, b) { return b.date - a.date; }).forEach(function (p) { if (!byYear[p.year]) byYear[p.year] = p; });
      var picks = Object.keys(byYear).sort().reverse().slice(0, 6).map(function (y) { return byYear[y]; });
      if (picks.length) {
        if (label) label.textContent = head;
        todayBox.textContent = '';
        picks.forEach(function (p) {
          var a = d.createElement('a'); a.className = 'blog-mini'; a.href = p.href;
          var im = d.createElement(p.img ? 'img' : 'div'); im.className = 'blog-mini-img';
          if (p.img) { im.src = p.img; im.alt = ''; im.loading = 'lazy'; }
          var b = d.createElement('span'), y = d.createElement('span'), tt = d.createElement('span');
          y.className = 'blog-mini-year'; y.textContent = p.year; tt.className = 'blog-mini-title'; tt.textContent = p.title;
          b.appendChild(y); b.appendChild(tt); a.appendChild(im); a.appendChild(b); todayBox.appendChild(a);
        });
      }
    }

    // One for right now: a random image-led reflection; "Another one" draws again
    var pick = $('[data-blog-pick]');
    if (pick) {
      var pool = posts.filter(function (p) { return p.img && p.kind === 'Reflection'; }), last = -1;
      var show = function (first) {
        if (!pool.length) return;
        var i; do { i = Math.floor(Math.random() * pool.length); } while (pool.length > 1 && i === last);
        last = i; var p = pool[i];
        var apply = function () {
          var im = pick.querySelector('.blog-pick-img'); if (im) { im.src = p.img; im.alt = ''; }
          var dt = pick.querySelector('.blog-pick-date'); if (dt) dt.textContent = longDate(p.date);
          var ti = pick.querySelector('.blog-pick-title'); if (ti) ti.textContent = p.title;
          var tx = pick.querySelector('.blog-pick-text'); if (tx) tx.textContent = p.excerpt;
          var go = pick.querySelector('.btn-primary'); if (go) go.href = p.href;
          pick.classList.remove('is-swapping');
        };
        if (first || reduce) apply(); else { pick.classList.add('is-swapping'); setTimeout(apply, 320); }
      };
      var again = pick.querySelector('.blog-again');
      if (again) again.addEventListener('click', function (e) { e.preventDefault(); show(false); });
      show(true);
    }
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

    each('.post-topics[data-topics]', function (box) {
      box.getAttribute('data-topics').split(',').forEach(function (name) {
        name = name.trim(); if (!name) return;
        var a = d.createElement('a'); a.className = 'post-topic';
        a.href = '/blog?topic=' + encodeURIComponent(name); a.textContent = 'More on ' + name;
        box.appendChild(a);
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
