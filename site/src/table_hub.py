"""Two-action guest pages. Only owner-verified table destinations are published."""
import html
import re
from urllib.parse import urlsplit
from guest_hub import LOONA_4992
from wallet_help import render_wallet_help


def verified_tables(settings):
    hosts = settings.get('approvedOrderHosts', [])
    if not isinstance(hosts, list) or any(not isinstance(x, str) or
            not re.fullmatch(r'[a-z0-9]+(?:[.-][a-z0-9]+)*', x) for x in hosts):
        raise ValueError('Order hosts must be explicitly approved hostnames')
    tables = settings.get('tables', [])
    if not isinstance(tables, list):
        raise ValueError('Tables must be a list')
    seen = set()
    result = []
    for table in tables:
        key, label, url = table['id'], table['label'], table['orderUrl']
        if not isinstance(key, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,31}', key) or key in seen:
            raise ValueError('Table IDs must be unique safe route names')
        if not isinstance(label, str) or not label.strip() or len(label) > 40:
            raise ValueError('A guest-visible table label is required')
        if not isinstance(url, str) or any(c.isspace() or ord(c) < 32 for c in url):
            raise ValueError('Use the original table URL without whitespace')
        parts = urlsplit(url)
        if (parts.scheme != 'https' or parts.hostname not in hosts or parts.username
                or parts.password or parts.port not in (None, 443)):
            raise ValueError('Table order destination must use an approved HTTPS host')
        seen.add(key)
        # Keep every query parameter and fragment exactly as supplied by the owner.
        result.append({'id': key, 'label': label.strip(), 'orderUrl': url})
    return result


def render_table_hub(config, document_head, table=None):
    h = lambda value: html.escape(str(value), quote=True)
    loyalty = config.get('loonaJoinUrl', '')
    if loyalty != LOONA_4992:
        raise ValueError('Keep the verified BRAVIS guest-card registration URL')
    label = table['label'] if table else 'Добро пожаловать'
    if table:
        order = (f'<a class="table-action table-action--primary" href="{h(table["orderUrl"])}" '
                 f'data-track="table_lunch_click" data-table="{h(table["id"])}">'
                 '<span><strong>Заказать бизнес-ланч</strong><small>Выбрать блюда и оформить заказ</small></span>'
                 '<span aria-hidden="true">→</span></a>')
        note = 'Ваш стол уже указан в ссылке заказа.'
    else:
        order = ('<div class="table-action table-action--unavailable" aria-disabled="true">'
                 '<span><strong>Заказать бизнес-ланч</strong><small>Отсканируйте QR-код на вашем столе</small></span></div>')
        note = 'Если QR-код не открывается, обратитесь к официанту.'
    document_head = document_head.replace('</head>', '<link rel="stylesheet" href="/assets/table-hub.css"><link rel="stylesheet" href="/assets/wallet-help.css"></head>')
    return document_head + f'''<a class="skip" href="#main">Перейти к содержимому</a>
<header class="table-header"><a href="/" aria-label="BRAVIS — основной сайт">BRAVIS</a><span>РЕСТОРАН · МОСКВА</span></header>
<main class="table-shell" id="main"><span class="table-label">{h(label)}</span>
<h1>Рады видеть<br><em>вас в BRAVIS.</em></h1><p class="table-intro">Вкусный обед и приятные поводы вернуться.</p>
<nav class="table-actions" aria-label="Заказ и карта гостя">{order}
<a class="table-action" href="{h(loyalty)}" data-track="loona_signup_click"><span><strong>Оформить карту гостя</strong><small>Программа лояльности BRAVIS</small></span><span aria-hidden="true">→</span></a></nav>
{render_wallet_help()}
<p class="table-note">{h(note)}</p></main>
<footer class="table-footer"><div class="footer-bottom"><a href="/">Сайт ресторана</a><a href="/privacy/">Политика обработки данных</a></div></footer>
<script src="/assets/site.js" defer></script></body></html>'''
