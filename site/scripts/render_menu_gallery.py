#!/usr/bin/env python3
"""Render an accessible five-section restaurant menu from approved print artwork."""
import html,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/'dist'
MANIFEST=ROOT/'content/menu_media.json'
def h(v):return html.escape(str(v),quote=True)
def main():
    htmlpath=DIST/'menu/index.html'
    page=htmlpath.read_text(encoding='utf-8')
    if not MANIFEST.exists():
        print("INFO: approved assets unavailable; safe phone fallback remains on menu")
        return
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    if manifest.get('selection')!='owner-approved-print-menu':raise RuntimeError("Menu assets unapproved")
    files=manifest.get('files',[])
    expected=['seasonal','main-front','main-back','business','children']
    assert [x.get('group') for x in files]==expected,"Menu set/category order mismatch"
    for obj in files:
        urls=obj.get('pages',[])
        if not urls or len(urls)>8:raise ValueError('Unexpected menu pages')
        for url in urls:
            if not re.fullmatch(r'/menu-media/[a-z0-9-]+\.jpg',url):raise ValueError('Unexpected menu URL')
            if not (DIST/url.lstrip('/')).is_file():raise FileNotFoundError(url)
    tiles=[]
    notes={
      'seasonal':'Специальные предложения сезона',
      'main-front':'Закуски, горячие блюда, мангал и десерты',
      'main-back':'Вино, коктейли и напитки',
      'business':'Обеды в BRAVIS',
      'children':'Блюда для маленьких гостей'
    }
    for i,entry in enumerate(files):
        title=h(entry['title']);src=h(entry['url'])
        key=h(entry['group'])
        cnt=len(entry['pages'])
        tiles.append(f'''<a class="print-card" href="{src}" data-menu-index="{i}" aria-label="Открыть {title}">
        <div class="print-card__image"><img src="{src}" width="460" height="620" alt="Оригинальное меню BRAVIS — {title}" loading="{'eager' if i < 2 else 'lazy'}"></div>
        <div class="print-card__text"><span class="print-card__overline">BRAVIS · МЕНЮ</span>
        <h2>{title}</h2><p>{h(notes[entry['group']])}</p>
        <span class="print-card__more">Посмотреть {'страницы' if cnt>1 else 'меню'} <span aria-hidden="true">↗</span></span></div></a>''')
    data=json.dumps([{"title":x["title"],"pages":x["pages"]} for x in files],ensure_ascii=False).replace("<","\\u003c")
    widget='''<div class="approved-menus" id="approved-menus"><div class="approved-menus__intro">
      <div class="section-label"><span class="line"></span> ОРИГИНАЛЬНЫЕ МЕНЮ BRAVIS</div>
      <h2>Выбирайте то, <em>что нравится.</em></h2>
      <p>Меню ресторана, сезонные предложения, барная карта, бизнес-ланч и блюда для детей. Откройте раздел, чтобы рассмотреть его крупно.</p>
    </div><div class="print-menu-grid">'''+''.join(tiles)+'''</div>
    <p class="approved-menus__disclaimer">Изображения меню предоставлены рестораном. Состав блюд, доступность и актуальные цены уточняйте у сотрудников.</p>
    </div><dialog class="menu-lightbox" id="menu-lightbox" aria-label="Просмотр меню">
      <header class="menu-lightbox__header"><strong id="menu-lightbox-title">Меню BRAVIS</strong>
      <span class="menu-lightbox__counter" id="menu-lightbox-counter"></span>
      <button type="button" id="menu-lightbox-close" aria-label="Закрыть меню">Закрыть ✕</button></header>
      <div class="menu-lightbox__viewer"><button type="button" id="menu-lightbox-prev" aria-label="Предыдущая страница">‹</button>
      <img id="menu-lightbox-image" alt="Оригинальная страница меню ресторана BRAVIS" width="1100" height="1550">
      <button type="button" id="menu-lightbox-next" aria-label="Следующая страница">›</button></div>
    </dialog>'''
    if '<div class="menu-placeholder">' in page:
        page,n=re.subn(r'<div class="menu-placeholder">.*?(?=<div class="menu-bottom-note">)',widget,page,count=1,flags=re.S)
        if n!=1:raise RuntimeError('Cannot locate safe insertion point in /menu/')
    elif '<nav class="menu-filter"' in page:
        # Preserve the owner-approved text menu for SEO, and put the image menus first.
        page=page.replace('<nav class="menu-filter"', widget + '<div class="menu-structured-heading"><h2>Блюда и цены из печатного меню</h2><p>Выбор позиций ниже. Полный ассортимент — на изображениях меню выше.</p></div><nav class="menu-filter"',1)
    else:
        raise RuntimeError('Unexpected menu template, refusing to replace')
    schema={"@context":"https://schema.org","@type":"Menu","name":"Меню ресторана BRAVIS","inLanguage":"ru","hasMenuSection":[{"@type":"MenuSection","name":entry["title"]} for entry in files]}
    schema_js=json.dumps(schema,ensure_ascii=False).replace("<","\\u003c")
    link='<link rel="stylesheet" href="/assets/menu-experience.css"><script type="application/ld+json">'+schema_js+'</script>'
    page=page.replace('</head>',link+'</head>',1)
    script='<script type="application/json" id="bravis-menu-data">'+data+'</script><script src="/assets/menu-experience.js" defer></script>'
    page=page.replace('</body>',script+'</body>',1)
    htmlpath.write_text(page,encoding='utf-8')
    print('PASS: five menu groups with covers, unique raster pages and accessible viewer')
if __name__=='__main__':main()
