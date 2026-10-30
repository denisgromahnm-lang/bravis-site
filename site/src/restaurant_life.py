"""Editorial restaurant facts, Moscow day rules and static progressive rendering.

The public JSON contains text and approved site links only. It carries no guest
data or claims about unconfirmed event dates. A content revision and the Moscow
clock are independent inputs: a browser can refresh these regions in place.
"""
from copy import deepcopy
from datetime import date, datetime
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo


TIME_ZONE = 'Europe/Moscow'
PART_IDS = {'today': 'bravis-today', 'formats': 'bravis-formats', 'news': 'bravis-news'}
_MONTHS = ('января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля',
           'августа', 'сентября', 'октября', 'ноября', 'декабря')
_WEEKDAYS = ('понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье')
_LINKS = frozenset(('/menu/', '/lunch/', '/banquets/', '/contacts/', '/#offers', '/#loyalty'))
_ITEM_KEYS = frozenset(('id', 'title', 'description', 'href', 'linkText'))
_OVERRIDE_STATES = frozenset(('unconfirmed', 'no_lunch_confirmed',
                              'special_hours_confirmed', 'regular_lunch_confirmed'))
_ARROW = '<span aria-hidden="true">↗</span>'


def _h(value):
    return escape(str(value), quote=True)


def _text(value, name, limit):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f'Invalid restaurant-life {name}')
    if any(ord(character) < 32 for character in value):
        raise ValueError(f'Invalid restaurant-life {name}')
    return value.strip()


def _shape(value, required, name):
    if not isinstance(value, dict) or set(value) != set(required):
        raise ValueError(f'Invalid restaurant-life {name} fields')


def _item(value, extra=()):
    _shape(value, _ITEM_KEYS | set(extra), 'item')
    item = dict(value)
    if not isinstance(item['id'], str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,63}', item['id']):
        raise ValueError('Invalid restaurant-life item ID')
    for key, limit in (('title', 140), ('description', 700), ('linkText', 80)):
        item[key] = _text(item[key], key, limit)
    if not isinstance(item['href'], str) or item['href'] not in _LINKS:
        raise ValueError('Restaurant-life links must use approved site routes')
    return item


def _day(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('Restaurant-life dates must use YYYY-MM-DD')
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError('Invalid restaurant-life date') from None


def _minute(value):
    if not isinstance(value, str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value):
        raise ValueError('Invalid restaurant-life time')
    hour, minute = map(int, value.split(':'))
    return hour * 60 + minute


def _overrides(value):
    if not isinstance(value, dict) or len(value) > 366:
        raise ValueError('Invalid restaurant-life holiday overrides')
    result = deepcopy(value)
    for day, override in result.items():
        _day(day)
        if not isinstance(override, dict) or override.get('state') not in _OVERRIDE_STATES:
            raise ValueError('Invalid restaurant-life holiday state')
        special = override['state'] == 'special_hours_confirmed'
        _shape(override, ('state', 'start', 'end') if special else ('state',), 'holiday override')
        if special and _minute(override['end']) <= _minute(override['start']):
            raise ValueError('Restaurant-life lunch hours must finish after they start')
    return result


def load_restaurant_life(path, *, lunch_price, holiday_overrides=None):
    """Validate the reviewed editorial file and return a bounded public snapshot.

    The existing lunch price and guest-hub overrides remain the source of truth.
    The caller writes restaurant_life_json(data) to /assets/restaurant-life.json.
    No current date is hashed into the revision, so an open page also needs its
    own Moscow clock refresh when the day or lunch window changes.
    """
    content = json.loads(Path(path).read_text(encoding='utf-8'))
    _shape(content, ('schemaVersion', 'timeZone', 'fallback', 'regulars', 'formats', 'news'), 'document')
    if type(content['schemaVersion']) is not int or content['schemaVersion'] != 1 or content['timeZone'] != TIME_ZONE:
        raise ValueError('Unsupported restaurant-life schema or time zone')
    price = str(lunch_price)
    if not re.fullmatch(r'[1-9]\d{0,4}', price):
        raise ValueError('Restaurant-life requires the verified lunch price')
    data = {'schemaVersion': 1, 'timeZone': TIME_ZONE, 'fallback': _item(content['fallback']),
            'regulars': [], 'holidayOverrides': _overrides({} if holiday_overrides is None else holiday_overrides), 'formats': [], 'news': []}
    for key, maximum in (('regulars', 1), ('formats', 8), ('news', 24)):
        if not isinstance(content[key], list) or len(content[key]) > maximum:
            raise ValueError(f'Invalid restaurant-life {key}')
    for raw in content['regulars']:
        item = _item(raw, ('weekdays', 'start', 'end'))
        # Only the already verified weekday lunch has a confirmed repeating rule.
        if (item['id'] != 'lunch' or item['href'] != '/lunch/' or item['weekdays'] != [1, 2, 3, 4, 5]
                or not all(type(day) is int for day in item['weekdays'])):
            raise ValueError('Unverified restaurant-life recurring offer')
        if item['start'] != '11:00' or item['end'] != '16:00' or item['title'].count('{price}') != 1:
            raise ValueError('Restaurant-life lunch must retain the approved schedule and price')
        item['title'] = item['title'].replace('{price}', price)
        data['regulars'].append(item)
    data['formats'] = [_item(value) for value in content['formats']]
    for raw in content['news']:
        item = _item(raw, ('date',))
        _day(item['date'])
        data['news'].append(item)
    for group in ('regulars', 'formats', 'news'):
        ids = [item['id'] for item in data[group]]
        if len(set(ids)) != len(ids):
            raise ValueError(f'Duplicate restaurant-life {group} ID')
    if data['fallback']['id'] in {item['id'] for item in data['regulars']}:
        raise ValueError('Restaurant-life fallback must have its own stable ID')
    data['news'].sort(key=lambda item: (item['date'], item['id']), reverse=True)
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    data['revision'] = sha256(encoded.encode('utf-8')).hexdigest()[:20]
    return data


def restaurant_life_json(data):
    """Safe as an inline application/json payload or a UTF-8 JSON asset."""
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).replace('<', '\\u003c').replace('&', '\\u0026')


def _moscow_now(now):
    if now is None:
        return datetime.now(ZoneInfo(TIME_ZONE))
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('Restaurant-life clock must be a timezone-aware datetime')
    return now.astimezone(ZoneInfo(TIME_ZONE))


def _date_label(value):
    return f'{value.day} {_MONTHS[value.month - 1]}'


def select_today(data, *, now=None):
    """Select a conservative current-day view; future formats never enter it.

    weekday is ISO Monday=1. A scheduled lunch may be shown before service starts;
    the active label applies only to start <= Moscow minute < end. After service
    ends, or without confirmed holiday hours, only the general menu remains.
    """
    current = _moscow_now(now)
    key = current.date().isoformat()
    minute = current.hour * 60 + current.minute
    result = {'date': key, 'dateLabel': _date_label(current.date()),
              'weekdayLabel': _WEEKDAYS[current.weekday()], 'items': [], 'notice': ''}
    override = data['holidayOverrides'].get(key)
    for regular in data['regulars']:
        start, end = regular['start'], regular['end']
        scheduled = current.isoweekday() in regular['weekdays']
        if override:
            state = override['state']
            if state == 'unconfirmed':
                scheduled = False
                result['notice'] = 'Режим бизнес-ланча сегодня уточните у ресторана.'
            elif state == 'no_lunch_confirmed':
                scheduled = False
                result['notice'] = 'Сегодня бизнес-ланча нет. Выберите блюда основного меню.'
            elif state == 'special_hours_confirmed':
                scheduled = True
                start, end = override['start'], override['end']
        if scheduled and minute < _minute(end):
            active = minute >= _minute(start)
            result['items'].append({key: regular[key] for key in _ITEM_KEYS} | {
                'eyebrow': ('Сейчас время бизнес-ланча' if active else 'Сегодня') + f' · {start}–{end} МСК'})
    result['items'].append(dict(data['fallback'], eyebrow='Меню и встречи'))
    return result


def _part_open(part, data):
    return (f'<section class="section restaurant-life restaurant-life--{part}" id="{PART_IDS[part]}" '
            f'data-restaurant-life-part="{part}" data-life-revision="{_h(data["revision"])}" '
            f'aria-labelledby="{PART_IDS[part]}-heading"><div class="wrap">')


def _card(item, *, news=False):
    date_html = ''
    if news:
        day = _day(item['date'])
        date_html = f'<time datetime="{_h(item["date"])}">{_date_label(day)} {day.year}</time>'
    elif item.get('eyebrow'):
        date_html = f'<span class="restaurant-life__eyebrow">{_h(item["eyebrow"])}</span>'
    return (f'<article class="restaurant-life__card" data-life-id="{_h(item["id"])}">'
            f'{date_html}<h3>{_h(item["title"])}</h3><p>{_h(item["description"])}</p>'
            f'<a class="restaurant-life__link" href="{_h(item["href"])}">{_h(item["linkText"])} {_ARROW}</a></article>')


def _render_today(data, now):
    today = select_today(data, now=now)
    notice = f'<p class="restaurant-life__notice">{_h(today["notice"])}</p>' if today['notice'] else ''
    return (_part_open('today', data)
            + f'<div class="restaurant-life__heading"><div><div class="section-label"><span class="line"></span> СЕГОДНЯ В BRAVIS</div>'
            + f'<h2 id="bravis-today-heading">{_h(today["dateLabel"])} <em>· {_h(today["weekdayLabel"])}</em></h2></div>'
            + '<a class="restaurant-life__all" href="/events/">События и жизнь ресторана ↗</a></div>'
            + f'<div class="restaurant-life__grid">{"".join(_card(item) for item in today["items"])}</div>'
            + notice + '</div></section>')


def _render_formats(data):
    return (_part_open('formats', data)
            + '<div class="restaurant-life__heading"><div><div class="section-label"><span class="line"></span> ПОВОДЫ ДЛЯ ВСТРЕЧИ</div>'
            + '<h2 id="bravis-formats-heading">Спланируем <em>ваш вечер.</em></h2></div>'
            + '<p>Дегустации, гастроужины и предложения ресторана. Запросите ближайшую программу и условия.</p></div>'
            + f'<div class="restaurant-life__grid">{"".join(_card(item) for item in data["formats"])}</div>'
            + '<p class="restaurant-life__notice">Даты, программу, наличие мест и условия участия подтверждает ресторан.</p>'
            + '</div></section>')


def _render_news(data, *, compact=False):
    items = data['news'][:3] if compact else data['news']
    cards = ''.join(_card(item, news=True) for item in items)
    if not cards:
        cards = '<p class="restaurant-life__notice">Новостями ресторана поделимся здесь.</p>'
    return (_part_open('news', data)
            + '<div class="restaurant-life__heading"><div><div class="section-label"><span class="line"></span> ЖИЗНЬ РЕСТОРАНА</div>'
            + '<h2 id="bravis-news-heading">У нас <em>происходит.</em></h2></div>'
            + ('<a class="restaurant-life__all" href="/events/#bravis-news">Все новости ↗</a>' if compact else '')
            + '</div>' + f'<div class="restaurant-life__grid">{cards}</div></div></section>')


def render_restaurant_life_home(data, *, now=None):
    """Home fragments; the caller may position the compact today region near hero."""
    return _render_today(data, now) + _render_formats(data) + _render_news(data, compact=True)


def render_restaurant_life_today(data, *, now=None):
    """The same today fragment, separately positionable beside the home hero."""
    return _render_today(data, now)


def render_restaurant_life_formats(data):
    """The same formats fragment, replacing the old experiences block."""
    return _render_formats(data)


def render_restaurant_life_news(data, *, compact=True):
    return _render_news(data, compact=compact)


def render_restaurant_life_page(data, *, now=None):
    """Page body only; the build supplies the existing head/header/footer."""
    return ('<section class="page-hero page-hero--light"><div class="wrap">'
            '<div class="section-label"><span class="line"></span> СОБЫТИЯ И НОВОСТИ</div>'
            '<h1>Жизнь <em>BRAVIS.</em></h1>'
            '<p>Поводы для встречи, программы ресторана и новости с точными датами.</p>'
            '</div></section>' + _render_today(data, now) + _render_formats(data) + _render_news(data))
