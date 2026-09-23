"""Local browser proof of the read-only review workflow. Requires MOCK=1 server."""
import argparse
import json
from uuid import uuid4
from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8007')
    args = parser.parse_args()
    if not args.url.startswith(('http://127.0.0.1:', 'http://localhost:')):
        parser.error('Use a disposable local MOCK=1 database')
    values = dict(title='Проверка перед стартом ' + str(uuid4())[:8],
        context='Учебный магазин обрабатывает вопросы вручную.',
        need='Сделать поиск по учебному справочнику.', users='Консультанты.',
        data='Данные обсудим позже', constraints='3 дня, только учебные материалы.',
        expected_result='Веб-прототип с цитатами из справочника.',
        success_criteria='Правильный ответ на 8 из 10 учебных вопросов.',
        contact='demo@example.com', interaction_format='Учебный созвон.',
        feedback_process='Бизнес проверит 10 учебных вопросов.')
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        page.set_default_timeout(20000)
        errors = []
        page.on('pageerror', lambda err: errors.append(str(err)))
        page.route('**/api/drafts', lambda route: route.continue_(post_data=json.dumps({
            **route.request.post_data_json, 'synthetic': True})))
        page.goto(args.url)
        page.locator('#bp-text').fill('Синтетическая задача: поиск по справочнику магазина.')
        page.locator('#bp-industry').fill('Учебная торговля')
        page.get_by_role('button', name='Уточнить задачу', exact=True).click()
        page.get_by_role('button', name='Собрать карточку', exact=True).click()
        for field, value in values.items():
            page.locator('#bp-f-' + field).fill(value)
        expect(page.get_by_role('button', name='Что помешает начать?', exact=True)).to_be_disabled()
        page.get_by_role('button', name='Сохранить изменения', exact=True).click()
        expect(page.locator('.bp-dirty')).to_have_count(0)
        page.locator('#bp-f-data-ok').check()
        page.get_by_role('button', name='Что помешает начать?', exact=True).click()
        expect(page.locator('.bp-review-issue')).to_have_count(1)
        expect(page.locator('.bp-review')).to_contain_text('mock')
        expect(page.locator('#bp-f-data-ok')).to_be_checked()
        expect(page.locator('.bp-total strong')).to_have_text('0')
        page.get_by_role('button', name='Уточнить поле', exact=True).click()
        expect(page.locator('#bp-f-data')).to_be_focused()
        page.locator('#bp-f-data').fill('CSV из 20 синтетических вопросов доступен в учебном репозитории.')
        expect(page.locator('.bp-review')).to_contain_text('несохранённые')
        expect(page.get_by_role('button', name='Проверить ещё раз', exact=True)).to_be_disabled()
        page.get_by_role('button', name='Сохранить изменения', exact=True).click()
        expect(page.locator('.bp-review')).to_contain_text('устарели')
        # Provider/network failure retains text and leaves retry available.
        page.route('**/api/cards/*/review', lambda route: route.fulfill(status=503,
            content_type='application/json', body=json.dumps({'detail': 'Проверка недоступна'})))
        page.get_by_role('button', name='Проверить ещё раз', exact=True).click()
        expect(page.locator('.bp-review-status')).to_contain_text('недоступна')
        expect(page.locator('#bp-f-data')).to_have_value('CSV из 20 синтетических вопросов доступен в учебном репозитории.')
        page.unroute('**/api/cards/*/review')
        page.get_by_role('button', name='Проверить ещё раз', exact=True).click()
        expect(page.locator('.bp-review-status')).to_contain_text('не выявила замечаний')
        # Saved content is restored from the server; the browser stores only its ID.
        remembered = page.evaluate("localStorage.getItem('sana:last-business-card')")
        assert remembered and len(remembered) == 36
        page.reload()
        page.get_by_role('button', name='Продолжить сохранённую карточку', exact=True).click()
        expect(page.locator('#bp-f-data')).to_have_value('CSV из 20 синтетических вопросов доступен в учебном репозитории.')
        expect(page.locator('.bp-total strong')).to_have_text('0')
        page.get_by_role('button', name='Отметить все для подтверждения', exact=True).click()
        page.get_by_role('button', name='Подтвердить отмеченные', exact=True).click()
        expect(page.locator('.bp-total strong')).to_have_text('100')
        expect(page.locator('.bp-review-status')).to_contain_text('не выявила замечаний')
        page.get_by_role('button', name='Опубликовать', exact=True).click()
        expect(page.locator('.catalog-detail h3')).to_have_text(values['title'])
        expect(page.locator('.catalog-review')).to_contain_text('не выявила замечаний')
        expect(page.locator('.catalog-detail')).to_contain_text('Место №')
        assert not errors, errors
        browser.close()
    print('PASS: review -> quote -> focus -> edit -> stale -> failure/retry -> confirm -> published review/rank')


if __name__ == '__main__':
    main()
