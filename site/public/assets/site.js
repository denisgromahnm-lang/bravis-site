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
  const track = (eventName) => {
    if (localStorage.getItem(consentKey) !== 'yes') return;
    if (typeof window.ym === 'function' && conf.ymId) window.ym(Number(conf.ymId), 'reachGoal', eventName);
    if (typeof window.gtag === 'function' && conf.ga4Id) window.gtag('event', eventName);
  };
  document.querySelectorAll('[data-track]').forEach(a => a.addEventListener('click', () => track(a.dataset.track)));
  if (!conf.ymId && !conf.ga4Id) return;
  function loadAnalytics() {
    if (conf.ymId) {
      window.ym=window.ym||function(){(window.ym.a=window.ym.a||[]).push(arguments)};
      window.ym.l=Date.now();
      const script=document.createElement('script');
      script.async=true; script.src='https://mc.yandex.ru/metrika/tag.js';
      document.head.appendChild(script);
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
  const saved = localStorage.getItem(consentKey);
  if (saved === 'yes') { loadAnalytics(); }
  if (saved === null) {
    const banner=document.createElement('div');banner.className='cookie-banner';banner.setAttribute('role','dialog');banner.setAttribute('aria-label','Настройки аналитики');
    // Reuse the actual page link, including the /bravis-site/ GitHub Pages prefix.
    const privacyHref = document.querySelector('.footer-bottom a[href$="/privacy/"]')?.getAttribute('href') || '/privacy/';
    banner.innerHTML='<p>Для улучшения сайта мы используем необязательную аналитику. <a href="'+privacyHref+'">Подробнее</a></p><div><button type="button" data-consent="no">Без аналитики</button><button type="button" data-consent="yes">Разрешить</button></div>';
    document.body.appendChild(banner);
    banner.querySelectorAll('[data-consent]').forEach(b => b.addEventListener('click',()=>{
      localStorage.setItem(consentKey,b.dataset.consent);
      banner.remove();if(b.dataset.consent==='yes') loadAnalytics();
    }));
  }
  const footer = document.querySelector('.footer-bottom');
  if (footer) {
    const settings=document.createElement('button'); settings.type='button';settings.className='cookie-settings';settings.textContent='Настройки cookie';
    settings.onclick=()=>{localStorage.removeItem(consentKey);location.reload();};
    footer.appendChild(settings);
  }
})();
