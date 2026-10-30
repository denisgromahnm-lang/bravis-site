"""Guest-facing offers using approved facts and existing restaurant links.

The caller supplies reserve_html from the site's trusted booking-button renderer;
other dynamic values are escaped here. No forms or loyalty automation are added.
"""
from html import escape
from urllib.parse import urlencode, urlsplit, urlunsplit


def _h(value):
    return escape(str(value), quote=True)


def _https(value):
    value = str(value).strip()
    parts = urlsplit(value)
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password:
        raise ValueError('Promotion links require an approved HTTPS URL')
    return value


def _wa(base, public_message):
    """Only public restaurant questions are inserted; no guest data is accepted."""
    parts = urlsplit(_https(base))
    if parts.hostname not in ('wa.me', 'www.wa.me'):
        raise ValueError('Promotion contact must retain the verified WhatsApp link')
    return urlunsplit((parts.scheme, parts.netloc, parts.path,
                       urlencode({'text': public_message}), ''))


ARROW = '<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M5 12h14m-6-6 6 6-6 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'
GIFT_ART = '<svg class="bravis-gift-art" aria-hidden="true" focusable="false" width="240" height="216" viewBox="0 0 200 180" fill="none"><circle cx="100" cy="90" r="79" stroke="currentColor" stroke-width=".8" stroke-opacity=".2"/><circle cx="100" cy="90" r="68" stroke="currentColor" stroke-width=".7" stroke-opacity=".12"/><path d="M31 76h55v53H31V76Z" fill="currentColor" fill-opacity=".035" stroke="currentColor" stroke-width="1.4"/><path d="M27 65h63v12H27V65Zm31 0v64M58 65c-13-1-22-3-21-11 1-10 18-5 21 11Zm0 0c13-1 22-3 21-11-1-10-18-5-21 11Z" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/><path d="M42 89h8m-8 6h8" stroke="currentColor" stroke-width="1" stroke-opacity=".4"/><ellipse cx="132" cy="134" rx="43" ry="7" stroke="currentColor" stroke-width="1.3"/><path d="M105 97v26c0 10 54 10 54 0V97" fill="currentColor" fill-opacity=".04" stroke="currentColor" stroke-width="1.4"/><ellipse cx="132" cy="97" rx="27" ry="8" fill="#bb946c" fill-opacity=".15" stroke="currentColor" stroke-width="1.3"/><path d="M105 108c12 7 42 7 54 0M105 117c12 7 42 7 54 0" stroke="currentColor" stroke-width="1" stroke-opacity=".45"/><path d="M132 90c-12-10-12-22-4-22l4 3 4-3c8 0 8 12-4 22Z" fill="#9b5965" fill-opacity=".15" stroke="currentColor" stroke-width="1.2"/><path d="m126 70 6 4 6-4m-6 4 1-11M125 79h.1m7 2h.1m5-4h.1M162 48v12m-6-6h12M104 38v8m-4-4h8" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/><path d="M48 143c17 6 34 9 52 9" stroke="currentColor" stroke-width=".9" stroke-opacity=".3"/></svg>'
KHINKALI = '<svg class="bravis-khinkali-art" aria-hidden="true" width="204" height="168" viewBox="0 0 204 168" fill="none"><circle cx="102" cy="83" r="75" stroke="currentColor" stroke-opacity=".25"/><path d="M102 48c-37 8-69 40-68 63 2 25 134 25 136 0 1-23-31-55-68-63Z" fill="currentColor" fill-opacity=".07" stroke="currentColor" stroke-width="2"/><path d="M91 50c-6-12-3-20 3-19l8 7 8-7c6-1 9 7 3 19M102 49v74M96 52c-14 26-18 45-15 68M109 52c14 26 18 45 15 68M91 54c-24 23-34 45-32 61M114 54c24 23 34 45 32 61" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'


def _contact_link(url, label, track='promotion_contact_click', extra_class=''):
    return (f'<a class="bravis-promo-link {_h(extra_class)}" href="{_h(_https(url))}" '
            f'target="_blank" rel="noopener noreferrer" data-track="{_h(track)}">'
            f'{_h(label)} {ARROW}</a>')


def gift_art():
    """A decorative BRAVIS gift and dessert, without a third-party card mockup."""
    return GIFT_ART


def welcome_strip(bonus):
    return f'''<aside class="bravis-welcome" aria-label="Подарки для гостей BRAVIS"><div class="wrap bravis-welcome__inner"><div class="bravis-welcome__copy"><p><svg class="bravis-welcome__symbol" aria-hidden="true" width="25" height="28" viewBox="0 0 28 30" fill="none"><path d="M4 13h20v14H4V13Zm-2-5h24v6H2V8Zm12 0v19M14 8C3 8 5-2 10 3l4 5Zm0 0c11 0 9-10 4-5l-4 5Z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg><strong>{_h(bonus)} бонусов и фирменный десерт</strong></p><small>Бонусы — за установку карты BRAVIS. Десерт — по приглашению на выходные.</small></div><a href="/#loyalty">Узнайте о подарках {ARROW}</a></div></aside>'''


def lunch_reward_strip():
    """An owner-confirmed reward; counting mechanics remain with the restaurant."""
    return f'''<aside class="bravis-lunch-reward" aria-label="Шестой бизнес-ланч бесплатно"><span class="bravis-lunch-reward__mark" aria-hidden="true"><svg width="62" height="62" viewBox="0 0 64 64" fill="none"><circle cx="32" cy="32" r="29" stroke="currentColor" stroke-width="1"/><path d="M13 17c-5 8-5 22 0 30M51 17c5 8 5 22 0 30M25 5h14M25 59h14" stroke="currentColor" stroke-width="1" stroke-opacity=".45" stroke-linecap="round"/></svg><span>6</span></span><div class="bravis-lunch-reward__copy"><strong>Шестой бизнес-ланч — бесплатно</strong><p>Условия учёта обедов уточняйте у команды ресторана.</p></div><a class="bravis-promo-link" href="/lunch/#lunch-menu" data-track="lunch_reward_menu_click">Выбрать обед {ARROW}</a></aside>'''


def offers_section(bonus, lunch_price, loona_url, whatsapp_url, reserve_html):
    dessert = _wa(whatsapp_url, 'Здравствуйте! Хочу провести выходные в BRAVIS. Подскажите, как получить приглашение на фирменный десерт.')
    khinkali = _wa(whatsapp_url, 'Здравствуйте! Хочу узнать действующие условия акции «Хинкальный безлимит» в BRAVIS.')
    family = _wa(whatsapp_url, 'Здравствуйте! Подскажите условия «Семейного воскресенья» в BRAVIS.')
    signup = (f'<a class="bravis-promo-link bravis-promo-link--solid" href="{_h(_https(loona_url))}" '
              f'target="_blank" rel="noopener noreferrer" data-track="loona_signup_click">Оформить карту {ARROW}</a>')
    return f'''<section class="section bravis-offers" id="offers" aria-labelledby="bravis-offers-heading"><div class="wrap"><div class="bravis-promo-heading"><div><div class="section-label"><span class="line"></span> ПРЕДЛОЖЕНИЯ ДЛЯ ГОСТЕЙ</div><h2 id="bravis-offers-heading">Больше поводов<br><em>для встречи.</em></h2></div><p>За любимыми блюдами, приятными подарками и временем вместе.</p></div><div class="bravis-offer-grid">
<article class="bravis-offer bravis-offer--gift"><div class="bravis-offer__top"><span class="bravis-offer__eyebrow">ПОДАРКИ ДЛЯ ВАШИХ ВСТРЕЧ</span>{gift_art()}</div><p class="bravis-offer__value">{_h(bonus)} <span>бонусов</span></p><h3>и фирменный<br>десерт</h3><p>{_h(bonus)} бонусных баллов — за установку карты гостя BRAVIS. А фирменный десерт станет сладким поводом заглянуть к нам в выходные.</p><p class="bravis-offer__note">Баланс и правила использования бонусов — на вашей карте. Подробности десерта — в персональном предложении.</p><div class="bravis-offer__actions">{signup}{_contact_link(dessert, 'Узнать о десерте', 'dessert_invitation_click')}</div></article>
<article class="bravis-offer bravis-offer--lunch"><div class="bravis-offer__top"><span class="bravis-offer__eyebrow">ОБЕД В ГОРОДЕ</span><span class="bravis-offer__tag">Пн–пт</span></div><div class="bravis-lunch-price"><p class="bravis-offer__value">{_h(lunch_price)} <span>₽</span></p><span class="bravis-lunch-tag"><span>6-й бизнес-ланч</span><strong>Бесплатно</strong></span></div><h3>Бизнес-ланч</h3><p>С 11:00 до 16:00 — время сделать паузу и пообедать в BRAVIS. Меню на каждый будний день.</p><p class="bravis-offer__reward">Возвращайтесь на обед: <strong>каждый шестой бизнес-ланч — за счёт BRAVIS.</strong></p><p class="bravis-offer__note">Условия учёта обедов уточняйте у команды ресторана. В праздничные дни уточняйте график.</p><div class="bravis-offer__actions"><a class="bravis-promo-link" href="/lunch/" data-track="lunch_from_offers">Посмотреть меню {ARROW}</a></div></article>
<article class="bravis-offer bravis-offer--khinkali"><div class="bravis-offer__top"><span class="bravis-offer__eyebrow">ГОРЯЧИЙ ПОВОД</span><span class="bravis-offer__number" aria-hidden="true">01</span></div><h3>Хинкальный<br>безлимит</h3><p>Свежие горячие порции к вашему столу. Собирайтесь с теми, кто любит хинкали так же, как вы.</p><p class="bravis-offer__note">Действующие условия акции сообщим перед бронированием.</p><div class="bravis-offer__actions">{_contact_link(khinkali, 'Узнать условия', 'khinkali_offer_contact')}{reserve_html}</div></article>
<article class="bravis-offer bravis-offer--family"><div class="bravis-offer__top"><span class="bravis-offer__eyebrow">ВЫХОДНОЙ ВМЕСТЕ</span><span class="bravis-offer__number" aria-hidden="true">02</span></div><h3>Семейное<br>воскресенье</h3><p>Детское меню, любимые блюда взрослых и время за общим столом. Приходите в BRAVIS всей семьёй.</p><p class="bravis-offer__note">Условия семейного предложения уточните у ресторана.</p><div class="bravis-offer__actions">{_contact_link(family, 'Спланировать воскресенье', 'family_offer_contact')}</div></article>
</div></div></section>'''


def experiences_section(whatsapp_url):
    wine = _wa(whatsapp_url, 'Здравствуйте! Подскажите ближайшие даты и программу винных дегустаций в BRAVIS.')
    gastro = _wa(whatsapp_url, 'Здравствуйте! Хочу узнать о ближайших гастроужинах BRAVIS: даты, программу и условия участия.')
    return f'''<section class="section bravis-experiences" id="experiences" aria-labelledby="bravis-experiences-heading"><div class="wrap"><div class="bravis-promo-heading"><div><div class="section-label section-label--light"><span class="line"></span> ВКУС И ВПЕЧАТЛЕНИЯ</div><h2 id="bravis-experiences-heading">Винные дегустации<br><em>и гастроужины.</em></h2></div><p>Камерные встречи, новые вкусы и разговоры, которые хочется продолжить.</p></div><div class="bravis-experience-grid"><article class="bravis-experience"><div class="bravis-experience__image"><img src="/uploads/bravis-interior-06.jpg" alt="Винная роспись в интерьере ресторана BRAVIS" width="375" height="500" loading="lazy"></div><div class="bravis-experience__copy"><span class="bravis-offer__eyebrow">ЗНАКОМСТВО СО ВКУСОМ</span><h3>Винные<br>дегустации</h3><p>Открывайте новые вина и делитесь впечатлениями за общим столом.</p>{_contact_link(wine, 'Узнать ближайшие даты', 'wine_tasting_contact')}</div></article><article class="bravis-experience"><div class="bravis-experience__image"><img src="/uploads/bravis-interior-05.jpg" alt="Зал BRAVIS для камерных гастрономических встреч" width="960" height="1280" loading="lazy"></div><div class="bravis-experience__copy"><span class="bravis-offer__eyebrow">ОСОБЕННЫЙ ВЕЧЕР</span><h3>Гастроужины<br>в BRAVIS</h3><p>Вечера, в которых блюда и вина рассказывают одну историю.</p>{_contact_link(gastro, 'Узнать программу', 'gastro_dinner_contact')}</div></article></div><p class="bravis-experiences__note">Ближайшие даты, программу и условия участия уточняйте у ресторана.</p></div></section>'''


def menu_campaign(whatsapp_url, reserve_html):
    """The khinkali offer now belongs in the menu hero, without a second banner."""
    return ''


def banquet_details(whatsapp_url, contact_choices=''):
    contact = _wa(whatsapp_url, 'Здравствуйте! Хочу запросить банкетное меню BRAVIS и обсудить условия мероприятия.')
    # Like reserve_html, choices come from the site's trusted UI renderer.
    request_actions = contact_choices or _contact_link(contact, 'Запросить банкетное меню', 'banquet_menu_request', 'bravis-promo-link--solid')
    return f'''<section class="section bravis-banquet-details" id="banquet-menu" aria-labelledby="bravis-banquet-menu-heading"><div class="wrap bravis-banquet-details__grid"><div><div class="section-label"><span class="line"></span> МЕНЮ ВАШЕЙ ВСТРЕЧИ</div><h2 id="bravis-banquet-menu-heading">Ваш праздник.<br><em>Ваше меню.</em></h2><p class="bravis-banquet-details__lead">Подберём банкетное меню под формат встречи, вашу компанию и пожелания гостей.</p><dl class="bravis-banquet-terms"><div><dt>Банкетное меню</dt><dd>Обсудим блюда, последовательность подачи и состав вашего праздничного стола.</dd></div><div><dt>Индивидуальный подход</dt><dd>Готовы адаптировать блюда по индивидуальной заявке. Пожелания к составу и подаче согласуем заранее.</dd></div><div><dt>Понятные условия</dt><dd>Меню, расчёт стоимости и условия обслуживания согласуем до подтверждения мероприятия.</dd></div></dl><a class="bravis-promo-link" href="/menu/" data-track="banquet_main_menu">Посмотреть блюда основного меню {ARROW}</a></div><aside class="bravis-banquet-request" aria-label="Запросить банкетное предложение"><span class="bravis-offer__eyebrow">НАЧНЁМ С ВАШИХ ПЛАНОВ</span><h3>Дата. Гости.<br>Формат встречи.</h3><p>Напишите, какой праздник вы планируете. Поможем подобрать меню и обсудим детали.</p>{request_actions}<small>Предложение подготовим по вашему запросу.</small></aside></div></section>'''


def contact_invitation(reserve_html):
    return f'''<section class="bravis-contact-invitation" aria-labelledby="bravis-contact-invitation-heading"><div class="wrap bravis-contact-invitation__inner"><div><div class="section-label section-label--light"><span class="line"></span> ДО ВСТРЕЧИ В BRAVIS</div><h2 id="bravis-contact-invitation-heading">Выберите повод.<br><em>Мы встретим.</em></h2><p>Стол на двоих, семейное воскресенье или вечер компанией — поможем спланировать ваш визит.</p></div><div class="bravis-contact-invitation__actions">{reserve_html}<a class="bravis-promo-link" href="/menu/" data-track="menu_from_contacts">Посмотреть меню {ARROW}</a></div></div></section>'''
