(() => {
  const dataNode = document.getElementById('bravis-menu-data');
  const dialog = document.getElementById('menu-lightbox');
  const stage = document.getElementById('menu-lightbox-stage');
  if (!dataNode || !dialog || !stage || typeof dialog.showModal !== 'function') return;
  let sections;
  try { sections = JSON.parse(dataNode.textContent); } catch { return; }
  if (!Array.isArray(sections) || !sections.length) return;
  const title = document.getElementById('menu-lightbox-title');
  const count = document.getElementById('menu-lightbox-counter');
  const image = document.getElementById('menu-lightbox-image');
  const sheet = document.getElementById('menu-lightbox-sheet');
  const prev = document.getElementById('menu-lightbox-prev');
  const next = document.getElementById('menu-lightbox-next');
  const zoomOut = document.getElementById('menu-zoom-out');
  const zoomIn = document.getElementById('menu-zoom-in');
  const fit = document.getElementById('menu-zoom-fit');
  const level = document.getElementById('menu-zoom-level');
  const original = document.getElementById('menu-original');
  const status = document.getElementById('menu-lightbox-status');
  let section = 0, page = 0, zoom = 1, focusBefore = null;
  let previousOverflow = '', drag = null, viewportWidth = 0, viewportHeight = 0;
  const maxZoom = 6;
  function controls(ready) {
    zoomOut.disabled = !ready || zoom <= 1;
    zoomIn.disabled = !ready || zoom >= maxZoom;
    fit.disabled = !ready || zoom === 1;
    level.textContent = Math.round(zoom * 100) + '%';
    stage.classList.toggle('is-zoomed', ready && zoom > 1);
  }
  function center() {
    return {
      x: (stage.scrollLeft + stage.clientWidth / 2 - sheet.offsetLeft) / (sheet.offsetWidth || 1),
      y: (stage.scrollTop + stage.clientHeight / 2 - sheet.offsetTop) / (sheet.offsetHeight || 1)
    };
  }
  function layout(point = { x: .5, y: .5 }) {
    if (!dialog.open || !image.naturalWidth || !image.naturalHeight) return;
    viewportWidth = stage.offsetWidth; viewportHeight = stage.offsetHeight;
    const scale = Math.min(viewportWidth / image.naturalWidth, viewportHeight / image.naturalHeight);
    sheet.style.width = Math.max(1, Math.floor(image.naturalWidth * scale * zoom)) + 'px';
    sheet.style.height = Math.max(1, Math.floor(image.naturalHeight * scale * zoom)) + 'px';
    stage.scrollLeft = zoom === 1 ? 0 : sheet.offsetLeft + point.x * sheet.offsetWidth - stage.clientWidth / 2;
    stage.scrollTop = zoom === 1 ? 0 : sheet.offsetTop + point.y * sheet.offsetHeight - stage.clientHeight / 2;
    controls(true);
  }
  function setZoom(value) {
    if (!image.complete || !image.naturalWidth) return;
    const point = center(); zoom = Math.max(1, Math.min(maxZoom, value)); layout(point);
  }
  function draw() {
    const choice = sections[section];
    if (!choice?.pages?.length) return;
    page = Math.max(0, Math.min(choice.pages.length - 1, page)); zoom = 1;
    title.textContent = choice.title; count.textContent = (page + 1) + ' / ' + choice.pages.length;
    original.href = choice.pages[page]; status.textContent = 'Загружаем меню…';
    stage.setAttribute('aria-busy', 'true'); sheet.style.width = sheet.style.height = '1px'; controls(false);
    image.alt = choice.title + ', страница ' + (page + 1); image.src = choice.pages[page];
    const singlePage = choice.pages.length === 1;
    dialog.classList.toggle('menu-lightbox--single', singlePage);
    prev.hidden = next.hidden = singlePage;
    prev.disabled = page === 0; next.disabled = page === choice.pages.length - 1;
  }
  image.addEventListener('load', () => {
    if (!dialog.open) return;
    status.textContent = ''; stage.setAttribute('aria-busy', 'false'); layout();
  });
  image.addEventListener('error', () => {
    if (!dialog.open) return;
    stage.setAttribute('aria-busy', 'false'); status.textContent = 'Меню не загрузилось. Попробуйте открыть оригинал.'; controls(false);
  });
  document.querySelectorAll('[data-menu-index]').forEach(link => link.addEventListener('click', event => {
    const index = Number(link.dataset.menuIndex);
    if (!Number.isInteger(index) || index < 0 || index >= sections.length) return;
    event.preventDefault(); section = index; page = 0; focusBefore = link;
    previousOverflow = document.documentElement.style.overflow; document.documentElement.style.overflow = 'hidden';
    dialog.showModal(); draw();
  }));
  prev.addEventListener('click', () => { page--; draw(); });
  next.addEventListener('click', () => { page++; draw(); });
  zoomIn.addEventListener('click', () => setZoom(zoom + .5));
  zoomOut.addEventListener('click', () => setZoom(zoom - .5));
  fit.addEventListener('click', () => setZoom(1));
  image.addEventListener('dblclick', () => setZoom(zoom === 1 ? 2 : 1));
  document.getElementById('menu-lightbox-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => {
    image.removeAttribute('src'); document.documentElement.style.overflow = previousOverflow;
    drag = null; stage.classList.remove('is-dragging');
    if (focusBefore?.isConnected) focusBefore.focus({ preventScroll: true });
  });
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  dialog.addEventListener('keydown', event => {
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    if (event.key === '+' || event.key === '=') { event.preventDefault(); setZoom(zoom + .5); }
    else if (event.key === '-') { event.preventDefault(); setZoom(zoom - .5); }
    else if (event.key === '0') { event.preventDefault(); setZoom(1); }
    else if (zoom > 1 && ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) {
      event.preventDefault(); const step = Math.max(80, stage.clientWidth / 4);
      if (event.key === 'ArrowLeft') stage.scrollLeft -= step;
      if (event.key === 'ArrowRight') stage.scrollLeft += step;
      if (event.key === 'ArrowUp') stage.scrollTop -= step;
      if (event.key === 'ArrowDown') stage.scrollTop += step;
    } else if (sections[section].pages.length > 1) {
      if (event.key === 'ArrowLeft' && page > 0) { event.preventDefault(); page--; draw(); }
      if (event.key === 'ArrowRight' && page < sections[section].pages.length - 1) { event.preventDefault(); page++; draw(); }
    }
  });
  // Native touch scrolling remains available; a mouse can drag the enlarged page.
  stage.addEventListener('pointerdown', event => {
    if (event.pointerType !== 'mouse' || event.button !== 0 || zoom <= 1) return;
    drag = { x: event.clientX, y: event.clientY, left: stage.scrollLeft, top: stage.scrollTop };
    stage.setPointerCapture(event.pointerId); stage.classList.add('is-dragging'); event.preventDefault();
  });
  stage.addEventListener('pointermove', event => {
    if (!drag) return;
    stage.scrollLeft = drag.left - (event.clientX - drag.x); stage.scrollTop = drag.top - (event.clientY - drag.y);
  });
  const endDrag = () => { drag = null; stage.classList.remove('is-dragging'); };
  ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(name => stage.addEventListener(name, endDrag));
  const resize = () => {
    if (dialog.open && (stage.offsetWidth !== viewportWidth || stage.offsetHeight !== viewportHeight)) layout(center());
  };
  if (typeof ResizeObserver === 'function') new ResizeObserver(resize).observe(stage);
  else window.addEventListener('resize', resize);
})();
