#!/usr/bin/env python3
"""Build the Bravis static website. No pip/npm packages are required."""
import json, html, re, shutil, hashlib
from pathlib import Path
from urllib.parse import quote
from datetime import date
from restaurant_life import (load_restaurant_life, restaurant_life_json, render_restaurant_life_today,
                             render_restaurant_life_formats, render_restaurant_life_news, render_restaurant_life_page)
from guest_promotions import (welcome_strip, offers_section, experiences_section,
                              menu_campaign, banquet_details, contact_invitation, gift_art)

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
CONFIG = json.loads((ROOT / 'site.config.json').read_text(encoding='utf-8'))
MENU = json.loads((ROOT / 'content/menu.json').read_text(encoding='utf-8'))
LUNCH = json.loads((ROOT / 'content/lunch.json').read_text(encoding='utf-8'))
GALLERY = json.loads((ROOT / 'content/gallery.json').read_text(encoding='utf-8')) if (ROOT / 'content/gallery.json').exists() else {}

h = lambda s: html.escape(str(s or ''), quote=True)
name = CONFIG.get('restaurantName','BRAVIS')
phone = CONFIG.get('phoneDisplay','')
phone_url = 'tel:' + re.sub(r'[^+0-9]', '', CONFIG.get('phoneE164',''))
address = CONFIG.get('addressFull', '')
official_email = CONFIG.get('operatorContactEmail', '').strip()
yandex_maps_url = CONFIG.get('yandexMapsUrl','').strip() or ('https://yandex.ru/maps/?text=' + quote(address))
two_gis_url = CONFIG.get('twoGisUrl','').strip()
from urllib.parse import urlsplit
if two_gis_url:
    parts = urlsplit(two_gis_url)
    if parts.scheme != 'https' or parts.hostname not in ('2gis.ru', 'www.2gis.ru', '2gis.com', 'www.2gis.com') or not re.fullmatch(r'/[a-z0-9_-]+/firm/[0-9]+/?', parts.path, re.I):
        raise ValueError('2GIS card must be an HTTPS URL of a known 2GIS firm')
# Never invent a Yandex Eda restaurant link. Until the restaurant's real
# share URL is supplied, link only to the official Yandex Eda landing page.
eda_direct_url = str(CONFIG.get('yandexEdaRestaurantUrl', '')).strip()
eda_service_url = str(CONFIG.get('yandexEdaServiceUrl', 'https://eda.yandex.ru/')).strip()
for delivery_candidate in [eda_service_url] + ([eda_direct_url] if eda_direct_url else []):
    parsed_delivery = urlsplit(delivery_candidate)
    if parsed_delivery.scheme != 'https' or parsed_delivery.hostname != 'eda.yandex.ru' or parsed_delivery.username or parsed_delivery.password or parsed_delivery.port:
        raise ValueError('Yandex Eda URL must use official https://eda.yandex.ru domain')
delivery_url = eda_direct_url or eda_service_url
delivery_has_direct_link = bool(eda_direct_url)
delivery_button_label = 'Заказать доставку' if delivery_has_direct_link else 'Перейти в Яндекс Еду'
# Loona signup is enabled only with the actual, owner-verified card registration URL.
loona_join_url = str(CONFIG.get('loonaJoinUrl', '')).strip()
loona_program_name = str(CONFIG.get('loonaProgramName', 'Карта гостя BRAVIS')).strip()
welcome_bonus = 500
arrow_up_right = '<svg aria-hidden="true" width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 13 13 3M3 3h10v10" stroke="currentColor" stroke-width="1.3"/></svg>'
if loona_join_url:
    parsed_loona = urlsplit(loona_join_url)
    # The vendor may issue registration links on loona.ai subdomains or its
    # authorized card delivery domain. Do not restrict to a guessed path, but
    # reject unsafe/non-HTTPS schemes.
    if parsed_loona.scheme != 'https' or not parsed_loona.hostname or parsed_loona.username or parsed_loona.password:
        raise ValueError('Loona card enrollment link must be an owner-verified HTTPS URL')
loona_registration_cta = (
    f'<div class="loyalty-registration">'
    f'<a class="loyalty-action" href="{h(loona_join_url)}" data-track="loona_signup_click" target="_blank" rel="noopener noreferrer">Оформить карту {arrow_up_right}</a>'
    f'<a class="loyalty-qr" href="{h(loona_join_url)}" data-track="loona_signup_click" target="_blank" rel="noopener noreferrer" aria-label="Оформить карту гостя BRAVIS">'
    f'<img src="/assets/loona-register.svg" alt="QR-код для регистрации в программе лояльности BRAVIS" width="156" height="156" loading="lazy">'
    f'<span>Откройте камеру телефона и сканируйте QR-код для получения карты гостя.</span></a>'
    f'</div>'
    if loona_join_url else
    '<p class="loyalty-pending">Онлайн-регистрация скоро появится здесь. Пока оформить карту можно по QR-коду в ресторане.</p>'
)

delivery_help_text = ('Оформление и условия доставки — в сервисе Яндекс Еда. Доступность зависит от вашего адреса.' if delivery_has_direct_link
                      else 'Выберите адрес доставки и найдите BRAVIS в Яндекс Еде. Прямой переход к меню ресторана пока уточняется.')
domain = CONFIG.get('domain','').strip().rstrip('/')
if domain and not domain.startswith(('https://','http://')): domain = 'https://' + domain
published = bool(CONFIG.get('public') and domain)
social_labels = {'telegram':'Telegram','vk':'ВКонтакте','instagram':'Instagram','max':'MAX','viber':'Viber','whatsapp':'Написать в WhatsApp','telegramMessage':'Написать в Telegram'}
social_links = {key: str(value).strip() for key, value in CONFIG.get('socialLinks', {}).items() if value and key in social_labels}
whatsapp_url = social_links['whatsapp']
max_contact_name = str(CONFIG.get('maxContactName', '')).strip()
max_contact_phone = str(CONFIG.get('phoneE164', '')).strip()
if max_contact_name and not re.fullmatch(r'\+[1-9][0-9]{7,14}', max_contact_phone):
    raise ValueError('MAX contact instructions require the verified business phone')
for social_url in social_links.values():
    parts = urlsplit(social_url)
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password:
        raise ValueError('Public social links must be verified HTTPS URLs')
maps_org_id = str(CONFIG.get('yandexMapsOrgId', ''))
if not re.fullmatch(r'[0-9]+', maps_org_id):
    raise ValueError('Yandex Maps organization ID is required for the verified restaurant')

def social_icon(key):
    icon_name = 'telegram' if key == 'telegramMessage' else key
    if icon_name == 'max':
        return '<svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><text x="12" y="15.5" text-anchor="middle" fill="currentColor" font-family="Arial,sans-serif" font-size="9" font-weight="700">MAX</text></svg>'
    if icon_name in ('telegram', 'vk', 'instagram', 'whatsapp'):
        return (ROOT / f'public/assets/icons/{icon_name}.svg').read_text(encoding='utf-8').strip()
    return '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true" focusable="false"><path d="M20 11a8 8 0 0 1-8 8H5l-3 3V11a9 9 0 0 1 18 0Z"/></svg>'

def social_navigation():
    labels = {'telegram':'Канал BRAVIS в Telegram', 'vk':'BRAVIS ВКонтакте', 'instagram':'Instagram BRAVIS', 'whatsapp':'Написать в WhatsApp', 'telegramMessage':'Написать в Telegram', 'max':'Написать в MAX', 'viber':'Написать в Viber'}
    groups = [('Соцсети', ('telegram','vk','instagram')), ('Написать нам', ('whatsapp','telegramMessage','max','viber'))]
    result = '<nav class="social-links" aria-label="Сообщества и связь с BRAVIS">'
    for caption, keys in groups:
        links = ''.join(f'<a class="social-icon social-icon--{h(key)}" href="{h(social_links[key])}" target="_blank" rel="noopener noreferrer" data-track="social_{h(key)}_click" aria-label="{h(labels[key])}" title="{h(labels[key])}">{social_icon(key)}</a>' for key in keys if key in social_links)
        if 'max' in keys and max_contact_name and 'max' not in social_links:
            links += '<a class="social-icon social-icon--max" href="/contacts/#max-contact" data-track="max_contact_open" aria-label="Как написать BRAVIS в MAX" title="Как написать BRAVIS в MAX">' + social_icon('max') + '</a>'
        if links:
            result += f'<div class="social-links__group"><span class="social-links__label">{caption}</span><div class="social-links__row">{links}</div></div>'
    return result + '</nav>'

def max_contact_guide():
    if not max_contact_name:
        return ''
    return f'''<section class="section max-contact-section" id="max-contact" aria-labelledby="max-contact-heading"><div class="wrap max-contact-grid"><div><div class="section-label"><span class="line"></span> НАПИСАТЬ НАМ</div><h2 id="max-contact-heading">BRAVIS <em>в MAX.</em></h2><p>Поможем спланировать визит и ответим на ваши вопросы.</p><a class="btn btn--outline" href="https://web.max.ru/" target="_blank" rel="noopener noreferrer" data-track="max_app_open">Открыть MAX ↗</a><p class="max-contact-phone"><span>{h(phone)}</span></p><button type="button" class="btn btn--outline max-contact-copy" data-copy-max-phone="{h(max_contact_phone)}" hidden>Скопировать номер</button><p class="max-contact-status" role="status" aria-live="polite"></p><p class="max-contact-hint">Номер также можно выделить и скопировать.</p></div><div><details class="max-contact-details"><summary>Как найти BRAVIS в MAX</summary><ol class="max-contact-steps"><li>В приложении MAX откройте «Чаты» и строку поиска.</li><li>Введите номер <span class="max-contact-number">{h(max_contact_phone)}</span> и выберите «Найти по номеру».</li><li>Откройте аккаунт «{h(max_contact_name)}» и напишите нам.</li></ol><a class="max-contact-help" href="https://help.max.ru/help/contacts/upravlenie_kontaktami/kak_priglasit_v_max_nuzhnogo_cheloveka" target="_blank" rel="noopener noreferrer">Инструкция MAX по поиску контакта ↗</a></details></div></div></section>'''

rating = str(CONFIG.get('yandexRating', '')).strip()
if not re.fullmatch(r'[0-5]\.[0-9]', rating) or not 0 < float(rating) <= 5:
    raise ValueError('Yandex rating must be the verified value from the restaurant card')
rating_checked = date.fromisoformat(CONFIG['yandexRatingCheckedAt'])

def yandex_award_banner(footer=False):
    label = f'BRAVIS на Яндекс Картах: Хорошее место {CONFIG["yandexGoodPlaceYear"]}, рейтинг {rating.replace(".", ",")}'
    modifier = ' yandex-award--footer' if footer else ''
    return f'''<a class="yandex-award{modifier}" href="{h(yandex_maps_url)}" target="_blank" rel="noopener noreferrer" data-track="reviews_click" aria-label="{h(label)}"><span class="yandex-award__source"><svg width="20" height="24" viewBox="0 0 20 24" fill="none" aria-hidden="true"><path d="M10 22S2 14.7 2 9a8 8 0 1 1 16 0c0 5.7-8 13-8 13Z" stroke="currentColor" stroke-width="1.6"/><circle cx="10" cy="9" r="2.5" fill="currentColor"/></svg>Яндекс Карты</span><span class="yandex-award__rating"><strong>{h(rating.replace('.',','))}</strong><span><span class="yandex-award__stars" aria-hidden="true">★★★★★</span><span class="yandex-award__guests">По оценкам гостей</span></span></span><strong class="yandex-award__title">Хорошее место <span>{h(CONFIG['yandexGoodPlaceYear'])}</span></strong><span class="yandex-award__date">По данным Яндекс Карт на {rating_checked.strftime('%d.%m.%Y')}</span><span class="yandex-award__link">Читать отзывы <svg aria-hidden="true" width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3 13 13 3M3 3h10v10" stroke="currentColor" stroke-width="1.4"/></svg></span></a>'''

def reputation():
    return f'''<section class="reputation section" aria-labelledby="reputation-title"><div class="wrap reputation-grid"><div><div class="section-label"><span class="line"></span> BRAVIS · НА СВЯЗИ</div><h2 id="reputation-title">До встречи<br><em>в BRAVIS.</em></h2><p>Новости и события — в наших сообществах. Напишите нам в мессенджере, чтобы уточнить детали визита.</p>{social_navigation()}</div><div class="reputation-card">{yandex_award_banner()}</div></div></section>'''
reserve_id = str(CONFIG.get('smartReserveId','')).strip()
reserve_link = 'https://reservation.yandex.ru/partner-reserve/forms/' + quote(reserve_id, safe='') if reserve_id else phone_url
reserve_label = 'Забронировать стол' if reserve_id else 'Забронировать по телефону'

# Production guard: an owner approval, verified menu, booking, legal information and
# analytics must all exist before search engines are allowed to index this site.
# Static GitHub previews may still build safely with all these fields missing.
if CONFIG.get('public'):
    blockers = []
    if not domain.startswith('https://') or any(x in domain for x in ('trycloudflare.com','github.io','localhost','127.0.0.1')):
        blockers.append('HTTPS official domain')
    if not CONFIG.get('productionReleaseApproved'):
        blockers.append('explicit owner publication approval')
    if not CONFIG.get('menuPricesApproved'):
        blockers.append('owner verification of prices and menu')
    if not CONFIG.get('legalPolicyApproved'):
        blockers.append('owner approval of complete privacy policy')
    if not reserve_id:
        blockers.append('working SmartReserve ID')
    if not str(CONFIG.get('yandexMetrikaId','')).isdigit():
        blockers.append('Yandex Metrika counter ID')
    if not str(CONFIG.get('verificationYandex','')).strip():
        blockers.append('Yandex Webmaster verification')
    if not str(CONFIG.get('operatorLegalName','')).strip() or not str(CONFIG.get('operatorContactEmail','')).strip():
        blockers.append('legal operator name and contact')
    hours = str(CONFIG.get('hoursText','')).strip().lower()
    if not hours or 'уточняйте' in hours:
        blockers.append('confirmed opening hours')
    if not (ROOT / 'content/menu_media.json').is_file():
        blockers.append('approved five-section menu')
    if not GALLERY.get('hero'):
        blockers.append('real restaurant photos')
    if blockers:
        raise SystemExit('PUBLICATION BLOCKED — ' + '; '.join(blockers))
main_photo = GALLERY.get('hero', '')
interior = GALLERY.get('interior', '')
food = GALLERY.get('food', '')
event_photo = GALLERY.get('events', '')
photos = GALLERY.get('gallery', [])[:9]
if not photos: photos=['/assets/ambience.svg','/assets/cuisine.svg','/assets/wine.svg']

def img(path, fallback):
    return (path if path.startswith('/') else '/' + path) if path else fallback

def button(text, target, alt=False, tracking='', ext=False):
    cls='btn btn--outline' if alt else 'btn btn--primary'
    attrs=' target="_blank" rel="noopener noreferrer"' if ext else ''
    mark=f' data-track="{h(tracking)}"' if tracking else ''
    return f'<a href="{h(target)}" class="{cls}"{attrs}{mark}>{h(text)} <svg aria-hidden="true" width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 13 13 3M3 3h10v10" stroke="currentColor" stroke-width="1.3"/></svg></a>'

def reserve_button(alt=False):
    return button(reserve_label,reserve_link,alt=alt,tracking='reserve_click' if reserve_id else 'reserve_phone_click',ext=bool(reserve_id))

def site_url(path):
    return (domain+path) if domain else ''

def active(page, current):
    return ' aria-current="page"' if page==current else ''

def head(title, desc, route, body_class, noindex=False):
    full_title=f'{title} | BRAVIS — ресторан в Москве' if title else 'BRAVIS — ресторан у метро Динамо, Расковой, 20'
    canonical=site_url(route) if not noindex else ''
    image=site_url(main_photo if main_photo else '/assets/wine-scene.svg')
    robot='index, follow, max-image-preview:large' if published and not noindex else 'noindex, nofollow'
    verification=''
    for k,kind in [('verificationYandex','yandex-verification'),('verificationGoogle','google-site-verification')]:
        if CONFIG.get(k):verification+=f'<meta name="{kind}" content="{h(CONFIG[k])}">'
    metadata=f'''<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#271b20">
<meta name="robots" content="{robot}">
<meta name="description" content="{h(desc)}">
<title>{h(full_title)}</title>
<link rel="icon" type="image/svg+xml" href="/assets/favicon.svg">
<link rel="preload" href="/assets/site.css" as="style">
<link rel="stylesheet" href="/assets/site.css">
<link rel="stylesheet" href="/assets/lunch.css">
<link rel="stylesheet" href="/assets/promotions.css">
<link rel="stylesheet" href="/assets/restaurant-life.css">
<meta property="og:type" content="website"><meta property="og:locale" content="ru_RU">
<meta property="og:site_name" content="BRAVIS"><meta property="og:title" content="{h(full_title)}">
<meta property="og:description" content="{h(desc)}"><meta property="og:image" content="{h(image or '/assets/wine-scene.svg')}">
{f'<meta property="og:url" content="{h(canonical)}"><link rel="canonical" href="{h(canonical)}">' if canonical else ''}
{verification}'''
    schema={"@context":"https://schema.org","@type":"Restaurant","name":"BRAVIS","description":"Армянская и европейская кухня, вино и атмосфера для встреч с близкими","telephone":CONFIG.get('phoneE164',''),"address":{"@type":"PostalAddress","streetAddress":"улица Расковой, 20","addressLocality":"Москва","addressCountry":"RU"},"servesCuisine":["Армянская","Европейская"],"hasMenu":site_url('/menu/') or '/menu/'}
    # Search engines receive exactly the same owner-confirmed opening hours
    # that are displayed in the footer and contact section.
    schedule=CONFIG.get('openingHours') or {}
    if schedule:
        schema['openingHoursSpecification']={
            '@type':'OpeningHoursSpecification',
            'dayOfWeek':schedule.get('days',[]),
            'opens':schedule.get('opens',''),
            'closes':schedule.get('closes','')
        }
    schema['sameAs']=[link for link in (yandex_maps_url,two_gis_url,*(url for key,url in social_links.items() if key not in ('whatsapp','telegramMessage'))) if link]
    if main_photo: schema['image']=site_url(main_photo) or main_photo
    if domain: schema['@id']=site_url('/#restaurant')
    schema['acceptsReservations']=reserve_link
    if official_email: schema['email']=official_email
    if domain:schema['url']=site_url('/')
    analytics = {"ymId": str(CONFIG.get('yandexMetrikaId','')).strip(), "ga4Id": str(CONFIG.get('ga4Id','')).strip()}
    analytics_js = json.dumps(analytics, ensure_ascii=False).replace('<', '\u003c')
    return f'''<!doctype html><html lang="ru"><head>{metadata}<script>window.BRAVIS_ANALYTICS={analytics_js}</script><script type="application/ld+json">{json.dumps(schema, ensure_ascii=False).replace('</','<\\/')}</script></head><body class="{body_class}">'''

def header(current):
    return f'''<a class="skip" href="#main">Перейти к содержимому</a>
<div class="announcement" id="top"><div class="wrap announcement__inner"><span class="announcement__city"><span class="dot"></span> Москва, улица Расковой, 20</span><a href="{h(phone_url)}" data-track="header_phone_click">{h(phone)}</a></div></div>
<header class="site-header"><div class="wrap header-inner">
<a class="logo" href="/" aria-label="BRAVIS — главная"><span class="logo__text">BRAVIS</span><span class="logo__caption">Ресторан · Москва</span></a>
<nav class="desktop-nav" aria-label="Основная навигация"><a href="/events/"{active('events',current)}>События</a><a href="/menu/"{active('menu',current)}>Меню</a><a href="/lunch/"{active('lunch',current)}>Бизнес-ланч</a><a href="/banquets/"{active('banquets',current)}>Банкеты</a><a href="/#delivery">Доставка</a><a href="/contacts/"{active('contacts',current)}>Контакты</a></nav>
<div class="header-actions"><a class="header-menu-link" href="/menu/" data-track="menu_from_header">Меню</a>{reserve_button()}<button type="button" class="menu-toggle" aria-label="Открыть меню" aria-controls="mobile-nav" aria-expanded="false"><span></span><span></span><span></span></button></div>
</div><nav class="mobile-nav" id="mobile-nav" aria-label="Мобильная навигация" hidden><a href="/">Главная</a><a href="/menu/">Меню</a><a href="/lunch/">Бизнес-ланч</a><a href="/banquets/">Банкеты</a><a href="/#delivery">Доставка</a><a href="/#offers">Предложения</a><a href="/events/">Жизнь ресторана</a><a href="/events/#bravis-formats">Дегустации и гастроужины</a><a href="/#loyalty">Карта гостя</a><a href="/contacts/">Контакты</a>{reserve_button()}</nav></header>'''

def footer():
    return f'''<footer class="footer"><div class="wrap footer-grid"><div><a href="/" class="footer-logo">BRAVIS</a><p>Вкус встреч.<br>Тепло Bravis.</p></div><div><span class="footer-caption">Навигация</span><a href="/menu/">Меню</a><a href="/lunch/">Бизнес-ланч</a><a href="/banquets/">Банкеты</a><a href="/#delivery">Доставка</a><a href="/#offers">Предложения</a><a href="/events/">Жизнь ресторана</a><a href="/events/#bravis-formats">Дегустации и гастроужины</a><a href="/#loyalty">Карта гостя</a><a href="/contacts/">Контакты</a></div><div><span class="footer-caption">Ждём в гости</span><p>{h(address)}</p><a href="{h(phone_url)}" data-track="footer_phone_click">{h(phone)}</a><p class="footer-schedule">{h(CONFIG.get('hoursText',''))}</p>{f'<a href="mailto:{h(official_email)}">{h(official_email)}</a>' if official_email else ''}</div><div class="footer-action">{reserve_button()}{social_navigation()}{yandex_award_banner(footer=True)}</div></div><div class="wrap footer-bottom"><span>© {date.today().year} BRAVIS. Все права защищены.</span><a href="/privacy/">Политика обработки персональных данных</a><a href="#top">Наверх ↑</a></div></footer><div class="mobile-bottom-cta"><a href="/menu/">Меню</a><a class="mobile-bottom-cta__primary" href="{h(reserve_link)}" {'target="_blank" rel="noopener noreferrer"' if reserve_id else ''} data-track="{h("reserve_click" if reserve_id else "reserve_phone_click")}">Забронировать</a></div><button class="back-to-top" type="button" aria-label="Наверх страницы" hidden><svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="m5 12 7-7 7 7M12 5v15" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg><span>Наверх</span></button><script src="/assets/site.js" defer></script></body></html>'''

def page(content, title, desc, route, current, body_class='', noindex=False):
    return head(title,desc,route,body_class,noindex)+header(current)+f'<main id="main">{content}</main>'+footer()

# Share the approved menu price between both home offers and the lunch page.
lunch_item = next(item for section in MENU['sections'] if section['id'] == 'lunch' for item in section['items'])
lunch_price = h(lunch_item['price'])
life_settings = json.loads((ROOT / 'content/guest-hub.json').read_text(encoding='utf-8'))
life_data = load_restaurant_life(ROOT / 'content/restaurant-life.json', lunch_price=lunch_item['price'], holiday_overrides=life_settings.get('holidayOverrides', {}))

home=f'''{welcome_strip(welcome_bonus)}
<section class="hero"><div class="wrap hero-grid"><div class="hero-content"><div class="eyebrow"><span class="line"></span> РЕСТОРАН У МЕТРО ДИНАМО</div><h1>Вкус встреч.<br><em>Тепло Bravis.</em></h1><p class="lead">Армянская и европейская кухня на улице Расковой, 20, у метро Динамо. Хорошее вино и атмосфера, в которой хочется остаться чуть дольше.</p><div class="hero-actions">{reserve_button()}{button('Посмотреть меню','/menu/',True,'menu_from_hero')}</div><div class="hero-foot"><span>МОСКВА</span><span class="hero-foot__divider"></span><span>УЛИЦА РАСКОВОЙ, 20</span></div></div><div class="hero-visual"><img class="hero-photo" src="{h(img(main_photo,'/assets/wine-scene.svg'))}" alt="{('Интерьер ресторана BRAVIS' if main_photo else 'Авторская иллюстрация винного вечера в BRAVIS')}" width="800" height="940" fetchpriority="high"><div class="hero-visual__frame"></div><div class="hero-visual__stamp"><span>BRAVIS</span><small>МЕСТО ДЛЯ<br>ВАШИХ ВСТРЕЧ</small></div></div></div><div class="hero-index" aria-hidden="true">01 / BRAVIS</div></section>
{offers_section(welcome_bonus, lunch_price, loona_join_url, whatsapp_url, reserve_button())}
{render_restaurant_life_today(life_data)}
{experiences_section(whatsapp_url)}
{render_restaurant_life_news(life_data, compact=True)}
<section class="intro section" id="about"><div class="wrap intro-grid"><div class="section-label"><span class="line"></span> НАША ФИЛОСОФИЯ</div><div><h2>Не просто ужин.<br><em>Повод встретиться.</em></h2><p>Bravis — про вечера, которые складываются из мелочей: знакомых вкусов, неспешных разговоров и тёплого света. Здесь уютно вдвоём, с семьёй и большой компанией.</p><a class="text-link" href="/contacts/">Найти нас {arrow_up_right}</a></div></div></section>
<section class="feature-section"><div class="wrap feature-grid"><div class="feature-photo"><img src="{h(img(food,'/assets/cuisine.svg'))}" alt="{('Блюда ресторана BRAVIS' if food else 'Авторская иллюстрация блюда')}" width="640" height="520" loading="lazy"></div><div class="feature-copy"><div class="section-label section-label--light"><span class="line"></span> КУХНЯ И ВИНО</div><h2>Вкусы, к которым<br><em>возвращаются.</em></h2><p>Армянские гастрономические традиции и европейская классика. Блюда для общего стола, бокал вина и удовольствие быть вместе.</p>{button('Открыть меню','/menu/',False,'menu_from_feature')}<div class="feature-folio">BRAVIS · FOOD & WINE</div></div></div></section>
<section class="delivery-section" id="delivery" aria-labelledby="delivery-heading">
  <div class="wrap">
    <div class="delivery-panel">
      <div class="delivery-content">
        <div class="section-label section-label--light"><span class="line"></span> BRAVIS · ДОСТАВКА</div>
        <h2 id="delivery-heading">BRAVIS —<br><em>у вас дома.</em></h2>
        <p>Любимые вкусы не обязательно ждать до следующей встречи. Перейдите в Яндекс Еду, чтобы проверить возможность доставки по вашему адресу.</p>
        <a class="delivery-action" href="{h(delivery_url)}" data-track="delivery_click" target="_blank" rel="noopener noreferrer">{h(delivery_button_label)} {arrow_up_right}</a>
        <p class="delivery-disclaimer">{h(delivery_help_text)}</p>
      </div>
      <div class="delivery-visual" aria-hidden="true">
        <span class="delivery-visual__arc delivery-visual__arc--one"></span>
        <span class="delivery-visual__arc delivery-visual__arc--two"></span>
        <div class="delivery-visual__circle"><img class="delivery-dish-art" src="/assets/cuisine.svg" width="260" height="210" alt="Иллюстрация блюда BRAVIS"><span>ВКУС ВСТРЕЧ</span></div>
        <div class="delivery-visual__eyebrow">BRAVIS <i>×</i> ЯНДЕКС ЕДА</div>
      </div>
    </div>
  </div>
</section>
<section class="loyalty-section" id="loyalty" aria-labelledby="loyalty-heading">
  <div class="wrap loyalty-grid">
    <div class="loyalty-copy">
      <div class="section-label"><span class="line"></span> BRAVIS · ПРОГРАММА ЛОЯЛЬНОСТИ</div>
      <h2 id="loyalty-heading">{welcome_bonus} бонусов<br><em>и фирменный десерт.</em></h2>
      <p class="loyalty-choice">Два повода стать ближе.</p><p>{welcome_bonus} бонусных баллов — за установку карты гостя BRAVIS. А фирменный десерт станет сладким поводом заглянуть к нам в выходные. Подробности — в персональном предложении.</p>
      <p class="loyalty-subtext">Карта всегда под рукой — в вашем смартфоне. Узнавайте о персональных предложениях и специальных событиях ресторана.</p>
      {loona_registration_cta}
      <small class="loyalty-smallprint">Баланс и правила использования бонусов — на вашей карте. Приглашение на десерт, дни визита и условия подарка уточняйте в персональном предложении.</small>
    </div>
    <div class="loyalty-art" aria-hidden="true">
      {gift_art()}
      <span class="loyalty-art__caption">ПРИВИЛЕГИИ ГОСТЕЙ BRAVIS</span>
    </div>
  </div>
</section>
<section class="section gallery-section" id="atmosphere"><div class="wrap"><div class="gallery-heading"><div><div class="section-label"><span class="line"></span> АТМОСФЕРА</div><h2>Здесь хорошо<br><em>быть вместе.</em></h2></div><p>Каждая встреча — своя история. А место для неё уже есть.</p></div><div class="gallery-grid">'''
for i,p in enumerate(photos[:3]):
    home+=f'<div class="gallery-item gallery-item--{i+1}"><img src="{h(img(p,"/assets/ambience.svg"))}" alt="{h(("Фотография ресторана BRAVIS" if ("/uploads/" in p) else "Иллюстрация атмосферы ресторана BRAVIS")+" — "+str(i+1))}" loading="lazy" width="650" height="650"></div>'
home+='''</div><p class="gallery-caption">BRAVIS · МОСКВА · РАСКОВОЙ, 20</p></div></section>'''
home+=f'''<section class="events-strip"><div class="wrap events-inner"><div><div class="section-label section-label--light"><span class="line"></span> ОСОБЕННЫЕ ПОВОДЫ</div><h2>Собирайте<br><em>самых близких.</em></h2><p>Семейный праздник, день рождения или вечер с коллегами — обсудим детали и поможем организовать встречу.</p>{button('Банкеты и мероприятия','/banquets/')}</div><div class="events-photo"><img src="{h(img(event_photo,'/assets/ambience.svg'))}" loading="lazy" width="640" height="520" alt="{'Интерьер для встреч в BRAVIS' if event_photo else 'Иллюстрация камерного интерьера'}"></div></div></section>
<section class="visit-section section"><div class="wrap visit-grid"><div><div class="section-label"><span class="line"></span> ПРИХОДИТЕ В ГОСТИ</div><h2>Ваш столик<br><em>уже ждёт.</em></h2><p>{h(address)}</p><p class="subtle">{h(CONFIG.get('hoursText',''))}</p><div class="hero-actions">{reserve_button()}{button('Как добраться',yandex_maps_url,True,ext=True)}</div></div><div class="visit-panel"><span class="visit-panel__mini">МЕСТО ВСТРЕЧ</span><span class="visit-panel__wordmark">BRAVIS</span><span class="visit-panel__detail">ВИНО · КУХНЯ · АТМОСФЕРА</span></div></div></section>'''

# Lunch dishes were transcribed and checked against the restaurant's print artwork.
# The complex price has one source: the existing structured restaurant menu.
lunch_image = LUNCH['sourceImage']
lunch_media = json.loads((ROOT / 'content/menu_media.json').read_text(encoding='utf-8'))
assert any(entry['group'] == 'business' and lunch_image in entry['pages'] for entry in lunch_media['files']), 'Lunch artwork must match the approved menu manifest'

home_lunch = f'''<section class="lunch-teaser" aria-labelledby="home-lunch-title"><div class="wrap lunch-teaser__inner"><div><div class="section-label"><span class="line"></span> BRAVIS · ОБЕДЫ ПО БУДНЯМ</div><h2 id="home-lunch-title">Встретимся <em>за обедом.</em></h2><p>Суп, горячее и напиток — {lunch_price} ₽ за комплекс. Фирменный салат и хлебная корзина к каждому заказу.</p></div>{button('Меню бизнес-ланча','/lunch/',tracking='lunch_from_home')}</div></section>'''
home = home.replace('<section class="delivery-section"', home_lunch + '<section class="delivery-section"', 1)

lunch = f'''<section class="lunch-hero"><div class="wrap lunch-hero__grid"><div><div class="section-label"><span class="line"></span> BRAVIS · БИЗНЕС-ЛАНЧ</div><h1>Пауза на<br><em>вкусный обед.</em></h1><p class="lead">Загляните в BRAVIS по будням с 11:00 до 16:00: на обед с коллегами или просто на время для себя. В праздничные дни уточняйте расписание у ресторана.</p><div class="lunch-price"><strong>{lunch_price} ₽</strong><span>суп, горячее и напиток</span></div><div class="hero-actions">{button('Выбрать день','#lunch-menu',tracking='lunch_menu_click')}{button('Уточнить ланч',phone_url,True,'lunch_phone_click')}</div></div><figure class="lunch-hero__photo"><img src="{h(img(interior,'/assets/ambience.svg'))}" alt="Интерьер ресторана BRAVIS для обеда и встреч" width="740" height="900" fetchpriority="high"><figcaption>МОСКВА · РАСКОВОЙ, 20</figcaption></figure></div></section>
<section class="lunch-menu" id="lunch-menu" aria-labelledby="lunch-menu-title"><div class="wrap"><div class="lunch-menu__intro"><div class="section-label"><span class="line"></span> МЕНЮ ПО ДНЯМ НЕДЕЛИ</div><h2 id="lunch-menu-title">Каждый день —<br><em>свой вкус.</em></h2><p>Выберите суп, горячее блюдо и напиток. Фирменный салат и хлебная корзина подаются к каждому заказу.</p></div><div class="lunch-tabs" role="tablist" aria-label="День недели для бизнес-ланча" data-lunch-tabs hidden>'''
for day in LUNCH['days']:
    lunch += f'<button type="button" role="tab" id="lunch-tab-{h(day["id"])}" aria-controls="lunch-{h(day["id"])}" aria-selected="false" tabindex="-1" aria-label="{h(day["name"])}"><span class="lunch-tabs__long" aria-hidden="true">{h(day["name"])}</span><span class="lunch-tabs__short" aria-hidden="true">{h(day["shortName"])}</span></button>'
lunch += '</div>'
for day in LUNCH['days']:
    lunch += f'<section class="lunch-day" id="lunch-{h(day["id"])}"><h3>{h(day["name"])}</h3><div class="lunch-courses">'
    for label, items in [('Суп на выбор', day['soups']), ('Горячее на выбор', day['mains']), ('Напиток на выбор', LUNCH['drinks'])]:
        lunch += f'<div class="lunch-course"><h4>{h(label)}</h4><ul>' + ''.join(f'<li>{h(item)}</li>' for item in items) + '</ul></div>'
    lunch += '</div></section>'
lunch += f'''<p class="lunch-included"><strong>К каждому заказу:</strong> {h(' и '.join(LUNCH['included']).lower())}.</p><details class="lunch-original"><summary>Посмотреть оригинальное меню бизнес-ланча</summary><div class="lunch-original__body"><a href="{h(lunch_image)}" target="_blank" rel="noopener noreferrer" data-track="lunch_print_open" aria-label="Открыть оригинальное меню бизнес-ланча крупно в новой вкладке"><img src="{h(lunch_image)}" alt="Печатное меню бизнес-ланча BRAVIS: комплекс {lunch_price} рублей и блюда по будням" width="1344" height="1875" loading="lazy"></a><p>Нажмите на изображение, чтобы открыть его крупно.</p></div></details></div></section>
<section class="lunch-visit"><div class="wrap lunch-visit__grid"><div><div class="section-label"><span class="line"></span> ЖДЁМ НА ОБЕД</div><h2>Ваш перерыв.<br><em>Наше гостеприимство.</em></h2><p>{h(address)}</p></div><div><p>Время подачи ланча, наличие блюд, актуальные цены и информацию об аллергенах уточняйте у команды ресторана.</p><div class="hero-actions">{reserve_button()}{button('Позвонить в BRAVIS',phone_url,True,'lunch_phone_click')}</div></div></div></section><script src="/assets/lunch.js" defer></script>'''

menu_top=f'''<section class="page-hero page-hero--light"><div class="wrap"><div class="section-label"><span class="line"></span> BRAVIS · КУХНЯ И ВИНО</div><h1>Наше <em>меню.</em></h1><p>Армянские традиции, европейские вкусы и вино, которое дополняет встречу.</p></div><div class="wrap menu-hero-offer"><span>ГОРЯЧИЙ ПОВОД СОБРАТЬСЯ</span><h2>Хинкальный <em>безлимит.</em></h2><p>Любимые хинкали — свежими горячими порциями. Действующие условия уточним перед бронированием.</p><div class="hero-actions">{reserve_button()}{button('Узнать условия',whatsapp_url,True,'khinkali_menu_contact',ext=True)}</div></div></section><section class="section menu-section"><div class="wrap">'''
menu_top += '<a class="lunch-link" href="/lunch/" data-track="lunch_from_menu">Бизнес-ланч: посмотреть меню по дням недели ↗</a>'
sections=[section for section in MENU.get('sections',[]) if section.get('id') != 'seasonal-dishes']
available=[s for s in sections if s.get('items')]
if available:
    bar_sections=[s for s in available if s.get('id','').startswith('bar-')]
    kitchen_sections=[s for s in available if s not in bar_sections]
    menu_top+='<nav class="menu-filter" aria-label="Разделы меню">' + ''.join(f'<a href="#{h(s.get("id","category"))}">{h(s.get("name","Раздел"))}</a>' for s in kitchen_sections)
    if bar_sections:
        menu_top+='<a href="#bar-menu">Бар и напитки</a>'
    menu_top+='</nav>'
    for s in available:
        if bar_sections and s is bar_sections[0]:
            menu_top+='<div id="bar-menu"><div class="menu-category-header"><div class="section-label"><span class="line"></span> БАРНАЯ КАРТА BRAVIS</div><h2>Бар и напитки</h2><p>Названия, цены и объёмы из печатной барной карты ресторана.</p></div><nav class="menu-filter" aria-label="Разделы барной карты">' + ''.join(f'<a href="#{h(b.get("id","category"))}">{h(b.get("name","Раздел"))}</a>' for b in bar_sections) + '</nav></div>'
        menu_top+=f'<div class="menu-category" id="{h(s.get("id","category"))}"><div class="menu-category-header"><div class="section-label"><span class="line"></span> МЕНЮ BRAVIS</div><h2>{h(s.get("name","Раздел"))}</h2><p>{h(s.get("note",""))}</p></div><div class="menu-items">'
        for item in s['items']:
            price = str(item.get('price','')).strip()
            price_str = ('<span class="dish-price">'+h(price)+' ₽</span>') if price else ''
            image = item.get('image','')
            photo_html=f'<img loading="lazy" src="{h(image)}" alt="{h(item.get("name","Блюдо"))}" width="140" height="140">' if image else ''
            weight = f'<span class="dish-weight">{h(item.get("weight",""))}</span>' if item.get('weight') else ''
            menu_top+=f'<article class="dish">{photo_html}<div class="dish-body"><div class="dish-title"><h3>{h(item.get("name",""))}</h3>{price_str}</div><p>{h(item.get("description",""))}</p>{weight}</div></article>'
        menu_top+='</div></div>'
else:
    menu_top+=f'''<div class="menu-placeholder"><div class="menu-placeholder__art"><img src="/assets/cuisine.svg" width="640" height="520" alt="Авторская иллюстрация блюда"></div><div><span class="overline">СКОРО НА САЙТЕ</span><h2>Выбирайте по вкусу.<br><em>Мы подскажем.</em></h2><p>Электронное меню обновляется. Актуальные блюда, винную карту и цены сейчас можно уточнить у команды ресторана по телефону.</p>{button('Позвонить и уточнить меню',phone_url)}</div></div>'''
menu_top+=f'''<div class="menu-bottom-note">Состав и наличие блюд могут меняться. Уточняйте актуальную информацию и аллергены у сотрудников ресторана. <a href="{h(phone_url)}">{h(phone)}</a></div></div></section>'''

banquet=f'''<section class="page-hero page-hero--dark"><div class="wrap page-hero-grid"><div><div class="section-label section-label--light"><span class="line"></span> СОБЫТИЯ В BRAVIS</div><h1>Встречи,<br><em>которые помнят.</em></h1><p>Дни рождения, камерные праздники, семейные ужины и встречи с коллегами — в атмосфере тепла и гостеприимства.</p>{button('Обсудить банкет в WhatsApp',whatsapp_url,ext=True,tracking='banquet_contact_click')}</div><div class="page-hero-photo"><img src="{h(img(event_photo,'/assets/ambience.svg'))}" alt="{'Зал ресторана BRAVIS' if event_photo else 'Иллюстрация ресторанного зала'}" width="640" height="520"></div></div></section>
{banquet_details(whatsapp_url)}
<section class="section"><div class="wrap"><div class="section-label"><span class="line"></span> ВАШ ФОРМАТ</div><h2>Не только меню.<br><em>Время вместе.</em></h2><p>Обсудим, что нужно вашей встрече: праздничный стол, приватность или пространство для съёмок. Стоимость и доступность согласуем по заявке.</p><div class="banquet-options"><article><h3>Праздничный стол</h3><p>Подберём блюда, подачу и обслуживание под ваш повод.</p>{button('Обсудить условия',whatsapp_url+'?text='+quote('Хочу обсудить банкетное меню и стоимость мероприятия.'),True,'banquet_format_contact',ext=True)}</article><article><h3>Аренда и приватность</h3><p>Обсудим возможность аренды, время и условия проведения закрытой встречи.</p>{button('Обсудить условия',whatsapp_url+'?text='+quote('Хочу обсудить возможность аренды и приватный формат встречи.'),True,'banquet_format_contact',ext=True)}</article><article><h3>Встречи и съёмки</h3><p>Расскажите о деловой встрече или съёмочном дне — обсудим формат и требования к площадке.</p>{button('Обсудить условия',whatsapp_url+'?text='+quote('Хочу обсудить площадку BRAVIS для встречи или съёмок.'),True,'banquet_format_contact',ext=True)}</article></div></div></section>
<section class="banner-dark"><div class="wrap banner-inner"><div><span class="overline">BRAVIS · ВАШЕ СОБЫТИЕ</span><h2>Начнём<br><em>с ваших пожеланий.</em></h2><p>Дату, меню и стоимость согласуем с вами до подтверждения мероприятия.</p></div><div>{button('Обсудить банкет в WhatsApp',whatsapp_url,ext=True,tracking='banquet_contact_click')}</div></div></section>'''

events = render_restaurant_life_page(life_data)
events += '<section class="section life-gallery"><div class="wrap"><div class="section-label"><span class="line"></span> АТМОСФЕРА В КАДРЕ</div><h2>Место для <em>ваших историй.</em></h2><p>Залы и детали BRAVIS. Фотографии интерьера ресторана.</p><div class="gallery-grid">'
for i, photo in enumerate(photos[:3]):
    events += f'<a class="gallery-item gallery-item--{i+1}" href="{h(img(photo, "/assets/ambience.svg"))}" target="_blank" rel="noopener noreferrer"><img src="{h(img(photo, "/assets/ambience.svg"))}" alt="Интерьер BRAVIS — фотография {i+1}" width="650" height="650" loading="lazy"></a>'
events += '</div><a class="text-link" href="https://rutube.ru/video/c2c357acb4f02a17b8ac298d603e38be/" target="_blank" rel="noopener noreferrer">Посмотреть видеосюжет о BRAVIS ↗</a><p class="subtle">Архивный сюжет о ресторане. Фотографии выше показывают интерьер, а не съёмки фильма.</p></div></section>'
events += '<section class="banner-dark"><div class="wrap banner-inner"><div><span class="overline">ВАШ ПОВОД ДЛЯ ВСТРЕЧИ</span><h2>Пусть следующая история<br><em>будет вашей.</em></h2></div><div>' + reserve_button() + '</div></div></section>'

contacts=f'''<section class="page-hero page-hero--light"><div class="wrap"><div class="section-label"><span class="line"></span> КОНТАКТЫ И МАРШРУТ</div><h1>До <em>встречи.</em></h1><p>Находите время для близких. А мы найдём для вас место.</p></div></section><section class="section"><div class="wrap contacts-grid"><div class="contacts-info"><div class="contact-row"><span>АДРЕС</span><h2>{h(address)}</h2></div><div class="contact-row"><span>ТЕЛЕФОН</span><a class="contact-big contact-value--phone" href="{h(phone_url)}" data-track="contacts_phone_click">{h(phone)}</a></div><div class="contact-row"><span>ОФИЦИАЛЬНАЯ ПОЧТА</span><a class="contact-big contact-value--email" href="mailto:{h(official_email)}">{h(official_email)}</a></div><div class="contact-row"><span>ВРЕМЯ РАБОТЫ</span><p>{h(CONFIG.get('hoursText',''))}</p></div><div class="contact-actions">{reserve_button()}{button('Открыть маршрут',yandex_maps_url,True,ext=True)}{button('Карточка BRAVIS в 2ГИС',two_gis_url,True,tracking='two_gis_click',ext=True) if two_gis_url else ''}</div></div><div class="map-card"><div class="map-card__line"></div><div class="map-card__inner"><span>BRAVIS</span><p>МОСКВА</p><p class="map-card__address">РАСКОВОЙ, 20</p><div class="map-pin">⌖</div><a href="{h(yandex_maps_url)}" target="_blank" rel="noopener noreferrer">Открыть на Яндекс Картах ↗</a>{f'<a href="{h(two_gis_url)}" target="_blank" rel="noopener noreferrer" data-track="two_gis_click">Открыть в 2ГИС ↗</a>' if two_gis_url else ''}</div></div></div></section>'''

home += reputation()
contacts += contact_invitation(reserve_button())
contacts += max_contact_guide()
contacts += reputation()
contacts = contacts.replace('<div class="map-card"><div class="map-card__line">', f'<div class="map-card" data-yandex-widget="map" data-yandex-org="{h(maps_org_id)}"><div class="map-card__line">', 1)
contacts = contacts.replace('<div class="map-pin">⌖</div>', '<div class="map-pin" aria-hidden="true">⌖</div><button type="button" class="external-widget-load" data-track="map_load">Показать карту здесь</button><small>Загрузится карта Яндекса. Сервис получит технические данные вашего браузера.</small>', 1)
not_found = '<section class="page-hero page-hero--light"><div class="wrap"><div class="section-label">BRAVIS · 404</div><h1>Страница <em>не найдена.</em></h1><p>Возможно, адрес изменился. Загляните в меню или вернитесь на главную.</p><div class="hero-actions">' + button('На главную','/') + button('Посмотреть меню','/menu/',True) + '</div></div></section>'

privacy_title='Политика обработки персональных данных'
operator = CONFIG.get('operatorLegalName','').strip()
legal_email = CONFIG.get('operatorContactEmail','').strip()
legal_address = CONFIG.get('operatorPostalAddress','').strip()
legal_inn = CONFIG.get('operatorInn','').strip()
legal_ogrn = CONFIG.get('operatorOgrn','').strip()
privacy=f'''<section class="page-hero page-hero--light"><div class="wrap"><div class="section-label"><span class="line"></span> ДОКУМЕНТЫ</div><h1>Персональные <em>данные.</em></h1></div></section><section class="section"><div class="wrap policy"><h2>{privacy_title}</h2>'''
if not CONFIG.get('legalPolicyApproved'):
    privacy+='''<p class="policy-warning"><strong>Проект документа.</strong> Эта редакция подготовлена для согласования с владельцем ресторана. До официальной публикации сайта необходимо проверить фактические процессы обработки данных, используемый хостинг, сроки хранения и применимые требования законодательства. Документ пока не утверждён.</p>'''
if not operator:
    privacy+='''<p class="policy-warning">Юридическое лицо и контакты оператора пока не указаны.</p>'''
else:
    privacy+=f'''<h3>1. Сведения об операторе</h3><p><strong>{h(operator)}</strong> (ИНН {h(legal_inn)}, ОГРН {h(legal_ogrn)}).</p><p>Адрес для письменных обращений: {h(legal_address)}.</p><p>Контактный e-mail: <a href="mailto:{h(legal_email)}">{h(legal_email)}</a>. Юридический адрес оператора не является адресом ресторана: BRAVIS принимает гостей по адресу {h(address)}.</p>'''
privacy+='''<h3>2. Сведения, возникающие при использовании сайта</h3>
<p>На данном сайте нет собственной формы регистрации, заказа или сбора контактных данных. Для отображения страниц могут обрабатываться технические сведения о запросах браузера — IP-адрес, сведения об устройстве и программе, дата, время, запрошенные страницы и технические журналы провайдера хостинга. Конкретный состав журналов и сроки их хранения требуют отдельного подтверждения у хостинг-провайдера перед запуском официального домена.</p>
<h3>3. Бронирование и телефонные обращения</h3>
<p>Кнопка «Забронировать» ведёт на внешний сервис Яндекс СмартРезерв. Если посетитель решит сообщить там имя, телефон или другие данные, соответствующая форма и условия обработки относятся к используемому сервису и к взаимоотношениям с рестораном. Сайт BRAVIS не записывает эти сведения в собственную базу через данную кнопку.</p>
<p>Нажатие на номер телефона открывает набор номера на устройстве посетителя; само по себе оно не передаёт имя или номер посетителя в форму нашего сайта.</p>
<h3>4. Программа лояльности BRAVIS</h3>
<p>В рамках программы лояльности ресторан использует сервис Loona. На сайте BRAVIS размещается информация о карте гостя и, после проверки оператором, ссылка на отдельную страницу регистрации Loona. Форма на нашем сайте не создаётся. При переходе на внешний сервис гость самостоятельно знакомится с условиями программы, правилами обработки персональных данных и уведомлений и решает, оформлять ли карту. Состав собираемых сведений, основания обработки, роли сторон и порядок получения согласий подлежат проверке оператором до официальной публикации.</p>
<h3>5. Необязательная аналитика и настройки cookie</h3>
<p>На сайте предусмотрена Яндекс Метрика (счётчик № 113768615), которая загружается только после выбора «Разрешить» в уведомлении об аналитике. После согласия возможна обработка технической информации о посещениях и событиях (например, открытие меню, переход к бронированию, нажатие на телефон). Текстовые поля с персональными данными для этих событий на сайте не предусмотрены.</p>
<p>Выбор посетителя сохраняется в локальном хранилище браузера, чтобы не спрашивать разрешение при каждом переходе. Отказ сохраняется аналогично; до согласия скрипт Яндекс Метрики не загружается кодом сайта. Изменить выбор можно через «Настройки cookie» внизу страниц; после смены выбора страница перезагрузится.</p>
<h3>6. Цели и основания обработки</h3>
<p>Предполагаемые цели: техническое предоставление страниц и обеспечение работы сайта; измерение посещаемости и интереса к разделам — только по отдельному выбору посетителя. Правовые основания, перечень лиц, имеющих доступ к сведениям, а также схема обработки и хранения должны быть уточнены перед выпуском окончательной редакции.</p>
<h3>7. Передача данных и сроки хранения</h3>
<p>Данные могут технически обрабатываться провайдерами размещения сайта, а после отдельного согласия — сервисом Яндекс Метрика. Бронирование происходит на сайте внешнего сервиса. Конкретные договорные роли поставщиков услуг, место хранения технических журналов, сроки хранения и процедуры удаления должны быть проверены владельцем сайта и ответственным за персональные данные до промышленного запуска.</p>
<h3>8. Обращения и изменение согласия</h3>
<p>По вопросам обработки персональных данных, получения сведений об обработке, исправления или удаления данных и отзыва согласия можно обратиться к оператору по указанному выше адресу или e-mail. Отзыв согласия на необязательную аналитику также доступен через ссылку «Настройки cookie» в нижней части сайта.</p>
<p>Настоящий документ является рабочим проектом и должен быть актуализирован и утверждён оператором до публикации BRAVIS на официальном домене.</p></div></section>'''

# Preserve the policy already published in production-timeweb commit 105bf7f.
if CONFIG.get('legalPolicyApproved'):
    privacy = (ROOT / 'content/privacy.approved.html').read_text(encoding='utf-8')

PAGES={
  'index.html':page(home,'','Ресторан BRAVIS на Расковой, 20 в Москве: армянская и европейская кухня, бизнес-ланч за 690 ₽ и 500 бонусов за установку карты гостя. Меню и бронирование.','/','home','home-page'),
  'menu/index.html':page(menu_top,'Меню и цены — армянская и европейская кухня','Меню ресторана BRAVIS в Москве: армянская и европейская кухня, винная карта. Актуальные блюда и информация.','/menu/','menu','menu-page'),
  'lunch/index.html':page(lunch,'Бизнес-ланч за 690 ₽ на Расковой, 20','Бизнес-ланч в BRAVIS на Расковой, 20: меню по будням, суп, горячее и напиток. Оригинальное меню и бронирование стола.','/lunch/','lunch','lunch-page'),
  'banquets/index.html':page(banquet,'Банкеты и мероприятия','Праздники, камерные банкеты, дни рождения и семейные встречи в ресторане BRAVIS, Москва, улица Расковой, 20.','/banquets/','banquets'),
  'events/index.html':page(events,'Жизнь ресторана — события и новости','События и новости BRAVIS: дегустации, гастроужины, встречи и жизнь ресторана на Расковой, 20.','/events/','events','events-page'),
  'contacts/index.html':page(contacts,'Адрес и контакты','Ресторан BRAVIS: Москва, улица Расковой, 20. Телефон +7 (989) 571-99-77. Как добраться и забронировать стол.','/contacts/','contacts'),
  '404.html':page(not_found,'Страница не найдена','Страница не найдена. Меню, контакты и бронирование ресторана BRAVIS.','/404.html','','not-found-page',noindex=True),
  'privacy/index.html':page(privacy,privacy_title,'Сведения об обработке персональных данных на сайте ресторана BRAVIS.','/privacy/','privacy')
}

# Reuse the guest hub prepared by the existing marketing executor.
from guest_hub import render_guest_hub
hub_settings = json.loads((ROOT / 'content/guest-hub.json').read_text(encoding='utf-8'))
PAGES['go/index.html'] = render_guest_hub(
    CONFIG, hub_settings,
    head('Меню и карта гостя', 'Меню, карта гостя и следующий визит в BRAVIS на Расковой, 20.', '/go/', 'guest-hub-page'),
    lunch_item['price'], reserve_link,
)

if DIST.exists():shutil.rmtree(DIST)
DIST.mkdir()
shutil.copytree(ROOT/'public', DIST, dirs_exist_ok=True)
asset_versions = {}
def version_asset(match):
    path = match.group(2)
    if path not in asset_versions:
        asset = ROOT / 'public' / path.lstrip('/')
        asset_versions[path] = hashlib.sha256(asset.read_bytes()).hexdigest()[:12]
    return match.group(1) + path + '?v=' + asset_versions[path] + match.group(3)

for filename,content in PAGES.items():
    if filename in ('index.html', 'events/index.html'):
        content = content.replace('</body>', '<script type="application/json" id="restaurant-life-data">' + restaurant_life_json(life_data) + '</script><script src="/assets/restaurant-life.js" defer></script></body>')
    # Fresh HTML requests the matching stylesheet/script even in a warm browser cache.
    content = re.sub(r"((?:href|src)=[\"'])(/assets/[A-Za-z0-9_./-]+\.(?:css|js))([\"'])", version_asset, content)
    target=DIST/filename
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(content,encoding='utf-8')
# Don't enable indexing before owner authorizes publication and sets domain/legal data.
(DIST/'robots.txt').write_text(('User-agent: *\nAllow: /\nSitemap: '+site_url('/sitemap.xml')+'\n') if published else 'User-agent: *\nDisallow: /\n', encoding='utf-8')
if published:
    uris=['/','/menu/','/lunch/','/banquets/','/events/','/contacts/','/privacy/','/go/']
    sitemap='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+h(site_url(uri))+'</loc></url>' for uri in uris)+'</urlset>'
    (DIST/'sitemap.xml').write_text(sitemap,encoding='utf-8')
(DIST/'assets/restaurant-life.json').write_text(restaurant_life_json(life_data), encoding='utf-8')
(DIST/'.nojekyll').write_text('',encoding='utf-8')
print('Built',len(PAGES),'pages in',DIST)
print('Publication:', 'PUBLIC' if published else 'PREVIEW ONLY (noindex)')
print('SmartReserve:', 'connected' if reserve_id else 'pending ID; calls by phone work')
print('Photos:', sum(bool(v) for v in (main_photo, interior, food, event_photo)), 'selected roles')
