#!/usr/bin/env python3
"""Build the Bravis static website. No pip/npm packages are required."""
import json, html, re, shutil
from pathlib import Path
from urllib.parse import quote
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
CONFIG = json.loads((ROOT / 'site.config.json').read_text(encoding='utf-8'))
MENU = json.loads((ROOT / 'content/menu.json').read_text(encoding='utf-8'))
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
delivery_help_text = ('Оформление и условия доставки — в сервисе Яндекс Еда. Доступность зависит от вашего адреса.' if delivery_has_direct_link
                      else 'Выберите адрес доставки и найдите BRAVIS в Яндекс Еде. Прямой переход к меню ресторана пока уточняется.')
domain = CONFIG.get('domain','').strip().rstrip('/')
if domain and not domain.startswith(('https://','http://')): domain = 'https://' + domain
published = bool(CONFIG.get('public') and domain)
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
    return f'<a href="{h(target)}" class="{cls}"{attrs}{mark}>{h(text)} <span aria-hidden="true">↗</span></a>'

def reserve_button(alt=False):
    return button(reserve_label,reserve_link,alt=alt,tracking='reserve_click' if reserve_id else 'reserve_phone_click',ext=bool(reserve_id))

def site_url(path):
    return (domain+path) if domain else ''

def active(page, current):
    return ' aria-current="page"' if page==current else ''

def head(title, desc, route, body_class):
    full_title=f'{title} | BRAVIS — ресторан в Москве' if title else 'BRAVIS — ресторан на Расковой, 20 в Москве'
    canonical=site_url(route)
    image=site_url(main_photo if main_photo else '/assets/wine-scene.svg')
    robot='index, follow, max-image-preview:large' if published else 'noindex, nofollow'
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
    schema['sameAs']=[link for link in (yandex_maps_url,two_gis_url) if link]
    if official_email: schema['email']=official_email
    if domain:schema['url']=site_url('/')
    analytics = {"ymId": str(CONFIG.get('yandexMetrikaId','')).strip(), "ga4Id": str(CONFIG.get('ga4Id','')).strip()}
    analytics_js = json.dumps(analytics, ensure_ascii=False).replace('<', '\u003c')
    return f'''<!doctype html><html lang="ru"><head>{metadata}<script>window.BRAVIS_ANALYTICS={analytics_js}</script><script type="application/ld+json">{json.dumps(schema, ensure_ascii=False).replace('</','<\\/')}</script></head><body class="{body_class}">'''

def header(current):
    return f'''<a class="skip" href="#main">Перейти к содержимому</a>
<div class="announcement"><div class="wrap announcement__inner"><span class="announcement__city"><span class="dot"></span> Москва, улица Расковой, 20</span><a href="{h(phone_url)}" data-track="header_phone_click">{h(phone)}</a></div></div>
<header class="site-header" id="top"><div class="wrap header-inner">
<a class="logo" href="/" aria-label="BRAVIS — главная"><span class="logo__text">BRAVIS</span><span class="logo__caption">Ресторан · Москва</span></a>
<nav class="desktop-nav" aria-label="Основная навигация"><a href="/"{active('home',current)}>Главная</a><a href="/menu/"{active('menu',current)}>Меню</a><a href="/banquets/"{active('banquets',current)}>Банкеты</a><a href="/#delivery">Доставка</a><a href="/contacts/"{active('contacts',current)}>Контакты</a></nav>
<div class="header-actions">{reserve_button()}<button type="button" class="menu-toggle" aria-label="Открыть меню" aria-controls="mobile-nav" aria-expanded="false"><span></span><span></span><span></span></button></div>
</div><nav class="mobile-nav" id="mobile-nav" aria-label="Мобильная навигация" hidden><a href="/">Главная</a><a href="/menu/">Меню</a><a href="/banquets/">Банкеты</a><a href="/#delivery">Доставка</a><a href="/contacts/">Контакты</a>{reserve_button()}</nav></header>'''

def footer():
    return f'''<footer class="footer"><div class="wrap footer-grid"><div><a href="/" class="footer-logo">BRAVIS</a><p>Вкус встреч.<br>Тепло Bravis.</p></div><div><span class="footer-caption">Навигация</span><a href="/menu/">Меню</a><a href="/banquets/">Банкеты</a><a href="/#delivery">Доставка</a><a href="/contacts/">Контакты</a></div><div><span class="footer-caption">Ждём в гости</span><p>{h(address)}</p><a href="{h(phone_url)}" data-track="footer_phone_click">{h(phone)}</a><p class="footer-schedule">{h(CONFIG.get('hoursText',''))}</p>{f'<a href="mailto:{h(official_email)}">{h(official_email)}</a>' if official_email else ''}</div><div class="footer-action">{reserve_button()}</div></div><div class="wrap footer-bottom"><span>© {date.today().year} BRAVIS. Все права защищены.</span><a href="/privacy/">Политика обработки персональных данных</a><a href="#top">Наверх ↑</a></div></footer><div class="mobile-bottom-cta"><a href="/menu/">Меню</a><a class="mobile-bottom-cta__primary" href="{h(reserve_link)}" {'target="_blank" rel="noopener noreferrer"' if reserve_id else ''} data-track="{h("reserve_click" if reserve_id else "reserve_phone_click")}">Забронировать</a></div><script src="/assets/site.js" defer></script></body></html>'''

def page(content, title, desc, route, current, body_class=''):
    return head(title,desc,route,body_class)+header(current)+f'<main id="main">{content}</main>'+footer()

home=f'''<section class="hero"><div class="wrap hero-grid"><div class="hero-content"><div class="eyebrow"><span class="line"></span> РЕСТОРАН В СЕРДЦЕ МОСКВЫ</div><h1>Вкус встреч.<br><em>Тепло Bravis.</em></h1><p class="lead">Армянская и европейская кухня, хорошее вино и атмосфера, в которой хочется остаться чуть дольше.</p><div class="hero-actions">{reserve_button()}{button('Посмотреть меню','/menu/',True,'menu_from_hero')}</div><div class="hero-foot"><span>МОСКВА</span><span class="hero-foot__divider"></span><span>УЛИЦА РАСКОВОЙ, 20</span></div></div><div class="hero-visual"><img class="hero-photo" src="{h(img(main_photo,'/assets/wine-scene.svg'))}" alt="{('Интерьер ресторана BRAVIS' if main_photo else 'Авторская иллюстрация винного вечера в BRAVIS')}" width="800" height="940" fetchpriority="high"><div class="hero-visual__frame"></div><div class="hero-visual__stamp"><span>BRAVIS</span><small>МЕСТО ДЛЯ<br>ВАШИХ ВСТРЕЧ</small></div></div></div><div class="hero-index" aria-hidden="true">01 / BRAVIS</div></section>
<section class="intro section" id="about"><div class="wrap intro-grid"><div class="section-label"><span class="line"></span> НАША ФИЛОСОФИЯ</div><div><h2>Не просто ужин.<br><em>Повод встретиться.</em></h2><p>Bravis — про вечера, которые складываются из мелочей: знакомых вкусов, неспешных разговоров и тёплого света. Здесь уютно вдвоём, с семьёй и большой компанией.</p><a class="text-link" href="/contacts/">Найти нас <span aria-hidden="true">↗</span></a></div></div></section>
<section class="feature-section"><div class="wrap feature-grid"><div class="feature-photo"><img src="{h(img(food,'/assets/cuisine.svg'))}" alt="{('Блюда ресторана BRAVIS' if food else 'Авторская иллюстрация блюда')}" width="640" height="520" loading="lazy"></div><div class="feature-copy"><div class="section-label section-label--light"><span class="line"></span> КУХНЯ И ВИНО</div><h2>Вкусы, к которым<br><em>возвращаются.</em></h2><p>Армянские гастрономические традиции и европейская классика. Блюда для общего стола, бокал вина и удовольствие быть вместе.</p>{button('Открыть меню','/menu/',False,'menu_from_feature')}<div class="feature-folio">BRAVIS · FOOD & WINE</div></div></div></section>
<section class="delivery-section" id="delivery" aria-labelledby="delivery-heading">
  <div class="wrap">
    <div class="delivery-panel">
      <div class="delivery-content">
        <div class="section-label section-label--light"><span class="line"></span> BRAVIS · ДОСТАВКА</div>
        <h2 id="delivery-heading">BRAVIS —<br><em>у вас дома.</em></h2>
        <p>Любимые вкусы не обязательно ждать до следующей встречи. Перейдите в Яндекс Еду, чтобы проверить возможность доставки по вашему адресу.</p>
        <a class="delivery-action" href="{h(delivery_url)}" data-track="delivery_click" target="_blank" rel="noopener noreferrer">{h(delivery_button_label)} <span aria-hidden="true">↗</span></a>
        <p class="delivery-disclaimer">{h(delivery_help_text)}</p>
      </div>
      <div class="delivery-visual" aria-hidden="true">
        <span class="delivery-visual__arc delivery-visual__arc--one"></span>
        <span class="delivery-visual__arc delivery-visual__arc--two"></span>
        <div class="delivery-visual__circle"><span class="delivery-visual__icon">B</span><span>ВКУС ВСТРЕЧ</span></div>
        <div class="delivery-visual__eyebrow">BRAVIS <i>×</i> ЯНДЕКС ЕДА</div>
      </div>
    </div>
  </div>
</section>
<section class="section gallery-section" id="atmosphere"><div class="wrap"><div class="gallery-heading"><div><div class="section-label"><span class="line"></span> АТМОСФЕРА</div><h2>Здесь хорошо<br><em>быть вместе.</em></h2></div><p>Каждая встреча — своя история. А место для неё уже есть.</p></div><div class="gallery-grid">'''
for i,p in enumerate(photos[:3]):
    home+=f'<div class="gallery-item gallery-item--{i+1}"><img src="{h(img(p,"/assets/ambience.svg"))}" alt="{h(("Фотография ресторана BRAVIS" if ("/uploads/" in p) else "Иллюстрация атмосферы ресторана BRAVIS")+" — "+str(i+1))}" loading="lazy" width="650" height="650"></div>'
home+='''</div><p class="gallery-caption">BRAVIS · МОСКВА · РАСКОВОЙ, 20</p></div></section>'''
home+=f'''<section class="events-strip"><div class="wrap events-inner"><div><div class="section-label section-label--light"><span class="line"></span> ОСОБЕННЫЕ ПОВОДЫ</div><h2>Собирайте<br><em>самых близких.</em></h2><p>Семейный праздник, день рождения или вечер с коллегами — обсудим детали и поможем организовать встречу.</p>{button('Банкеты и мероприятия','/banquets/')}</div><div class="events-photo"><img src="{h(img(event_photo,'/assets/ambience.svg'))}" loading="lazy" width="640" height="520" alt="{'Интерьер для встреч в BRAVIS' if event_photo else 'Иллюстрация камерного интерьера'}"></div></div></section>
<section class="visit-section section"><div class="wrap visit-grid"><div><div class="section-label"><span class="line"></span> ПРИХОДИТЕ В ГОСТИ</div><h2>Ваш столик<br><em>уже ждёт.</em></h2><p>{h(address)}</p><p class="subtle">{h(CONFIG.get('hoursText',''))}</p><div class="hero-actions">{reserve_button()}{button('Как добраться',yandex_maps_url,True,ext=True)}</div></div><div class="visit-panel"><span class="visit-panel__mini">МЕСТО ВСТРЕЧ</span><span class="visit-panel__wordmark">BRAVIS</span><span class="visit-panel__detail">ВИНО · КУХНЯ · АТМОСФЕРА</span></div></div></section>'''

menu_top='''<section class="page-hero page-hero--light"><div class="wrap"><div class="section-label"><span class="line"></span> BRAVIS · КУХНЯ И ВИНО</div><h1>Наше <em>меню.</em></h1><p>Армянские традиции, европейские вкусы и вино, которое дополняет встречу.</p></div></section><section class="section menu-section"><div class="wrap">'''
sections=MENU.get('sections',[])
available=[s for s in sections if s.get('items')]
if available:
    menu_top+='<nav class="menu-filter" aria-label="Разделы меню">' + ''.join(f'<a href="#{h(s.get("id","category"))}">{h(s.get("name","Раздел"))}</a>' for s in available) + '</nav>'
    for s in available:
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

banquet=f'''<section class="page-hero page-hero--dark"><div class="wrap page-hero-grid"><div><div class="section-label section-label--light"><span class="line"></span> СОБЫТИЯ В BRAVIS</div><h1>Встречи,<br><em>которые помнят.</em></h1><p>Дни рождения, камерные праздники, семейные ужины и встречи с коллегами — в атмосфере тепла и гостеприимства.</p>{button('Обсудить мероприятие',phone_url,tracking='banquet_phone_click')}</div><div class="page-hero-photo"><img src="{h(img(event_photo,'/assets/ambience.svg'))}" alt="{'Зал ресторана BRAVIS' if event_photo else 'Иллюстрация ресторанного зала'}" width="640" height="520"></div></div></section>
<section class="section"><div class="wrap two-col"><div><div class="section-label"><span class="line"></span> ВАШ ПОВОД</div><h2>Праздник —<br><em>в хорошей компании.</em></h2></div><div><p>Для небольшого семейного торжества, делового ужина или праздника с друзьями мы поможем подобрать формат. Условия, меню и доступность дат согласуются индивидуально.</p><p>Оставьте детали по телефону: команда расскажет о возможностях ресторана и ответит на вопросы.</p>{button('Позвонить в BRAVIS',phone_url,tracking='banquet_phone_click')}</div></div></section>
<section class="banner-dark"><div class="wrap banner-inner"><div><span class="overline">BRAVIS · СОБЫТИЯ</span><h2>Давайте обсудим<br><em>ваш вечер.</em></h2></div><div>{button('Связаться с рестораном',phone_url)}</div></div></section>'''

contacts=f'''<section class="page-hero page-hero--light"><div class="wrap"><div class="section-label"><span class="line"></span> КОНТАКТЫ И МАРШРУТ</div><h1>До <em>встречи.</em></h1><p>Находите время для близких. А мы найдём для вас место.</p></div></section><section class="section"><div class="wrap contacts-grid"><div class="contacts-info"><div class="contact-row"><span>АДРЕС</span><h2>{h(address)}</h2></div><div class="contact-row"><span>ТЕЛЕФОН</span><a class="contact-big" href="{h(phone_url)}" data-track="contacts_phone_click">{h(phone)}</a></div><div class="contact-row"><span>ОФИЦИАЛЬНАЯ ПОЧТА</span><a class="contact-big" href="mailto:{h(official_email)}">{h(official_email)}</a></div><div class="contact-row"><span>ВРЕМЯ РАБОТЫ</span><p>{h(CONFIG.get('hoursText',''))}</p></div><div class="contact-actions">{reserve_button()}{button('Открыть маршрут',yandex_maps_url,True,ext=True)}{button('Карточка BRAVIS в 2ГИС',two_gis_url,True,tracking='two_gis_click',ext=True) if two_gis_url else ''}</div></div><div class="map-card"><div class="map-card__line"></div><div class="map-card__inner"><span>BRAVIS</span><p>МОСКВА</p><p class="map-card__address">РАСКОВОЙ, 20</p><div class="map-pin">⌖</div><a href="{h(yandex_maps_url)}" target="_blank" rel="noopener noreferrer">Открыть на Яндекс Картах ↗</a>{f'<a href="{h(two_gis_url)}" target="_blank" rel="noopener noreferrer" data-track="two_gis_click">Открыть в 2ГИС ↗</a>' if two_gis_url else ''}</div></div></div></section>'''

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
<h3>4. Необязательная аналитика и настройки cookie</h3>
<p>На сайте предусмотрена Яндекс Метрика (счётчик № 113768615), которая загружается только после выбора «Разрешить» в уведомлении об аналитике. После согласия возможна обработка технической информации о посещениях и событиях (например, открытие меню, переход к бронированию, нажатие на телефон). Текстовые поля с персональными данными для этих событий на сайте не предусмотрены.</p>
<p>Выбор посетителя сохраняется в локальном хранилище браузера, чтобы не спрашивать разрешение при каждом переходе. Отказ сохраняется аналогично; до согласия скрипт Яндекс Метрики не загружается кодом сайта. Изменить выбор можно через «Настройки cookie» внизу страниц; после смены выбора страница перезагрузится.</p>
<h3>5. Цели и основания обработки</h3>
<p>Предполагаемые цели: техническое предоставление страниц и обеспечение работы сайта; измерение посещаемости и интереса к разделам — только по отдельному выбору посетителя. Правовые основания, перечень лиц, имеющих доступ к сведениям, а также схема обработки и хранения должны быть уточнены перед выпуском окончательной редакции.</p>
<h3>6. Передача данных и сроки хранения</h3>
<p>Данные могут технически обрабатываться провайдерами размещения сайта, а после отдельного согласия — сервисом Яндекс Метрика. Бронирование происходит на сайте внешнего сервиса. Конкретные договорные роли поставщиков услуг, место хранения технических журналов, сроки хранения и процедуры удаления должны быть проверены владельцем сайта и ответственным за персональные данные до промышленного запуска.</p>
<h3>7. Обращения и изменение согласия</h3>
<p>По вопросам обработки персональных данных, получения сведений об обработке, исправления или удаления данных и отзыва согласия можно обратиться к оператору по указанному выше адресу или e-mail. Отзыв согласия на необязательную аналитику также доступен через ссылку «Настройки cookie» в нижней части сайта.</p>
<p>Настоящий документ является рабочим проектом и должен быть актуализирован и утверждён оператором до публикации BRAVIS на официальном домене.</p></div></section>'''

PAGES={
  'index.html':page(home,'','Ресторан BRAVIS на улице Расковой, 20 в Москве. Армянская и европейская кухня, вино, семейные ужины и встречи. Бронирование столов.','/','home','home-page'),
  'menu/index.html':page(menu_top,'Меню','Меню ресторана BRAVIS в Москве: армянская и европейская кухня, винная карта. Актуальные блюда и информация.','/menu/','menu'),
  'banquets/index.html':page(banquet,'Банкеты и мероприятия','Праздники, камерные банкеты, дни рождения и семейные встречи в ресторане BRAVIS, Москва, улица Расковой, 20.','/banquets/','banquets'),
  'contacts/index.html':page(contacts,'Адрес и контакты','Ресторан BRAVIS: Москва, улица Расковой, 20. Телефон +7 (989) 571-99-77. Как добраться и забронировать стол.','/contacts/','contacts'),
  'privacy/index.html':page(privacy,privacy_title,'Сведения об обработке персональных данных на сайте ресторана BRAVIS.','/privacy/','privacy')
}

if DIST.exists():shutil.rmtree(DIST)
DIST.mkdir()
shutil.copytree(ROOT/'public', DIST, dirs_exist_ok=True)
for filename,content in PAGES.items():
    target=DIST/filename
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(content,encoding='utf-8')
# Don't enable indexing before owner authorizes publication and sets domain/legal data.
(DIST/'robots.txt').write_text(('User-agent: *\nAllow: /\nSitemap: '+site_url('/sitemap.xml')+'\n') if published else 'User-agent: *\nDisallow: /\n', encoding='utf-8')
if published:
    uris=['/','/menu/','/banquets/','/contacts/','/privacy/']
    sitemap='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+h(site_url(uri))+'</loc></url>' for uri in uris)+'</urlset>'
    (DIST/'sitemap.xml').write_text(sitemap,encoding='utf-8')
(DIST/'.nojekyll').write_text('',encoding='utf-8')
print('Built',len(PAGES),'pages in',DIST)
print('Publication:', 'PUBLIC' if published else 'PREVIEW ONLY (noindex)')
print('SmartReserve:', 'connected' if reserve_id else 'pending ID; calls by phone work')
print('Photos:', sum(bool(v) for v in (main_photo, interior, food, event_photo)), 'selected roles')
