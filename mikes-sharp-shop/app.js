// Mike's Sharp Shop - shared behavior

// Nav: solid graphite on scroll (IntersectionObserver sentinel, no scroll listener)
(function () {
  var nav = document.getElementById('nav');
  if (!nav) return;
  var sentinel = document.createElement('div');
  sentinel.style.cssText = 'position:absolute;top:0;height:70px;width:1px;pointer-events:none;';
  document.body.prepend(sentinel);
  new IntersectionObserver(function (entries) {
    nav.classList.toggle('scrolled', !entries[0].isIntersecting);
  }, { threshold: 0 }).observe(sentinel);
})();

// Scroll reveal
(function () {
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
  }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
  document.querySelectorAll('.reveal').forEach(function (el) { io.observe(el); });
})();

// Mobile drawer
(function () {
  var drawer = document.getElementById('drawer');
  var open = document.getElementById('openMenu');
  var close = document.getElementById('closeMenu');
  if (!drawer || !open) return;
  function setOpen(state) {
    drawer.classList.toggle('open', state);
    drawer.setAttribute('aria-hidden', String(!state));
    document.body.style.overflow = state ? 'hidden' : '';
  }
  open.addEventListener('click', function () { setOpen(true); });
  if (close) close.addEventListener('click', function () { setOpen(false); });
  drawer.querySelectorAll('a').forEach(function (a) { a.addEventListener('click', function () { setOpen(false); }); });
})();

// Cross-page fade fallback (only for browsers without native View Transitions).
// Modern browsers use the CSS @view-transition crossfade; this fades to the
// page background color, never white.
(function () {
  if ('startViewTransition' in document) return;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.addEventListener('click', function (e) {
    var a = e.target.closest('a');
    if (!a) return;
    var href = a.getAttribute('href');
    if (!href || href.charAt(0) === '#' || a.target === '_blank' || /^(mailto:|tel:|https?:)/i.test(href)) return;
    e.preventDefault();
    if (reduce) { window.location.href = href; return; }
    document.body.classList.add('is-leaving');
    setTimeout(function () { window.location.href = href; }, 320);
  });
  window.addEventListener('pageshow', function () { document.body.classList.remove('is-leaving'); });
})();

// Demo form handler (no backend wired yet)
function handleSubmit(e) {
  e.preventDefault();
  var btn = e.target.querySelector('button[type=submit]');
  var original = btn.textContent;
  btn.textContent = 'Thanks, we will be in touch';
  setTimeout(function () { e.target.reset(); btn.textContent = original; }, 3200);
  return false;
}
