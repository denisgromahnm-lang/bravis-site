"""Static in-restaurant guest hub; no forms, checkout or new analytics."""
import html
import json

ARROW = '<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M5 12h14m-6-6 6 6-6 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'

LOONA_4992 = 'https://app.loona.ai/4992/create/register?source=qr&tag=none'


def render_guest_hub(config, settings, document_head, lunch_price, reserve_link):
    escape = lambda value: html.escape(str(value), quote=True)
    enabled = settings.get('loonaEnabled', True)
    loona = config.get('loonaJoinUrl', '')
    if enabled and loona != LOONA_4992:
        raise ValueError('Guest hub must retain the verified main Loona 4992 URL')
    cards = [
        ('guest_card', 'Карта гостя Bravis', 'Карта гостя BRAVIS в вашем смартфоне. Условия программы — на странице оформления.', loona if enabled else '', True),
        ('lunch', 'Меню бизнес-ланча', f'{lunch_price} ₽ · пн–пт · 11:00–16:00 МСК', '/lunch/', False),
        ('menu_evening', 'Меню и вечер в Bravis', 'Посмотрите актуальное меню и выберите повод вернуться.', '/menu/', False),
        ('corporate', 'Корпоратив или семейная встреча', 'Обсудить дату, число гостей и формат.', '/banquets/', False),
        ('future_booking', 'Стол на следующий визит', 'Открыть существующую форму бронирования. Подтверждение — по правилам сервиса.', reserve_link, False),
        ('public_review', 'Оставить отзыв на Яндекс Картах', 'Откроется карточка Bravis — выберите раздел отзывов.', config['yandexMapsUrl'], False),
        ('private_feedback', 'Написать ресторану', 'Вопрос, пожелание или жалоба — передадим ответственному.', '/contacts/#max-contact', False),
    ]
    rows = []
    for key, title, description, href, primary in cards:
        modifier = ' guest-hub-card--primary' if primary else ''
        content = f'<span class="guest-hub-card__title">{escape(title)}</span><span class="guest-hub-card__description">{escape(description)}</span>'
        if href:
            track = ' data-track="reserve_click"' if key == 'future_booking' else (' data-track="loona_signup_click"' if key == 'guest_card' else '')
            card = f'<a class="guest-hub-card{modifier}" href="{escape(href)}"{track}>{content}<span class="guest-hub-card__arrow" aria-hidden="true">{ARROW}</span></a>'
        else:
            card = f'<div class="guest-hub-card guest-hub-card--unavailable">{content}<span class="guest-hub-card__description">Оформление временно недоступно. Обратитесь к сотруднику ресторана.</span></div>'
        rows.append(f'<li data-hub-id="{key}">{card}</li>')
    # One promotional block: a conservative static evening variant, enhanced by the same lunch clock.
    promos = []
    for key in ('evening', 'lunch'):
        promo = dict(settings['promo'][key])
        if key == 'lunch':
            if promo['title'].count('{price}') != 1:
                raise ValueError('Lunch promo title must contain one {price} placeholder')
            promo['title'] = promo['title'].replace('{price}', str(lunch_price))
        if promo['href'] not in ('/lunch/', '/banquets/'):
            raise ValueError('Hub promo must use an existing approved site route')
        if not promo['image'].startswith(('/uploads/', '/menu-media/')) or '..' in promo['image']:
            raise ValueError('Hub promo must use existing self-hosted restaurant media')
        hidden = ' hidden' if key == 'lunch' else ''
        modifier = ' guest-hub-promo__variant--menu' if key == 'lunch' else ''
        promos.append(
            f'<a class="guest-hub-promo__variant{modifier}" data-promo-variant="{key}" href="{escape(promo["href"])}"{hidden}>'
            f'<img src="{escape(promo["image"])}" alt="{escape(promo["imageAlt"])}" width="68" height="86" loading="lazy">'
            f'<div><p class="guest-hub-promo__eyebrow">{escape(promo["eyebrow"])}</p>'
            f'<h2>{escape(promo["title"])}</h2><span class="guest-hub-promo__cta">{escape(promo["linkText"])} <span aria-hidden="true">{ARROW}</span></span></div></a>'
        )
    promo_html = '<section class="guest-hub-promo" aria-label="Предложение Bravis">' + ''.join(promos) + '</section>'
    runtime = {'holidayOverrides': settings.get('holidayOverrides', {}), 'lunchPrice': str(lunch_price)}
    payload = json.dumps(runtime, ensure_ascii=False).replace('<', '\\u003c')
    document_head = document_head.replace('</head>', '<link rel="stylesheet" href="/assets/guest-hub.css"></head>')
    return document_head + f'''<a class="skip" href="#main">Перейти к содержимому</a>
<header class="guest-hub-header" id="top"><a class="guest-hub-brand logo" href="/" aria-label="BRAVIS — основной сайт">BRAVIS</a><span>Расковой, 20</span><a class="guest-hub-menu" href="/menu/" data-track="menu_from_header">Меню</a></header>
<main class="guest-hub-shell" id="main" data-guest-hub>
  <div class="guest-hub-intro"><p class="guest-hub-eyebrow">ВЫ УЖЕ В BRAVIS</p><h1>Меню и карта гостя</h1><p>Выберите, что удобно сейчас, или спланируйте следующую встречу.</p></div>
  {promo_html}
  <p class="guest-hub-badge" data-lunch-badge hidden>Сейчас время бизнес-ланча</p>
  <ul class="guest-hub-links" aria-label="Меню, карта и следующий визит">{''.join(rows)}</ul>
  <div class="guest-hub-notes"><p data-lunch-note>Бизнес-ланч: {escape(lunch_price)} ₽, пн–пт с 11:00 до 16:00 МСК. В праздничные дни режим уточняйте у сотрудника.</p><p>Заказ примет сотрудник ресторана.</p><p>Напишите, что понравилось и что стоит исправить.</p></div>
</main>
<footer class="guest-hub-footer"><div class="footer-bottom"><a href="/privacy/">Политика обработки персональных данных</a><a href="/">Основной сайт Bravis</a></div></footer>
<button class="back-to-top" type="button" aria-label="Наверх страницы" hidden><svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="m5 12 7-7 7 7M12 5v15" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg><span>Наверх</span></button>
<script type="application/json" id="guest-hub-settings">{payload}</script><script src="/assets/guest-hub.js" defer></script><script src="/assets/site.js" defer></script></body></html>'''

