"""Browser regression for the separate review; disposable local MOCK=1 server only."""
import argparse
import json
from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8014')
    args = parser.parse_args()
    if not args.url.startswith(('http://127.0.0.1:', 'http://localhost:')):
        parser.error('Use a disposable local MOCK=1 database')
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width':1440, 'height':1000})
        request = page.request
        base = args.url.rstrip('/') + '/api'
        assert request.get(args.url.rstrip('/')+'/health').json()['configured_mode'] == 'mock'
        card = request.get(base+'/cards').json()[0]
        assert card['synthetic']
        path = base+'/cards/'+card['id']
        card = request.get(path).json()
        response = request.patch(path, headers={'X-Demo-Role':'business','If-Match':str(card['revision'])},
                                 data={'changes':{'data':'Данные обсудим позже'}})
        assert response.ok, response.text()
        card = response.json()
        page.add_init_script("localStorage.setItem('sana:last-business-card',"+json.dumps(card['id'])+");")
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(args.url)
        page.get_by_role('button', name='Продолжить сохранённую карточку',exact=True).click()
        primary, second = page.locator('.bp-step-card .bp-review'), page.locator('.bp-nvidia-review')
        checked = page.locator('[data-field="data"]').locator('xpath=..').get_by_role('checkbox')
        checked.check()
        primary.locator('button.bp-primary').click()
        expect(primary).to_contain_text('Демонстрационная проверка')
        before = request.get(path).json()
        second.get_by_role('button',name='Второе мнение NVIDIA',exact=True).click()
        expect(second).to_contain_text('Демонстрационная проверка')
        expect(checked).to_be_checked()
        after = request.get(path).json()
        assert after['review'] == before['review']
        assert after['rating'] == before['rating'] and after['confirmed_fields'] == before['confirmed_fields']
        assert after['nvidia_review']['mode'] == 'mock'
        # A failed second opinion must preserve primary review and pending confirmation.
        page.route('**/review/nvidia', lambda route: route.fulfill(status=503, content_type='application/json',
                    body=json.dumps({'detail':'NVIDIA unavailable (synthetic test)'})))
        second.get_by_role('button',name='Второе мнение NVIDIA',exact=True).click()
        expect(second.locator('.bp-review-status')).to_contain_text('Проверка недоступна')
        expect(checked).to_be_checked()
        expect(primary).to_contain_text('Демонстрационная проверка')
        assert request.get(path).json() == after
        page.unroute('**/review/nvidia')
        page.locator('[data-field="data"]').fill('Доступны учебные CSV и эталоны ответов')
        expect(second.get_by_role('button',name='Второе мнение NVIDIA',exact=True)).to_be_disabled()
        expect(primary).to_contain_text('Есть несохранённые правки')
        expect(second).to_contain_text('Есть несохранённые правки')
        page.get_by_role('button',name='Сохранить изменения',exact=True).click()
        expect(second).to_contain_text('результаты проверки устарели')
        expect(primary).to_contain_text('результаты проверки устарели')
        page.reload()
        page.get_by_role('button',name='Продолжить сохранённую карточку',exact=True).click()
        expect(page.locator('.bp-nvidia-review')).to_contain_text('результаты проверки устарели')
        assert not errors, errors
        browser.close()
        print('PASS: separate mock opinion -> no score/input changes -> failure preserves data -> stale -> F5')


if __name__ == '__main__':
    main()
