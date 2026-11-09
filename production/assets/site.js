(() => {
  const header = document.querySelector('.site-header');
  if (header) {
    const fitHeader = () => {
      document.documentElement.style.setProperty('--site-header-height', Math.ceil(header.getBoundingClientRect().height) + 'px');
    };
    fitHeader();
    window.addEventListener('resize', fitHeader, {passive:true});
    if (typeof ResizeObserver === 'function') new ResizeObserver(fitHeader).observe(header);
  }
  const toggle = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.mobile-nav');
  if (toggle && nav) {
    const fitNav = () => {
      const header = toggle.closest('.site-header');
      nav.style.setProperty('--mobile-nav-top', Math.ceil(header.getBoundingClientRect().bottom) + 'px');
    };
    const close = () => { nav.hidden = true; toggle.setAttribute('aria-expanded', 'false'); toggle.setAttribute('aria-label','Открыть меню'); document.body.classList.remove('nav-open'); };
    toggle.addEventListener('click', () => {
      if (!nav.hidden) return close();
      nav.hidden = false;
      toggle.setAttribute('aria-expanded', 'true');
      toggle.setAttribute('aria-label', 'Закрыть меню');
      document.body.classList.add('nav-open');
      fitNav();
    });
    window.addEventListener('resize', () => { if (!nav.hidden) fitNav(); });
    nav.querySelectorAll('a').forEach(el => el.addEventListener('click', close));
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && !nav.hidden) { close(); toggle.focus(); }
    });
    window.matchMedia('(max-width: 1199px)').addEventListener('change', event => {
      if (!event.matches) close();
    });
  }
  // Counters are only initialized after explicit consent and when owner IDs exist.
  const conf = window.BRAVIS_ANALYTICS || {};
  const consentKey = 'bravis_analytics_consent_v1';
  // Some browser privacy modes block storage. Keep consent for this page in memory.
  let consentValue = null;
  try { consentValue = localStorage.getItem(consentKey); } catch {}
  const track = (eventName) => {
    if (consentValue !== 'yes') return;
    if (typeof window.ym === 'function' && conf.ymId) window.ym(Number(conf.ymId), 'reachGoal', eventName);
    if (typeof window.gtag === 'function' && conf.ga4Id) window.gtag('event', eventName);
  };
  // Delegation also covers freshly published restaurant-news links.
  document.addEventListener('click', event => {
    const target = event.target instanceof Element ? event.target : null;
    const tracked = target?.closest('[data-track]');
    if (tracked) track(tracked.dataset.track);
    const anchor = target?.closest('a[href]');
    if (!anchor) return;
    const href = anchor.getAttribute('href') || '';
    if (href.startsWith('tel:')) track('phone_click');
    if (/^\/(?:bravis-site\/)?menu\/(?:[#?].*)?$/.test(href)) track('menu_open');
  });
  if (!conf.ymId && !conf.ga4Id) return;
  function loadAnalytics() {
    if (conf.ymId) {
      window.ym=window.ym||function(){(window.ym.a=window.ym.a||[]).push(arguments)};
      window.ym.l=Date.now();
      const script=document.createElement('script');
      script.async=true; script.src='https://mc.yandex.com/metrika/tag.js?id='+encodeURIComponent(conf.ymId);
      document.head.appendChild(script);
      // Enable privacy-friendly baseline features only after visitors accept analytics.
      // Webvisor and e-commerce remain disabled until the owner approves their use.
      window.ym(Number(conf.ymId),'init',{clickmap:true,trackLinks:true,accurateTrackBounce:true});
    }
    if (conf.ga4Id) {
      const script=document.createElement('script');script.async=true;
      script.src='https://www.googletagmanager.com/gtag/js?id='+encodeURIComponent(conf.ga4Id);
      document.head.appendChild(script);
      window.dataLayer=window.dataLayer||[];
      window.gtag=function(){dataLayer.push(arguments)};
      gtag('js',new Date()); gtag('config',conf.ga4Id);
    }
  }
  const saved = consentValue;
  if (saved === 'yes') { loadAnalytics(); }
  if (saved === null) {
    const banner=document.createElement('div');banner.className='cookie-banner';banner.setAttribute('role','dialog');banner.setAttribute('aria-label','Настройки аналитики');
    // Reuse the actual page link, including the /bravis-site/ GitHub Pages prefix.
    const privacyHref = document.querySelector('.footer-bottom a[href$="/privacy/"]')?.getAttribute('href') || '/privacy/';
    banner.innerHTML='<p>Для улучшения сайта мы используем необязательную аналитику. <a href="'+privacyHref+'">Подробнее</a></p><div><button type="button" data-consent="no">Без аналитики</button><button type="button" data-consent="yes">Разрешить</button></div>';
    document.body.appendChild(banner);
    banner.querySelectorAll('[data-consent]').forEach(b => b.addEventListener('click',()=>{
      consentValue = b.dataset.consent;
      try { localStorage.setItem(consentKey,consentValue); } catch {}
      banner.remove();if(b.dataset.consent==='yes') loadAnalytics();
    }));
  }
  const footer = document.querySelector('.footer-bottom');
  if (footer) {
    const settings=document.createElement('button'); settings.type='button';settings.className='cookie-settings';settings.textContent='Настройки cookie';
    settings.onclick=()=>{try { localStorage.removeItem(consentKey); } catch {} location.reload();};
    footer.appendChild(settings);
  }
})();

// The visitor controls the embedded map; its toolbar stays outside the provider iframe.
(() => {
  document.querySelectorAll('[data-yandex-widget="map"]').forEach(container => {
    const button = container.querySelector('.external-widget-load');
    const id = container.dataset.yandexOrg;
    if (!button || !/^\d+$/.test(id || '')) return;
    button.addEventListener('click', () => {
      if (container.classList.contains('map-is-open')) return;
      const original = [...container.children].map(node => [node, node.hidden]);
      original.forEach(([node]) => { node.hidden = true; });
      const panel = document.createElement('div'); panel.className = 'map-embedded';
      const toolbar = document.createElement('div'); toolbar.className = 'map-embedded__toolbar';
      const close = document.createElement('button'); close.type = 'button'; close.textContent = 'Закрыть карту';
      const route = document.createElement('a'); route.href = 'https://yandex.ru/maps/org/bravis/' + id + '/';
      route.target = '_blank'; route.rel = 'noopener noreferrer'; route.textContent = 'Открыть маршрут ↗';
      toolbar.append(close, route);
      const frame = document.createElement('iframe'); frame.title = 'Ресторан BRAVIS на Яндекс Картах';
      frame.src = 'https://yandex.ru/map-widget/v1/?ol=biz&oid=' + id + '&z=16';
      frame.referrerPolicy = 'strict-origin-when-cross-origin';
      panel.append(toolbar, frame); container.append(panel); container.classList.add('map-is-open');
      close.addEventListener('click', () => {
        panel.remove(); container.classList.remove('map-is-open');
        original.forEach(([node, hidden]) => { node.hidden = hidden; });
        button.focus({preventScroll:true});
      });
      close.focus({preventScroll:true});
    });
  });
})();

// Keep the return-to-top control available on long pages at every screen size.
(() => {
  const button = document.querySelector('.back-to-top');
  if (!button) return;
  let pending = false;
  const update = () => {
    pending = false;
    button.hidden = window.scrollY < 400;
    if (button.hidden) return;
    const booking = document.querySelector('.mobile-bottom-cta');
    const banner = document.querySelector('.cookie-banner');
    let bottom = Math.max(20, (booking?.getBoundingClientRect().height || 0) + 12);
    if (banner) {
      const bannerRect = banner.getBoundingClientRect();
      const buttonRect = button.getBoundingClientRect();
      if (bannerRect.right > buttonRect.left - 12 && bannerRect.left < buttonRect.right + 12) {
        bottom = Math.max(bottom, innerHeight - bannerRect.top + 12);
      }
    }
    button.style.setProperty('--back-to-top-bottom', bottom + 'px');
  };
  const schedule = () => {
    if (!pending) { pending = true; requestAnimationFrame(update); }
  };
  ['scroll', 'resize', 'pageshow'].forEach(event => window.addEventListener(event, schedule, { passive: true }));
  const banner = document.querySelector('.cookie-banner');
  if (banner) {
    new MutationObserver(schedule).observe(document.body, { childList: true });
    if (typeof ResizeObserver === 'function') new ResizeObserver(schedule).observe(banner);
  }
  button.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    document.querySelector('.logo')?.focus({ preventScroll: true });
  });
  update();
})();

// The verified MAX account is found by phone; no public profile URL is assumed.
(() => {
  document.querySelectorAll('[data-copy-max-phone]').forEach(button => {
    if (!navigator.clipboard?.writeText) return;
    button.hidden = false;
    const status = button.closest('.max-contact-section').querySelector('.max-contact-status');
    button.addEventListener('click', async () => {
      button.disabled = true;
      try {
        await navigator.clipboard.writeText(button.dataset.copyMaxPhone);
        status.textContent = 'Номер скопирован. Вставьте его в поиск MAX.';
      } catch {
        status.textContent = 'Не удалось скопировать. Выделите номер выше и скопируйте его вручную.';
      } finally {
        button.disabled = false;
      }
    });
  });
})();
