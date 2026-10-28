(() => {
  const toggle = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.mobile-nav');
  if (toggle && nav) {
    const close = () => { nav.hidden = true; toggle.setAttribute('aria-expanded', 'false'); toggle.setAttribute('aria-label','Открыть меню'); document.body.classList.remove('nav-open'); };
    toggle.addEventListener('click', () => {
      if (!nav.hidden) return close();
      nav.hidden = false;
      toggle.setAttribute('aria-expanded', 'true');
      toggle.setAttribute('aria-label', 'Закрыть меню');
      document.body.classList.add('nav-open');
    });
    nav.querySelectorAll('a').forEach(el => el.addEventListener('click', close));
    document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
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
  document.querySelectorAll('[data-track]').forEach(a => a.addEventListener('click', () => track(a.dataset.track)));
  // Aggregate goals include every menu entry point and every phone link,
  // while retaining detailed per-button goals for diagnostics.
  document.querySelectorAll('a[href]').forEach(a => a.addEventListener('click', () => {
    const href = a.getAttribute('href') || '';
    if (href.startsWith('tel:')) track('phone_click');
    if (/^\/(?:bravis-site\/)?menu\/(?:[#?].*)?$/.test(href)) track('menu_open');
  }));
  if (!conf.ymId && !conf.ga4Id) return;
  function loadAnalytics() {
    if (conf.ymId) {
      window.ym=window.ym||function(){(window.ym.a=window.ym.a||[]).push(arguments)};
      window.ym.l=Date.now();
      const script=document.createElement('script');
      script.async=true; script.src='https://mc.yandex.ru/metrika/tag.js?id='+encodeURIComponent(conf.ymId);
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

// Loading a map or a rating is an explicit visitor action, separate from analytics consent.
(() => {
  document.querySelectorAll('[data-yandex-widget]').forEach(container => {
    const button = container.querySelector('.external-widget-load');
    const id = container.dataset.yandexOrg;
    if (!button || !/^\d+$/.test(id || '')) return;
    button.addEventListener('click', () => {
      const frame = document.createElement('iframe');
      const map = container.dataset.yandexWidget === 'map';
      frame.title = map ? 'Ресторан BRAVIS на Яндекс Картах' : 'Текущий рейтинг BRAVIS на Яндекс Картах';
      frame.src = map ? 'https://yandex.ru/map-widget/v1/?ol=biz&oid=' + id + '&z=16' : 'https://yandex.ru/sprav/widget/rating-badge/' + id + '?type=rating';
      frame.referrerPolicy = 'strict-origin-when-cross-origin';
      if (map) frame.allowFullscreen = true;
      container.replaceChildren(frame);
    }, { once: true });
  });
})();
