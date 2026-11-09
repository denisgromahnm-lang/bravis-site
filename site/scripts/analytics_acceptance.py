"""Synthetic goal acceptance; no events are sent to Yandex or order services."""
import json
from playwright.sync_api import expect


def accept_analytics(browser, base, root, report):
    tables = json.loads((root / 'content/table-links.json').read_text())['tables']
    errors = []

    def context(consent=None):
        result = browser.new_context(viewport={'width': 390, 'height': 844})
        if consent is not None:
            result.add_init_script('localStorage.setItem("bravis_analytics_consent_v1",' + json.dumps(consent) + ')')
        def intercept(route):
            if route.request.url.startswith(base + '/'):
                route.continue_()
            elif route.request.url.startswith('https://mc.yandex.com/metrika/tag.js'):
                route.fulfill(status=200, content_type='application/javascript', body='')
            else:
                route.abort()
        result.route('**/*', intercept)
        page = result.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        return result, page

    def goals(page):
        return page.evaluate('()=>Array.from(window.ym?.a||[],value=>Array.from(value)).filter(value=>value[1]==="reachGoal")')

    def click(link):
        # Real pointer interaction, while staying on the fixture page.
        link.evaluate('(element)=>element.addEventListener("click",event=>event.preventDefault(),{once:true})')
        link.click()

    yes, page = context('yes')
    checks = []
    for table in tables:
        page.goto(base + '/t/' + table['id'] + '/', wait_until='networkidle')
        order = page.locator('[data-track="table_lunch_click"]')
        expect(order).to_have_attribute('href', table['orderUrl'])
        click(order)
        click(page.locator('[data-track="loona_signup_click"]'))
        values = goals(page)
        assert [value[2] for value in values] == ['table_lunch_click', 'loona_signup_click']
        assert all(value[0] == 113768615 and value[3] == {'table_id': table['id']} for value in values), values
        expect(order).to_have_attribute('href', table['orderUrl'])
        checks.append(table['id'])
    assert '20' in checks and 'bar-20' in checks

    page.goto(base + '/banquets/', wait_until='networkidle')
    choices = page.locator('[data-track="banquet_menu_request"]')
    expect(choices).to_have_count(3)
    for choice in choices.all():
        click(choice)
    values = goals(page)
    assert [value[2] for value in values] == ['banquet_menu_request'] * 3
    assert [value[3] for value in values] == [{'messenger': key} for key in ('whatsapp', 'telegram', 'max')]

    # A semantic goal and an identical data-track marker must produce one goal.
    page.evaluate('''()=>{
        const fixture=document.createElement('div');fixture.id='analytics-fixture';
        fixture.innerHTML='<a href="tel:+70000000000" data-track="phone_click">Тест звонка</a><a href="/menu/" data-track="menu_open"><span>Тест меню</span></a>';
        document.querySelector('main').prepend(fixture);
    }''')
    click(page.locator('#analytics-fixture a').nth(0))
    click(page.locator('#analytics-fixture a').nth(1))
    assert [value[2] for value in goals(page)][-2:] == ['phone_click', 'menu_open']
    yes.close()

    denied, page = context()
    requests = []
    page.on('request', lambda request: requests.append(request.url) if 'mc.yandex.com/' in request.url else None)
    page.goto(base + '/t/bar-20/', wait_until='networkidle')
    click(page.locator('[data-track="table_lunch_click"]'))
    assert not goals(page) and not requests
    page.locator('[data-consent="no"]').click()
    click(page.locator('[data-track="loona_signup_click"]'))
    page.reload(wait_until='networkidle')
    assert not goals(page) and not requests
    expect(page.locator('.cookie-banner')).to_have_count(0)
    denied.close()
    assert not errors, errors
    (report / 'analytics-goals-acceptance.json').write_text(json.dumps({
        'status': 'PASS', 'table_ids': checks, 'table_and_signup_parameters': True,
        'bar_20_distinct_from_table_20': True, 'banquet_messengers': ['whatsapp', 'telegram', 'max'],
        'consent_and_denial_preserved': True, 'identical_goal_deduplicated': True,
        'real_external_goal_or_order_requests': 0,
    }, ensure_ascii=False, indent=2) + '\n')
    print('PASS: all31 table/signup goal parameters, distinct bar20/table20, messenger choice, consent and one goal per semantic click; synthetic only')
