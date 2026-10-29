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
GIFT = '<svg aria-hidden="true" width="44" height="44" viewBox="0 0 48 48" fill="none"><path d="M8 23h32v19H8V23Zm-3-8h38v8H5v-8Zm19 0v27M24 15c-8 0-13-1-13-6 0-7 12-5 13 6Zm0 0c8 0 13-1 13-6 0-7-12-5-13 6Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>'
KHINKALI = '<svg class="bravis-khinkali-art" aria-hidden="true" width="204" height="168" viewBox="0 0 204 168" fill="none"><circle cx="102" cy="83" r="75" stroke="currentColor" stroke-opacity=".25"/><path d="M102 48c-37 8-69 40-68 63 2 25 134 25 136 0 1-23-31-55-68-63Z" fill="currentColor" fill-opacity=".07" stroke="currentColor" stroke-width="2"/><path d="M91 50c-6-12-3-20 3-19l8 7 8-7c6-1 9 7 3 19M102 49v74M96 52c-14 26-18 45-15 68M109 52c14 26 18 45 15 68M91 54c-24 23-34 45-32 61M114 54c24 23 34 45 32 61" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'


def _contact_link(url, label, track='promotion_contact_click', extra_class=''):
    return (f'<a class="bravis-promo-link {_h(extra_class)}" href="{_h(_https(url))}" '
            f'target="_blank" rel="noopener noreferrer" data-track="{_h(track)}">'
            f'{_h(label)} {ARROW}</a>')


def welcome_strip(bonus):
    return f'''<aside class="bravis-welcome" aria-label="Подарки для гостей BRAVIS"><div class="wrap bravis-welcome__inner"><div class="bravis-welcome__copy"><p><strong>{_h(bonus)} бонусов или фирменный десерт?</strong><span>А можно и то, и другое.</span></p><small>Бонусы — за установку карты, десерт — по отдельному приглашению.</small></div><a href="/#loyalty">Узнать о подарках {ARROW}</a></div></aside>'''


def offers_section(bonus, lunch_price, loona_url, whatsapp_url, reserve_html):
    dessert = _wa(whatsapp_url, 'Здравствуйте! Подскажите, как получить приглашение на фирменный десерт в BRAVIS.')
    khinkali = _wa(whatsapp_url, 'Здравствуйте! Хочу узнать действующие условия акции «Хинкальный безлимит» в BRAVIS.')
    family = _wa(whatsapp_url, 'Здравствуйте! Подскажите условия «Семейного воскресенья» в BRAVIS.')
    signup = (f'<a class="bravis-promo-link bravis-promo-link--solid" href="{_h(_https(loona_url))}" '
              f'target="_blank" rel="noopener noreferrer" data-track="loona_signup_click">Оформить карту {ARROW}</a>')
    return f'''<section class="section bravis-offers" id="offers" aria-labelledby="bravis-offers-heading"><div class="wrap"><div class="bravis-promo-heading"><div><div class="section-label"><span class="line"></span> ПРЕДЛОЖЕНИЯ ДЛЯ ГОСТЕЙ</div><h2 id="bravis-offers-heading">Больше поводов<br><em>для встречи.</em></h2></div><p>За любимыми блюдами, приятными подарками и временем вместе.</p></div><div class="bravis-offer-grid">
<article class="bravis-offer bravis-offer--gift"><div class="bravis-offer__top"><span class="bravis-offer__eyebrow">КАРТА ГОСТЯ</span>{GIFT}</div><p class="bravis-offer__value">{_h(bonus)} <span>бонусов</span></p><h3>И приглашение на десерт</h3><p>{_h(bonus)} бонусов — за установку карты BRAVIS. Фирменный десерт — по отдельному приглашению в назначенный день.</p><p class="bravis-offer__note">Баланс и правила использования бонусов — на вашей карте. Условия десерта — в приглашении.</p><div class="bravis-offer__actions">{signup}{_contact_link(dessert, 'Узнать о десерте', 'dessert_invitation_click')}</div></article>
<article class="bravis-offer bravis-offer--lunch"><div class="bravis-offer__top"><span class="bravis-offer__eyebrow">ОБЕД В ГОРОДЕ</span><span class="bravis-offer__tag">Пн–пт</span></div><p class="bravis-offer__value">{_h(lunch_price)} <span>₽</span></p><h3>Бизнес-ланч</h3><p>С 11:00 до 16:00 — время сделать паузу и пообедать в BRAVIS. Меню на каждый будний день.</p><p class="bravis-offer__note">В праздничные дни уточняйте график у ресторана.</p><div class="bravis-offer__actions"><a class="bravis-promo-link" href="/lunch/" data-track="lunch_from_offers">Посмотреть меню {ARROW}</a></div></article>
<article class="bravis-offer bravis-offer--khinkali"><div class="bravis-offer__top"><span class="bravis-offer__eyebrow">ГОРЯЧИЙ ПОВОД</span><span class="bravis-offer__number" aria-hidden="true">01</span></div><h3>Хинкальный<br>безлимит</h3><p>Свежие горячие порции к вашему столу. Собирайтесь с теми, кто любит хинкали так же, как вы.</p><p class="bravis-offer__note">Действующие условия акции сообщим перед бронированием.</p><div class="bravis-offer__actions">{_contact_link(khinkali, 'Узнать условия', 'khinkali_offer_contact')}{reserve_html}</div></article>
<article class="bravis-offer bravis-offer--family"><div class="bravis-offer__top"><span class="bravis-offer__eyebrow">ВЫХОДНОЙ ВМЕСТЕ</span><span class="bravis-offer__number" aria-hidden="true">02</span></div><h3>Семейное<br>воскресенье</h3><p>Детское меню, любимые блюда взрослых и время за общим столом. Приходите в BRAVIS всей семьёй.</p><p class="bravis-offer__note">Условия семейного предложения уточните у ресторана.</p><div class="bravis-offer__actions">{_contact_link(family, 'Спланировать воскресенье', 'family_offer_contact')}</div></article>
</div></div></section>'''


def experiences_section(whatsapp_url):
    wine = _wa(whatsapp_url, 'Здравствуйте! Подскажите ближайшие даты и программу винных дегустаций в BRAVIS.')
    gastro = _wa(whatsapp_url, 'Здравствуйте! Хочу узнать о ближайших гастроужинах BRAVIS: даты, программу и условия участия.')
    return f'''<section class="section bravis-experiences" id="experiences" aria-labelledby="bravis-experiences-heading"><div class="wrap"><div class="bravis-promo-heading"><div><div class="section-label section-label--light"><span class="line"></span> ВКУС И ВПЕЧАТЛЕНИЯ</div><h2 id="bravis-experiences-heading">Винные дегустации<br><em>и гастроужины.</em></h2></div><p>Камерные встречи, новые вкусы и разговоры, которые хочется продолжить.</p></div><div class="bravis-experience-grid"><article class="bravis-experience"><div class="bravis-experience__image"><img src="/uploads/bravis-interior-06.jpg" alt="Винная роспись в интерьере ресторана BRAVIS" width="375" height="500" loading="lazy"></div><div class="bravis-experience__copy"><span class="bravis-offer__eyebrow">ЗНАКОМСТВО СО ВКУСОМ</span><h3>Винные<br>дегустации</h3><p>Открывайте новые вина и делитесь впечатлениями за общим столом.</p>{_contact_link(wine, 'Узнать ближайшие даты', 'wine_tasting_contact')}</div></article><article class="bravis-experience"><div class="bravis-experience__image"><img src="/uploads/bravis-interior-05.jpg" alt="Зал BRAVIS для камерных гастрономических встреч" width="960" height="1280" loading="lazy"></div><div class="bravis-experience__copy"><span class="bravis-offer__eyebrow">ОСОБЕННЫЙ ВЕЧЕР</span><h3>Гастроужины<br>в BRAVIS</h3><p>Вечера, в которых блюда и вина рассказывают одну историю.</p>{_contact_link(gastro, 'Узнать программу', 'gastro_dinner_contact')}</div></article></div><p class="bravis-experiences__note">Ближайшие даты, программу и условия участия уточняйте у ресторана.</p></div></section>'''


def menu_campaign(whatsapp_url, reserve_html):
    contact = _wa(whatsapp_url, 'Здравствуйте! Подскажите действующие условия «Хинкального безлимита» в BRAVIS и как забронировать стол.')
    return f'''<section class="bravis-menu-campaign" aria-labelledby="bravis-khinkali-heading"><div class="wrap bravis-menu-campaign__inner"><div class="bravis-menu-campaign__copy"><div class="section-label"><span class="line"></span> ЕСТЬ ПОВОД СОБРАТЬСЯ</div><h2 id="bravis-khinkali-heading">Хинкальный <em>безлимит.</em></h2><p>Любимые хинкали — свежими горячими порциями. Уточните условия акции и выбирайте время для встречи.</p><div class="bravis-menu-campaign__actions">{_contact_link(contact, 'Узнать условия', 'khinkali_menu_contact')}{reserve_html}</div></div>{KHINKALI}</div></section>'''


def banquet_details(whatsapp_url):
    contact = _wa(whatsapp_url, 'Здравствуйте! Хочу запросить банкетное меню BRAVIS и обсудить условия мероприятия.')
    return f'''<section class="section bravis-banquet-details" id="banquet-menu" aria-labelledby="bravis-banquet-menu-heading"><div class="wrap bravis-banquet-details__grid"><div><div class="section-label"><span class="line"></span> МЕНЮ ВАШЕЙ ВСТРЕЧИ</div><h2 id="bravis-banquet-menu-heading">Ваш праздник.<br><em>Ваше меню.</em></h2><p class="bravis-banquet-details__lead">Подберём банкетное меню под формат встречи, вашу компанию и пожелания гостей.</p><dl class="bravis-banquet-terms"><div><dt>Банкетное меню</dt><dd>Обсудим блюда, последовательность подачи и состав вашего праздничного стола.</dd></div><div><dt>Индивидуальный подход</dt><dd>Готовы адаптировать блюда по индивидуальной заявке. Пожелания к составу и подаче согласуем заранее.</dd></div><div><dt>Понятные условия</dt><dd>Меню, расчёт стоимости и условия обслуживания согласуем до подтверждения мероприятия.</dd></div></dl><a class="bravis-promo-link" href="/menu/" data-track="banquet_main_menu">Посмотреть блюда основного меню {ARROW}</a></div><aside class="bravis-banquet-request" aria-label="Запросить банкетное предложение"><span class="bravis-offer__eyebrow">НАЧНЁМ С ВАШИХ ПЛАНОВ</span><h3>Дата. Гости.<br>Формат встречи.</h3><p>Напишите, какой праздник вы планируете. Поможем подобрать меню и обсудим детали.</p>{_contact_link(contact, 'Запросить банкетное меню', 'banquet_menu_request', 'bravis-promo-link--solid')}<small>Предложение подготовим по вашему запросу.</small></aside></div></section>'''


def contact_invitation(reserve_html):
    return f'''<section class="bravis-contact-invitation" aria-labelledby="bravis-contact-invitation-heading"><div class="wrap bravis-contact-invitation__inner"><div><div class="section-label section-label--light"><span class="line"></span> ДО ВСТРЕЧИ В BRAVIS</div><h2 id="bravis-contact-invitation-heading">Выберите повод.<br><em>Мы встретим.</em></h2><p>Стол на двоих, семейное воскресенье или вечер компанией — поможем спланировать ваш визит.</p></div><div class="bravis-contact-invitation__actions">{reserve_html}<a class="bravis-promo-link" href="/menu/" data-track="menu_from_contacts">Посмотреть меню {ARROW}</a></div></div></section>'''
