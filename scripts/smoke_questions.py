"""Q&A acceptance in installed Edge. Only use a disposable local demo database."""
import argparse
import re
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8008')
    args = parser.parse_args()
    parsed = urlsplit(args.url)
    if (parsed.scheme != 'http' or parsed.hostname not in {'localhost', '127.0.0.1', '::1'}
            or parsed.path not in {'', '/'} or parsed.query or parsed.fragment or parsed.username):
        parser.error('This smoke creates synthetic questions. Use a disposable local demo database.')
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        page.set_default_timeout(12000)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url + '/#community')
        expect(page.locator('#community')).to_be_visible()
        users = page.request.get(args.url + '/api/community').json()['users']
        student = next(user for user in users if user['role'] == 'student')
        identity = page.get_by_label('Учётная запись / Пайдаланушы', exact=True)

        def switch(user_id):
            page.get_by_role('tab', name='Сотрудничество', exact=True).click()
            identity.select_option(user_id)
            expect(page.locator('.community-header .community-notice')).to_contain_text('выбрана')

        switch(student['id'])
        page.get_by_role('tab', name='Командам', exact=True).click()
        page.locator('.catalog-open').first.click()
        page.get_by_role('tab', name=re.compile('^Вопросы')).click()
        panel = page.locator('#catalog .community-questions')
        unique = str(uuid4())[:8]
        first_text = f'Какие данные доступны для проверки прототипа? {unique}'
        second_text = f'Как получить тестовый набор материалов? {unique}'

        def ask(text):
            panel.get_by_label('Ваш вопрос', exact=True).fill(text)
            expect(panel.get_by_role('button', name='Отправить вопрос', exact=True)).to_be_disabled()
            panel.get_by_role('button', name='Найти похожие вопросы', exact=True).click()
            expect(panel.get_by_role('button', name='Отправить вопрос', exact=True)).to_be_enabled()
            panel.get_by_role('button', name='Отправить вопрос', exact=True).click()
            expect(panel.locator('.community-question').filter(has_text=text)).to_be_visible()

        ask(first_text)
        ask(second_text)
        first = panel.locator('.community-question').filter(has_text=first_text)
        second = panel.locator('.community-question').filter(has_text=second_text)
        first.get_by_role('button', name='Редактировать вопрос', exact=True).click()
        first.get_by_label('Сохранить вопрос', exact=True).fill('Несохранённый черновик первого вопроса')
        first.get_by_role('button', name='Отмена', exact=True).click()
        second.get_by_role('button', name='Редактировать вопрос', exact=True).click()
        expect(second.get_by_label('Сохранить вопрос', exact=True)).to_have_value(second_text)
        second.get_by_role('button', name='Отмена', exact=True).click()

        switch('demo-business')
        page.get_by_role('tab', name='Командам', exact=True).click()
        expect(panel.get_by_role('button', name='Подписаться на ответы', exact=True)).to_have_count(0)
        first.get_by_role('button', name='Ответить', exact=True).click()
        answer = 'Передадим 30 синтетических записей после согласования состава команды.'
        first.get_by_label('Ответить', exact=True).fill(answer)
        first.locator('form').get_by_role('button', name='Ответить', exact=True).click()
        expect(first.locator('blockquote')).to_have_text(answer)
        first.get_by_role('button', name='Сохранить исправленный ответ', exact=True).click()
        first.get_by_label('Сохранить исправленный ответ', exact=True).fill(answer + ' В формате CSV.')
        first.locator('form').get_by_role('button', name='Сохранить исправленный ответ', exact=True).click()
        expect(first).to_contain_text('изменён')
        first.get_by_role('button', name='Предложить перенос в карточку', exact=True).click()
        expect(first.get_by_label('Поле карточки', exact=True)).to_have_value('data')
        first.get_by_role('button', name='Перенести в рабочую карточку', exact=True).click()
        expect(first).to_contain_text('Перенесено в рабочую карточку')
        second.get_by_role('button', name='Отметить дубликат', exact=True).click()
        second.get_by_label('Исходный вопрос', exact=True).select_option(label=first_text)
        second.locator('form').get_by_role('button', name='Отметить дубликат', exact=True).click()
        expect(second).to_contain_text('Дубликат')
        second.get_by_role('button', name='Исходный вопрос', exact=True).click()
        expect(second.locator('.community-original')).to_contain_text(answer)

        switch(student['id'])
        expect(page.locator('.community-inbox')).to_contain_text('Получен ответ')
        page.get_by_role('tab', name='Командам', exact=True).click()
        expect(first.locator('blockquote')).to_contain_text(answer)
        expect(first.get_by_role('button', name='Редактировать вопрос', exact=True)).to_have_count(0)
        page.get_by_role('tab', name='Сотрудничество', exact=True).click()
        page.get_by_label('Язык / Тіл', exact=True).select_option('kk')
        page.get_by_role('tab', name='Командам', exact=True).click()
        expect(panel.get_by_label('Сұрақтар', exact=True)).to_be_visible()
        page.set_viewport_size({'width': 390, 'height': 844})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Horizontal overflow'
        Path('logs/community-qa').mkdir(parents=True, exist_ok=True)
        page.screenshot(path='logs/community-qa/questions-mobile.png', full_page=True)
        assert not errors, errors
        browser.close()
    print('PASS: similar -> question -> isolated drafts -> owner answer/edit -> transfer -> duplicate link -> student inbox -> KK/mobile')


if __name__ == '__main__':
    main()
