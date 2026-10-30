"""Render the restaurant's approved photographs without new browser scripts."""
from html import escape
from pathlib import Path
from struct import unpack
from urllib.parse import urlsplit

PUBLIC = Path(__file__).resolve().parents[1] / 'public'
_SOF = frozenset((0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                  0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF))


def _dimensions(path):
    """Read JPEG frame dimensions with the standard library, without decoding."""
    with path.open('rb') as source:
        if source.read(2) != b'\xff\xd8':
            raise ValueError('Restaurant gallery requires original JPEG photographs')
        while True:
            if source.read(1) != b'\xff':
                raise ValueError('Invalid JPEG marker in restaurant gallery')
            marker = source.read(1)
            while marker == b'\xff':
                marker = source.read(1)
            if not marker or marker[0] in (0xD9, 0xDA):
                break
            if marker[0] in (0x01, *range(0xD0, 0xD9)):
                continue
            length_bytes = source.read(2)
            if len(length_bytes) != 2:
                break
            length = unpack('>H', length_bytes)[0]
            if length < 2:
                break
            if marker[0] in _SOF:
                frame = source.read(5)
                if len(frame) == 5:
                    height, width = unpack('>HH', frame[1:])
                    if width and height:
                        return width, height
                break
            source.seek(length - 2, 1)
    raise ValueError('JPEG dimensions missing in restaurant gallery: ' + path.name)


def _photos(gallery):
    candidates = [gallery.get(key) for key in ('hero', 'interior', 'events')]
    candidates.extend(gallery.get('gallery', []))
    approved = []
    for value in candidates:
        if not value or value in approved:
            continue
        parts = urlsplit(value)
        if (parts.scheme or parts.netloc or parts.query or parts.fragment
                or not parts.path.startswith('/uploads/')
                or '..' in parts.path.split('/') or not parts.path.endswith('.jpg')):
            raise ValueError('Gallery photographs must be approved local upload paths')
        path = PUBLIC / parts.path.lstrip('/')
        if not path.is_file():
            raise ValueError('Approved gallery photograph missing: ' + value)
        approved.append(value)
    return approved


def render_restaurant_gallery(gallery):
    """Return a complete page body; photographs retain their original proportions."""
    photos = _photos(gallery)
    if not photos:
        raise ValueError('The restaurant gallery needs approved photographs')
    cards = []
    for number, photo in enumerate(photos, 1):
        width, height = _dimensions(PUBLIC / photo.lstrip('/'))
        url = escape(photo, quote=True)
        label = f'Интерьер ресторана BRAVIS — фотография {number}'
        cards.append(
            f'<figure class="restaurant-gallery__item">'
            f'<a class="restaurant-gallery__photo" href="{url}" target="_blank" '
            f'rel="noopener noreferrer" aria-label="{label}. Открыть оригинал в новой вкладке">'
            f'<img src="{url}" alt="{label}" width="{width}" height="{height}" '
            f'loading="lazy" decoding="async"></a>'
            f'<figcaption><span>BRAVIS · В ДЕТАЛЯХ</span><span>{number:02d}</span></figcaption>'
            f'</figure>')
    return (
        '<section class="page-hero page-hero--light restaurant-gallery-hero"><div class="wrap">'
        '<div class="section-label"><span class="line"></span> РЕСТОРАН ИЗНУТРИ</div>'
        '<h1>Атмосфера<br><em>вашей встречи.</em></h1>'
        '<p>Загляните в BRAVIS перед визитом. Наши залы, свет и детали интерьера — '
        'на настоящих фотографиях ресторана.</p>'
        '<a class="restaurant-gallery__events" href="/events/">Что происходит в BRAVIS '
        '<svg aria-hidden="true" width="14" height="14" viewBox="0 0 16 16" fill="none">'
        '<path d="M3 13 13 3M3 3h10v10" stroke="currentColor" stroke-width="1.3"/>'
        '</svg></a>'
        '</div></section>'
        '<section class="restaurant-gallery" aria-label="Фотографии интерьера ресторана BRAVIS">'
        '<div class="wrap"><p class="restaurant-gallery__hint">'
        'Нажмите на фотографию, чтобы рассмотреть её в полном размере.</p>'
        '<div class="restaurant-gallery__columns">' + ''.join(cards) + '</div></div></section>'
    )
