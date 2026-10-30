// Same-origin public editorial snapshots only; no guest state or page reloads.
(() => {
  'use strict';
  const script = document.currentScript;
  const initial = document.getElementById('restaurant-life-data');
  const elements = [...document.querySelectorAll('[data-restaurant-life-part]')];
  if (!script?.src || !initial || !elements.length) return;

  const MAX_BYTES = 50 * 1024;
  const PART_IDS = {today: 'bravis-today', formats: 'bravis-formats', news: 'bravis-news'};
  const LINKS = new Set(['/menu/', '/lunch/', '/banquets/', '/contacts/', '/#offers', '/#loyalty']);
  const ITEM_KEYS = ['id', 'title', 'description', 'href', 'linkText'];
  const MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля',
    'августа', 'сентября', 'октября', 'ноября', 'декабря'];
  const WEEKDAYS = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье'];
  const OVERRIDE_STATES = new Set(['unconfirmed', 'no_lunch_confirmed',
    'special_hours_confirmed', 'regular_lunch_confirmed']);
  let base, feed;
  try {
    const source = new URL(script.src, location.href);
    if (source.origin !== location.origin) return;
    base = new URL('../', source);
    feed = new URL('restaurant-life.json', source);
  } catch { return; }

  const visible = () => document.visibilityState === 'visible';
  const route = path => {
    const url = new URL(path.slice(1), base);
    return url.pathname + url.hash;
  };
  const shape = (value, keys) => {
    if (!value || typeof value !== 'object' || Array.isArray(value)
      || Object.getPrototypeOf(value) !== Object.prototype) throw new Error('Invalid object');
    const actual = Object.keys(value);
    if (actual.length !== keys.length || actual.some(key => !keys.includes(key))) throw new Error('Invalid fields');
  };
  const text = (value, limit) => {
    if (typeof value !== 'string' || !value.trim() || [...value].length > limit || /[\u0000-\u001f]/.test(value)) {
      throw new Error('Invalid text');
    }
    for (const character of value) {
      const point = character.codePointAt(0);
      if (point >= 0xd800 && point <= 0xdfff) throw new Error('Invalid Unicode');
    }
    return value.trim();
  };
  const day = value => {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) throw new Error('Invalid date');
    const [year, month, date] = value.split('-').map(Number);
    const check = new Date(0);
    check.setUTCFullYear(year, month - 1, date);
    if (!year || check.getUTCFullYear() !== year || check.getUTCMonth() !== month - 1 || check.getUTCDate() !== date) {
      throw new Error('Invalid date');
    }
    return {year, month, date};
  };
  const minute = value => {
    if (typeof value !== 'string' || !/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(value)) throw new Error('Invalid time');
    const [hour, min] = value.split(':').map(Number);
    return hour * 60 + min;
  };
  const item = (raw, extra = []) => {
    shape(raw, [...ITEM_KEYS, ...extra]);
    if (typeof raw.id !== 'string' || !/^[a-z][a-z0-9-]{0,63}$/.test(raw.id)
      || !LINKS.has(raw.href)) throw new Error('Invalid item');
    return {id: raw.id, title: text(raw.title, 140), description: text(raw.description, 700),
      href: raw.href, linkText: text(raw.linkText, 80)};
  };
  const list = (raw, max) => {
    if (!Array.isArray(raw) || raw.length > max) throw new Error('Invalid list');
    return raw;
  };
  const unique = items => {
    if (new Set(items.map(value => value.id)).size !== items.length) throw new Error('Duplicate ID');
    return items;
  };
  const validate = raw => {
    shape(raw, ['schemaVersion', 'timeZone', 'revision', 'fallback', 'regulars', 'holidayOverrides', 'formats', 'news']);
    if (raw.schemaVersion !== 1 || raw.timeZone !== 'Europe/Moscow'
      || typeof raw.revision !== 'string' || !/^[a-f0-9]{20}$/.test(raw.revision)) throw new Error('Unsupported snapshot');
    const data = {schemaVersion: 1, timeZone: 'Europe/Moscow', revision: raw.revision,
      fallback: item(raw.fallback), regulars: [], holidayOverrides: {}, formats: [], news: []};
    data.regulars = unique(list(raw.regulars, 1).map(value => {
      const result = item(value, ['weekdays', 'start', 'end']);
      if (value.id !== 'lunch' || value.href !== '/lunch/' || value.start !== '11:00' || value.end !== '16:00'
        || !Array.isArray(value.weekdays) || value.weekdays.length !== 5
        || value.weekdays.some((weekday, index) => weekday !== index + 1)
        || value.title.includes('{price}')) throw new Error('Unverified recurring offer');
      return {...result, weekdays: [...value.weekdays], start: value.start, end: value.end};
    }));
    if (data.regulars.some(value => value.id === data.fallback.id)) throw new Error('Duplicate today ID');
    if (!raw.holidayOverrides || Array.isArray(raw.holidayOverrides)
      || typeof raw.holidayOverrides !== 'object' || Object.getPrototypeOf(raw.holidayOverrides) !== Object.prototype
      || Object.keys(raw.holidayOverrides).length > 366) throw new Error('Invalid overrides');
    for (const [key, value] of Object.entries(raw.holidayOverrides)) {
      day(key);
      if (!value || !OVERRIDE_STATES.has(value.state)) throw new Error('Invalid holiday state');
      const special = value.state === 'special_hours_confirmed';
      shape(value, special ? ['state', 'start', 'end'] : ['state']);
      if (special && minute(value.end) <= minute(value.start)) throw new Error('Invalid lunch window');
      data.holidayOverrides[key] = special ? {state: value.state, start: value.start, end: value.end} : {state: value.state};
    }
    data.formats = unique(list(raw.formats, 8).map(value => item(value)));
    data.news = unique(list(raw.news, 24).map(value => {
      const result = item(value, ['date']);
      day(value.date);
      return {...result, date: value.date};
    })).sort((a, b) => a.date === b.date ? (a.id < b.id ? 1 : a.id > b.id ? -1 : 0) : (a.date < b.date ? 1 : -1));
    return data;
  };
  const parse = source => {
    if (new TextEncoder().encode(source).byteLength > MAX_BYTES) throw new Error('Snapshot too large');
    return validate(JSON.parse(source));
  };
  let current = null;
  try { current = parse(initial.textContent); } catch { /* Keep the static fallback. */ }

  const records = elements.filter(element => Object.hasOwn(PART_IDS, element.dataset.restaurantLifePart)).map(element => ({
    element, part: element.dataset.restaurantLifePart,
    compact: Boolean(element.querySelector('.restaurant-life__all')), signature: null
  }));
  if (!records.length) return;
  let moscowClock;
  try {
    moscowClock = new Intl.DateTimeFormat('en-GB', {timeZone: 'Europe/Moscow',
      year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23'});
  } catch { /* Formats and news still work when the Moscow clock is unavailable. */ }
  const dateLabel = value => value.date + ' ' + MONTHS[value.month - 1];
  const today = data => {
    if (!moscowClock) throw new Error('Clock unavailable');
    const fields = Object.fromEntries(moscowClock.formatToParts(new Date()).map(part => [part.type, part.value]));
    const key = fields.year + '-' + fields.month + '-' + fields.day;
    const calendar = day(key);
    const stamp = new Date(0);
    stamp.setUTCFullYear(calendar.year, calendar.month - 1, calendar.date);
    const weekday = stamp.getUTCDay() || 7;
    const clockMinute = Number(fields.hour) * 60 + Number(fields.minute);
    const result = {date: key, dateLabel: dateLabel(calendar), weekdayLabel: WEEKDAYS[weekday - 1], items: [], notice: ''};
    const seen = new Set();
    const appendItem = (value, eyebrow) => {
      if (seen.has(value.id)) return;
      seen.add(value.id);
      result.items.push({...Object.fromEntries(ITEM_KEYS.map(name => [name, value[name]])), eyebrow});
    };
    const override = data.holidayOverrides[key];
    for (const regular of data.regulars) {
      let {start, end} = regular;
      let scheduled = regular.weekdays.includes(weekday);
      if (override?.state === 'unconfirmed') {
        scheduled = false;
        result.notice = 'Режим бизнес-ланча сегодня уточните у ресторана.';
      } else if (override?.state === 'no_lunch_confirmed') {
        scheduled = false;
        result.notice = 'Сегодня бизнес-ланча нет. Выберите блюда основного меню.';
      } else if (override?.state === 'special_hours_confirmed') {
        scheduled = true;
        ({start, end} = override);
      }
      if (scheduled && clockMinute < minute(end)) {
        appendItem(regular, (clockMinute >= minute(start) ? 'Сейчас время бизнес-ланча' : 'Сегодня')
          + ' · ' + start + '–' + end + ' МСК');
      }
    }
    data.news.filter(value => value.date === key).forEach(value => appendItem(value, 'Сегодня в BRAVIS'));
    if (weekday === 5 || weekday === 6) {
      data.formats.filter(value => value.id === 'live-music').forEach(value => appendItem(value, 'Сегодня вечером'));
    }
    appendItem(data.fallback, 'Меню и встречи');
    return result;
  };

  const node = (tag, className, value) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (value !== undefined) element.textContent = value;
    return element;
  };
  const link = (className, href, label) => {
    const element = node('a', className, label);
    element.setAttribute('href', route(href));
    return element;
  };
  const heading = (part, label, lead, emphasis) => {
    const row = node('div', 'restaurant-life__heading');
    const copy = node('div');
    const eyebrow = node('div', 'section-label');
    eyebrow.append(node('span', 'line'), document.createTextNode(' ' + label));
    const title = node('h2');
    title.id = PART_IDS[part] + '-heading';
    title.append(document.createTextNode(lead), node('em', '', emphasis));
    copy.append(eyebrow, title);
    row.append(copy);
    return row;
  };
  const card = (value, news = false) => {
    const result = node('article', 'restaurant-life__card');
    result.dataset.lifeId = value.id;
    if (news) {
      const calendar = day(value.date);
      const time = node('time', '', dateLabel(calendar) + ' ' + calendar.year);
      time.setAttribute('datetime', value.date);
      result.append(time);
    } else if (value.eyebrow) result.append(node('span', 'restaurant-life__eyebrow', value.eyebrow));
    result.append(node('h3', '', value.title), node('p', '', value.description));
    const action = link('restaurant-life__link', value.href, value.linkText + ' ');
    const arrow = node('span', '', '↗');
    arrow.setAttribute('aria-hidden', 'true');
    action.append(arrow);
    result.append(action);
    return result;
  };
  const viewFor = record => record.part === 'today' ? today(current)
    : record.part === 'formats' ? current.formats : current.news.slice(0, record.compact ? 3 : 24);
  const render = (record, view) => {
    const wrap = node('div', 'wrap');
    let row;
    if (record.part === 'today') {
      row = heading('today', 'СЕГОДНЯ В BRAVIS', view.dateLabel + ' ', '· ' + view.weekdayLabel);
      row.append(link('restaurant-life__all', '/events/', 'События и жизнь ресторана ↗'));
    } else if (record.part === 'formats') {
      row = heading('formats', 'ПОВОДЫ ДЛЯ ВСТРЕЧИ', 'Спланируем ', 'ваш вечер.');
      row.append(node('p', '', 'Дегустации, гастроужины и предложения ресторана. Запросите ближайшую программу и условия.'));
    } else {
      row = heading('news', 'ЖИЗНЬ РЕСТОРАНА', 'У нас ', 'происходит.');
      if (record.compact) row.append(link('restaurant-life__all', '/events/#bravis-news', 'Все новости ↗'));
    }
    const grid = node('div', 'restaurant-life__grid');
    const values = record.part === 'today' ? view.items : view;
    values.forEach(value => grid.append(card(value, record.part === 'news')));
    if (record.part === 'news' && !values.length) grid.append(node('p', 'restaurant-life__notice', 'Новостями ресторана поделимся здесь.'));
    wrap.append(row, grid);
    const notice = record.part === 'today' ? view.notice : record.part === 'formats'
      ? 'Даты, программу, наличие мест и условия участия подтверждает ресторан.' : '';
    if (notice) wrap.append(node('p', 'restaurant-life__notice', notice));
    return wrap;
  };

  const pathWithin = (element, root) => {
    const path = [];
    while (element && element !== root) {
      path.unshift([...element.parentElement.children].indexOf(element));
      element = element.parentElement;
    }
    return element === root ? path : null;
  };
  const visibleAnchor = () => {
    if (window.scrollY < 1) return null;
    const header = document.querySelector('.site-header');
    const bottom = header?.getBoundingClientRect().bottom || 0;
    const threshold = bottom > 0 && bottom < innerHeight / 2 ? bottom + 8 : 8;
    const candidates = [...document.querySelectorAll('main h1,main h2,main h3,main p,main [data-life-id],main > section,footer')];
    const shown = candidates.map(element => ({element, rect: element.getBoundingClientRect()}))
      .filter(value => value.rect.width > 0 && value.rect.height > 0 && value.rect.bottom > threshold && value.rect.top < innerHeight - 20);
    const target = shown.filter(value => value.rect.top >= threshold).sort((a, b) => a.rect.top - b.rect.top)[0]
      || shown.sort((a, b) => b.rect.top - a.rect.top)[0];
    if (!target) return null;
    const record = records.find(value => value.element.contains(target.element));
    const article = record && target.element.closest('[data-life-id]');
    const root = article || record?.element;
    return {element: target.element, top: target.rect.top, record, card: article?.dataset.lifeId,
      sectionTop: record?.element.getBoundingClientRect().top,
      path: root ? pathWithin(target.element, root) : null};
  };
  const restoreAnchor = anchor => {
    if (!anchor) return;
    let element = anchor.element;
    let top = anchor.top;
    if (!element.isConnected && anchor.record) {
      element = anchor.card ? anchor.record.element.querySelector('[data-life-id="' + anchor.card + '"]') : anchor.record.element;
      for (const index of anchor.path || []) element = element?.children[index];
    }
    // If the visible card was removed, retain the surrounding section's place.
    if (!element?.isConnected && anchor.record?.element.isConnected) {
      element = anchor.record.element;
      top = anchor.sectionTop;
    }
    if (!element?.isConnected) return;
    const change = element.getBoundingClientRect().top - top;
    if (Math.abs(change) > 0.5) window.scrollBy({top: change, left: 0, behavior: 'instant'});
  };
  const refreshRegions = () => {
    if (!visible() || !current) return;
    const changes = [];
    for (const record of records) {
      if (!record.element.isConnected) continue;
      try {
        const view = viewFor(record);
        const signature = JSON.stringify(view);
        if (record.signature === signature) {
          record.element.dataset.lifeRevision = current.revision;
          continue;
        }
        // These regions have no forms; preserve an unexpected future form too.
        if (record.element.contains(document.activeElement)
          || record.element.querySelector('form,input,textarea,select,[contenteditable]:not([contenteditable="false"])')) continue;
        const content = render(record, view);
        const existing = record.element.children;
        const identical = existing.length === 1 && existing[0].isEqualNode(content);
        if (identical) {
          record.signature = signature;
          record.element.dataset.lifeRevision = current.revision;
        } else changes.push({record, content, signature});
      } catch { /* A clock failure must not disturb a usable static region. */ }
    }
    if (!changes.length) return;
    const anchor = visibleAnchor();
    for (const {record, content, signature} of changes) {
      record.element.replaceChildren(content);
      record.signature = signature;
      record.element.dataset.lifeRevision = current.revision;
    }
    restoreAnchor(anchor);
  };

  let inFlight = false;
  let lastRequestAt = -Infinity;
  const readSnapshot = async (response, controller) => {
    const declared = Number(response.headers.get('content-length'));
    if (!response.ok || declared > MAX_BYTES || !response.body?.getReader) throw new Error('Snapshot unavailable');
    const reader = response.body.getReader();
    const chunks = [];
    let size = 0;
    try {
      while (true) {
        const {done, value} = await reader.read();
        if (done) break;
        size += value.byteLength;
        if (size > MAX_BYTES) {
          controller.abort();
          throw new Error('Snapshot too large');
        }
        chunks.push(value);
      }
    } finally { reader.releaseLock(); }
    const bytes = new Uint8Array(size);
    let offset = 0;
    chunks.forEach(chunk => { bytes.set(chunk, offset); offset += chunk.byteLength; });
    return parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes));
  };
  const requestSnapshot = async () => {
    const stamp = performance.now();
    if (!visible() || inFlight || stamp - lastRequestAt < 10000) return;
    lastRequestAt = stamp;
    inFlight = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);
    try {
      const response = await fetch(feed.href, {cache: 'no-store', credentials: 'same-origin',
        mode: 'same-origin', redirect: 'error', signal: controller.signal});
      current = await readSnapshot(response, controller);
      refreshRegions();
    } catch {
      controller.abort();
      // Offline, rejected and malformed snapshots retain current content.
    }
    finally { clearTimeout(timeout); inFlight = false; }
  };
  const resume = () => {
    if (!visible()) return;
    refreshRegions();
    requestSnapshot();
  };
  records.forEach(record => record.element.addEventListener('focusout', () => setTimeout(refreshRegions, 0)));
  document.addEventListener('visibilitychange', resume);
  window.addEventListener('pageshow', resume);
  window.addEventListener('focus', resume);
  setInterval(resume, 60000);
  resume();
})();
