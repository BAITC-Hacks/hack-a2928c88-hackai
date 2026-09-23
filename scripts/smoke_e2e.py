"""Full browser scenario on localhost only. With --mode live this spends two AI calls."""
import argparse
import json
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8002')
    parser.add_argument('--mode', choices=['live', 'mock'], default='mock')
    args = parser.parse_args()
    if not args.url.startswith(('http://127.0.0.1:', 'http://localhost:')):
        parser.error('Creates demo records; localhost only')
    unique = 'Синтетическая задача ' + str(uuid4())[:8]
    values = {
        'title': unique,
        'context': 'Синтетический магазин получает вопросы по электронной почте.',
        'need': 'Нужен помощник для ответов по каталогу товаров.',
        'users': 'Консультанты учебного магазина.',
        'data': '100 синтетических вопросов и CSV с 20 вымышленными товарами.',
        'constraints': 'Прототип за 3 дня, только синтетические данные.',
        'expected_result': 'Веб-прототип поиска ответов с указанием товара.',
        'success_criteria': 'Не менее 8 верных ответов на 10 контрольных вопросов.',
        'contact': 'demo@example.com, вымышленный контакт.',
        'interaction_format': 'Один учебный созвон для уточнений.',
        'feedback_process': 'Проверка прототипа по контрольным вопросам через 3 дня.',
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width':1440,'height':1000})
        page.set_default_timeout(20000)
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(args.url)
        page.locator('#bp-text').fill('Синтетический пример: нужен чат-бот для нашего учебного магазина.')
        page.locator('#bp-industry').fill('Учебная торговля')
        with page.expect_response(lambda r: r.url.endswith('/clarify'), timeout=60000) as pending:
            page.get_by_role('button', name='Уточнить задачу', exact=True).click()
        clarification = pending.value.json()
        assert pending.value.ok and clarification['mode'] == args.mode, clarification
        assert len(clarification['questions']) >= 3
        for q in clarification['questions']:
            page.locator('#bp-q-' + q['id']).fill(values.get(q['field'], 'Сведения пока не определены.'))
        with page.expect_response(lambda r: r.url.endswith('/card'), timeout=60000) as pending:
            page.get_by_role('button', name='Собрать карточку', exact=True).click()
        built = pending.value.json()
        assert pending.value.ok and built['mode'] == args.mode, built
        expect(page.locator('.bp-total strong')).to_have_text('0')
        # Human edits are explicit; no AI-invented fields are silently introduced.
        for field, value in values.items():
            page.locator('#bp-f-' + field).fill(value)
        page.get_by_role('button', name='Сохранить изменения', exact=True).click()
        expect(page.locator('.bp-dirty')).to_have_count(0)
        for field in values:
            page.locator('#bp-f-' + field + '-ok').check()
        page.get_by_role('button', name='Подтвердить отмеченные', exact=True).click()
        expect(page.locator('.bp-total strong')).to_have_text('100')
        page.locator('#bp-f-data').fill('Обновлено человеком: 120 синтетических вопросов и CSV с 20 товарами.')
        page.get_by_role('button', name='Сохранить изменения', exact=True).click()
        expect(page.locator('.bp-total strong')).to_have_text('80')
        page.locator('#bp-f-data-ok').check()
        page.get_by_role('button', name='Подтвердить отмеченные', exact=True).click()
        expect(page.locator('.bp-total strong')).to_have_text('100')
        page.get_by_role('button', name='Опубликовать', exact=True).click()
        card = page.locator('.catalog-card').filter(has_text=unique)
        expect(card).to_be_visible()
        card.get_by_role('button', name='Посмотреть задачу', exact=True).click()
        page.locator('.catalog-proposal-form select').select_option(index=1)
        proposal_title = 'Учебный прототип ' + unique
        page.locator('[name=idea]').fill(proposal_title)
        page.locator('[name=plan]').fill('Изучить синтетические данные, собрать и проверить прототип.')
        page.locator('[name=timeline]').fill('3 дня')
        page.locator('[name=prototype_url]').fill('https://example.com/e2e-prototype')
        page.get_by_role('button', name='Отправить отклик', exact=True).click()
        proposal = page.locator('.catalog-proposal').filter(has_text=proposal_title)
        expect(proposal).to_be_visible()
        proposal.get_by_role('button', name='Выбрать', exact=True).click()
        expect(proposal).to_contain_text('Команда выбрана')
        proposal.get_by_role('button', name='Подтвердить этап', exact=True).click()
        expect(proposal).to_contain_text('Баллы прогресса: 10')
        expect(page.locator('.catalog-notice')).to_contain_text('Этап подтверждён')
        proposal.get_by_role('button', name='Подтвердить этап', exact=True).click()
        expect(page.locator('.catalog-notice')).to_contain_text('Повторного начисления нет')
        page.route('**/api/drafts', lambda route: route.fulfill(status=503, content_type='text/plain', body='upstream unavailable'))
        message = page.evaluate("""async () => {
            const {api} = await import('/static/api.js');
            try { await api.createDraft({text:'synthetic',industry:'demo'}); }
            catch (error) { return error.message; }
        }""")
        assert 'HTTP 503' in message and 'SyntaxError' not in message
        assert not errors, errors
        Path('logs').mkdir(exist_ok=True)
        page.screenshot(path='logs/e2e-' + args.mode + '.png', full_page=True)
        print(json.dumps({'e2e':'passed','mode':args.mode,'provider':built['provider'],
            'score_sequence':[0,100,80,100],'manual_selection':True,'progress_points':10},ensure_ascii=True))
        browser.close()


if __name__ == '__main__':
    main()
