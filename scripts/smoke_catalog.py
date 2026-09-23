"""Browser acceptance of T-002; use only a disposable local demo database.

Optional dev tool: pip install playwright==1.63.0; installed Edge is used.
"""
import argparse
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    args = parser.parse_args()
    if not args.url.startswith(('http://127.0.0.1:', 'http://localhost:')):
        parser.error('This test creates a proposal: use a disposable local demo only')
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width':1440, 'height':1000})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url)
        page.get_by_role('tab', name='Командам', exact=True).click()
        expect(page.locator('.catalog-card').first).to_be_visible()
        page.locator('.catalog-levels .chip').filter(has_text='Черновик').click()
        expect(page.locator('.catalog-card.level-draft').first).to_be_visible()
        expect(page.locator('.catalog-card:not(.level-draft)')).to_have_count(0)
        page.locator('.catalog-open').first.click()
        page.get_by_role('tab', name='Откликнуться', exact=True).click()
        page.locator('.catalog-proposal-form select').select_option(index=1)
        unique = 'Browser smoke ' + str(uuid4())[:8]
        page.get_by_label('Идея решения', exact=True).fill(unique)
        page.get_by_label('План работы', exact=True).fill('Синтетический прототип и проверка результата')
        page.get_by_label('Срок', exact=True).fill('3 дня')
        page.get_by_role('button', name='Отправить отклик', exact=True).click()
        # The link is required by the API; the form now blocks the request before it is sent.
        expect(page.locator('input[name=prototype_url]:invalid')).to_have_count(1)
        page.locator('input[name=prototype_url]').fill('https://example.com/browser-smoke')
        page.get_by_role('button', name='Отправить отклик', exact=True).click()
        proposal = page.locator('.catalog-proposal').filter(has_text=unique)
        expect(proposal).to_be_visible()
        proposal.get_by_role('button', name='Выбрать', exact=True).click()
        expect(proposal).to_contain_text('Команда выбрана')
        proposal.get_by_role('button', name='Подтвердить этап', exact=True).click()
        expect(proposal).to_contain_text('Баллы прогресса: 10')
        expect(page.locator('.catalog-notice')).to_contain_text('подтверждён')
        proposal.get_by_role('button', name='Подтвердить этап', exact=True).click()
        expect(page.locator('.catalog-notice')).to_contain_text('Повторного начисления нет')
        Path('logs').mkdir(exist_ok=True)
        page.screenshot(path='logs/catalog-smoke.png', full_page=True)
        assert not errors, errors
        browser.close()
        print('PASS: low-score catalogue -> proposal -> manual selection -> milestone -> no duplicate points')


if __name__ == '__main__':
    main()
