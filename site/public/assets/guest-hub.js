// Progressive lunch emphasis only: no forms, URLs from query, storage or network requests.
(() => {
  const hub = document.querySelector('[data-guest-hub]');
  if (!hub) return;
  // The fixed table QR needs no query or hash. Strip untrusted input before the
  // unchanged consent-aware analytics helper can initialize on this page.
  try {
    if (location.search || location.hash) history.replaceState(history.state, '', location.pathname);
  } catch {
    // Preserve the stored consent choice, but do not expose an uncleared URL to analytics.
    if (location.search || location.hash) window.BRAVIS_ANALYTICS = {};
  }
  try {
    const settings = JSON.parse(document.getElementById('guest-hub-settings').textContent);
    const parts = new Intl.DateTimeFormat('en-GB', {
      timeZone: 'Europe/Moscow', year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', hourCycle: 'h23'
    }).formatToParts(new Date());
    const fields = Object.fromEntries(parts.map(part => [part.type, part.value]));
    const key = fields.year + '-' + fields.month + '-' + fields.day;
    const weekday = new Date(Date.UTC(Number(fields.year), Number(fields.month) - 1, Number(fields.day))).getUTCDay();
    const minute = Number(fields.hour) * 60 + Number(fields.minute);
    let active = weekday >= 1 && weekday <= 5 && minute >= 660 && minute < 960;
    const override = settings.holidayOverrides?.[key];
    const note = hub.querySelector('[data-lunch-note]');
    let state = active ? 'open' : 'regular';
    const timeMinute = value => {
      if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(value || '')) return null;
      const [hour, min] = value.split(':').map(Number);
      return hour * 60 + min;
    };
    if (override) {
      if (override.state === 'unconfirmed') {
        active = false; state = 'unconfirmed';
        note.textContent = Number(fields.day) + '.' + fields.month + ': режим бизнес-ланча уточните у сотрудника ресторана.';
      } else if (override.state === 'no_lunch_confirmed') {
        active = false; state = 'no-lunch';
        note.textContent = Number(fields.day) + '.' + fields.month + ' бизнес-ланча нет. Актуальное основное меню доступно выше.';
      } else if (override.state === 'special_hours_confirmed') {
        const start = timeMinute(override.start), end = timeMinute(override.end);
        if (start === null || end === null || end <= start) throw new Error('Invalid confirmed lunch hours');
        active = minute >= start && minute < end; state = active ? 'open-special' : 'special';
        note.textContent = Number(fields.day) + '.' + fields.month + ': бизнес-ланч с ' + override.start + ' до ' + override.end + ' МСК, ' + settings.lunchPrice + ' ₽.';
      } else if (override.state !== 'regular_lunch_confirmed') {
        throw new Error('Unknown holiday state');
      }
    }
    const order = active
      ? ['guest_card', 'lunch', 'menu_evening', 'corporate', 'future_booking', 'public_review', 'private_feedback']
      : ['guest_card', 'menu_evening', 'corporate', 'lunch', 'future_booking', 'public_review', 'private_feedback'];
    const list = hub.querySelector('.guest-hub-links');
    // Reorder the actual DOM once; never move a control already focused by a guest.
    if (!list.contains(document.activeElement)) {
      order.forEach(id => list.appendChild(list.querySelector('[data-hub-id="' + id + '"]')));
    }
    hub.querySelectorAll('[data-promo-variant]').forEach(variant => {
      variant.hidden = variant.dataset.promoVariant !== (active ? 'lunch' : 'evening');
    });
    hub.querySelector('[data-lunch-badge]').hidden = !active;
    hub.dataset.lunchState = state;
  } catch {
    // Static links and the general holiday note remain usable if time support fails.
  }
})();

