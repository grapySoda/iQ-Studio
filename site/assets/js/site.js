/* iQ-Studio Pages — runtime behavior
   Adapted from github_page_style/iQ-Studio Docs.html inline <script>.
   Differences from prototype:
   - SPA page switcher removed: each tutorial is its own URL.
   - Sidebar active-state is driven by <body data-current="..."> set per page.
   - Sidebar groups auto-open if they contain the active link.
   - TOC is built from the current page's h2/h3 (no per-page lookup needed).
   - Mobile sidebar toggle + backdrop wired up.
*/

(function () {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  /* ---------- Sidebar: active state + auto-expand active group ---------- */
  const current = document.body.dataset.current || '';
  if (current) {
    $$('#sidebar [data-page]').forEach(a => {
      if (a.dataset.page === current) {
        a.classList.add('is-active');
        const grp = a.closest('.nav-group');
        if (grp) grp.classList.add('is-open');
      }
    });
  }

  /* ---------- Sidebar: collapse/expand groups on click ---------- */
  $$('[data-group] .nav-group__toggle').forEach(btn => {
    btn.addEventListener('click', () => btn.parentElement.classList.toggle('is-open'));
  });

  /* ---------- Mobile sidebar toggle ---------- */
  const sidebar = $('#sidebar');
  const toggle = $('#sidebar-toggle');
  let backdrop = $('#sidebar-backdrop');
  if (!backdrop && sidebar) {
    backdrop = document.createElement('div');
    backdrop.id = 'sidebar-backdrop';
    backdrop.className = 'sidebar-backdrop';
    document.body.appendChild(backdrop);
  }
  function openSidebar() {
    sidebar && sidebar.classList.add('is-open');
    backdrop && backdrop.classList.add('is-visible');
  }
  function closeSidebar() {
    sidebar && sidebar.classList.remove('is-open');
    backdrop && backdrop.classList.remove('is-visible');
  }
  if (toggle) toggle.addEventListener('click', e => {
    e.preventDefault();
    sidebar && sidebar.classList.contains('is-open') ? closeSidebar() : openSidebar();
  });
  if (backdrop) backdrop.addEventListener('click', closeSidebar);

  /* ---------- TOC: build from h2/h3 in main content ---------- */
  const tocList = $('#toc-list');
  if (tocList) {
    const headings = $$('main.main h2, main.main h3').filter(h => h.id);
    tocList.innerHTML = '';
    headings.forEach(h => {
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = '#' + h.id;
      a.textContent = (h.textContent || '').trim();
      if (h.tagName === 'H3') a.classList.add('toc-l3');
      li.appendChild(a);
      tocList.appendChild(li);
    });
    if (headings.length === 0) {
      const toc = $('.toc');
      if (toc) toc.style.display = 'none';
    }
    /* Scroll-spy: highlight current section as the user scrolls */
    if (headings.length > 0 && 'IntersectionObserver' in window) {
      const linkFor = new Map();
      $$('#toc-list a').forEach(a => {
        const id = a.getAttribute('href').slice(1);
        linkFor.set(id, a);
      });
      const visible = new Set();
      const io = new IntersectionObserver(entries => {
        entries.forEach(e => {
          if (e.isIntersecting) visible.add(e.target.id);
          else visible.delete(e.target.id);
        });
        $$('#toc-list a').forEach(a => a.classList.remove('is-active'));
        for (const h of headings) {
          if (visible.has(h.id)) {
            const a = linkFor.get(h.id);
            if (a) a.classList.add('is-active');
            break;
          }
        }
      }, { rootMargin: '-80px 0px -70% 0px', threshold: 0 });
      headings.forEach(h => io.observe(h));
    } else if (headings.length > 0) {
      tocList.querySelector('a').classList.add('is-active');
    }
  }

  /* ---------- Code copy buttons ---------- */
  $$('.codeblock__copy').forEach(btn => {
    btn.addEventListener('click', () => {
      const pre = btn.closest('.codeblock').querySelector('pre');
      if (!pre) return;
      const text = pre.innerText;
      const done = () => {
        const orig = btn.textContent;
        btn.textContent = 'Copied!';
        setTimeout(() => { btn.textContent = orig; }, 1200);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done).catch(() => {
          fallbackCopy(text); done();
        });
      } else {
        fallbackCopy(text); done();
      }
    });
  });
  function fallbackCopy(text) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); } catch (_) {}
    document.body.removeChild(ta);
  }
})();
