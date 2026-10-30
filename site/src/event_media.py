"""Render approved restaurant photographs and videos without a browser library.

The caller loads a local content manifest. Its ``events`` entries have id, title,
description, optional ISO date, and photos (src, alt, width, height, optional
caption and structured srcset). Its ``videos`` entries have src, poster, title,
width, height and an optional description. Private source links stay outside
this public manifest.
"""
from datetime import date
from html import escape
from pathlib import Path
import re


PUBLIC = Path(__file__).resolve().parents[1] / 'public'
ARROW = ('<svg aria-hidden="true" focusable="false" width="16" height="16" '
         'viewBox="0 0 16 16" fill="none"><path d="M3 13 13 3M3 3h10v10" '
         'stroke="currentColor" stroke-width="1.3"/></svg>')


def _h(value):
    return escape(str(value), quote=True)


def _asset(value, extensions):
    """Accept existing local media only, never remote or encoded URL paths."""
    if not isinstance(value, str) or not re.fullmatch(
            r'/(?:uploads|media)/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_.-]+\.(?:'
            + '|'.join(extensions) + ')', value):
        raise ValueError('Event media requires an approved local media path')
    path = PUBLIC / value.lstrip('/')
    if not path.resolve().is_relative_to(PUBLIC.resolve()) or not path.is_file():
        raise ValueError('Approved event media file is missing: ' + value)
    return value


def _dimension(value):
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 16384:
        raise ValueError('Event media dimensions must match its original media')
    return value


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Event media needs ' + label)
    return value.strip()


def _photo(photo):
    src = _asset(photo['src'], ('jpg', 'jpeg', 'png', 'webp', 'avif'))
    alt = _text(photo['alt'], 'a descriptive photo caption')
    width, height = _dimension(photo['width']), _dimension(photo['height'])
    srcset = photo.get('srcset', [])
    responsive = ''
    if srcset:
        if not isinstance(srcset, list):
            raise ValueError('Photo srcset must be a list of local src/width entries')
        candidates = []
        seen_widths = set()
        for candidate in srcset:
            candidate_src = _asset(candidate['src'], ('jpg', 'jpeg', 'png', 'webp', 'avif'))
            candidate_width = _dimension(candidate['width'])
            if candidate_width in seen_widths:
                raise ValueError('Photo srcset widths must be unique')
            seen_widths.add(candidate_width)
            candidates.append(f'{candidate_src} {candidate_width}w')
        responsive = (' srcset="' + _h(', '.join(candidates)) + '" '
                      'sizes="(max-width: 560px) calc(100vw - 36px), '
                      '(max-width: 1000px) calc((100vw - 56px) / 2), 400px"')
    caption = photo.get('caption', '')
    caption_html = f'<figcaption>{_h(caption)}</figcaption>' if caption else ''
    return (f'<figure class="event-media__photo"><a href="{_h(src)}" target="_blank" '
            f'rel="noopener noreferrer" aria-label="{_h(alt)}. Открыть фотографию крупно">'
            f'<img src="{_h(src)}" alt="{_h(alt)}" width="{width}" height="{height}"'
            f'{responsive} loading="lazy" decoding="async"></a>{caption_html}</figure>')


def render_event_media(data, compact=False):
    """Render real event photographs, or no block while no photos are approved."""
    events = [event for event in data.get('events', []) if event.get('photos')]
    if not events:
        return ''
    if compact:
        events = events[:1]
    articles = []
    seen_ids = set()
    for event in events:
        event_id = event['id']
        if (not isinstance(event_id, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}', event_id)
                or event_id in seen_ids):
            raise ValueError('Event media IDs must be unique safe identifiers')
        seen_ids.add(event_id)
        title = _text(event['title'], 'an event title')
        description = event.get('description', '')
        date_html = ''
        if event.get('date'):
            event_date = date.fromisoformat(event['date'])
            date_html = (f'<time datetime="{event_date.isoformat()}">'
                         f'{event_date.strftime("%d.%m.%Y")}</time>')
        photos = event['photos'][:3] if compact else event['photos']
        articles.append(
            f'<article class="event-media__event" id="event-media-{event_id}" '
            f'aria-labelledby="event-media-{event_id}-title">'
            f'<div class="event-media__intro">{date_html}'
            f'<h3 id="event-media-{event_id}-title">{_h(title)}</h3>'
            + (f'<p>{_h(description)}</p>' if description else '')
            + '</div><div class="event-media__photos">'
            + ''.join(_photo(photo) for photo in photos) + '</div></article>')
    more = (f'<a class="event-media__more" href="/events/#bravis-in-frames">'
            f'Больше историй и фотографий {ARROW}</a>' if compact else '')
    modifier = ' event-media--compact' if compact else ''
    return (
        f'<section class="section event-media{modifier}" id="bravis-in-frames" '
        'aria-labelledby="bravis-in-frames-title"><div class="wrap">'
        '<div class="section-label"><span class="line"></span> ВСТРЕЧИ И ВПЕЧАТЛЕНИЯ</div>'
        '<div class="event-media__heading"><h2 id="bravis-in-frames-title">'
        'Жизнь BRAVIS <em>в кадре.</em></h2>' + more + '</div>'
        + ''.join(articles) + '</div></section>')


def render_restaurant_videos(data):
    """Expose native video controls with no autoplay or proactive video preload."""
    videos = data.get('videos', [])
    if not videos:
        return ''
    cards = []
    for index, video in enumerate(videos, 1):
        src = _asset(video['src'], ('mp4', 'webm'))
        poster = _asset(video['poster'], ('jpg', 'jpeg', 'png', 'webp', 'avif'))
        title = _text(video['title'], 'a video title')
        width, height = _dimension(video['width']), _dimension(video['height'])
        description = video.get('description', '')
        cards.append(
            f'<figure class="restaurant-videos__item"><video controls playsinline '
            f'preload="none" poster="{_h(poster)}" width="{width}" height="{height}" '
            f'aria-labelledby="restaurant-video-{index}-title" src="{_h(src)}">'
            f'<a href="{_h(src)}">Открыть видео «{_h(title)}»</a></video>'
            f'<figcaption><h3 id="restaurant-video-{index}-title">{_h(title)}</h3>'
            + (f'<p>{_h(description)}</p>' if description else '')
            + '</figcaption></figure>')
    return (
        '<section class="section restaurant-videos" id="bravis-in-motion" '
        'aria-labelledby="bravis-in-motion-title"><div class="wrap">'
        '<div class="section-label section-label--light"><span class="line"></span> '
        'АТМОСФЕРА BRAVIS</div><h2 id="bravis-in-motion-title">'
        'Загляните <em>к нам.</em></h2><div class="restaurant-videos__grid">'
        + ''.join(cards) + '</div></div></section>')
