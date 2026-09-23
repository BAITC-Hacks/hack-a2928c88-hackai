"""Local mock-only browser scenario for immutable first-stage terms and acceptance."""
import argparse
import json
from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8009')
    args = parser.parse_args()
    if not args.url.startswith(('http://127.0.0.1:', 'http://localhost:')):
        parser.error('Only disposable local demo instances')
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        request = page.request
        b = {'X-Demo-Role':'business'}
        t = {'X-Demo-Role':'team'}
        base = args.url + '/api'
        draft = request.post(base+'/drafts', headers=b, data=dict(text='Учебный поиск',industry='Синтетика',synthetic=True)).json()
        request.post(base+f"/drafts/{draft['id']}/clarify",headers=b)
        card = request.post(base+f"/drafts/{draft['id']}/card",headers=b,data={'answers':{}}).json()
        values = dict(title='Синтетическая приёмка этапа', need='Поиск по справочнику',data='Два учебных вопроса с ответами',
                      expected_result='Прототип поиска',success_criteria='Бизнес сверит оба ответа с эталоном')
        def mutate(suffix, payload=None, method='post'):
            response = getattr(request, method)(base+f"/cards/{card['id']}"+suffix,
                headers={**b,'If-Match':str(card['revision'])}, data=payload)
            assert response.ok, response.text()
            return response.json()
        card = mutate('', {'changes':values}, 'patch')
        card = mutate('/confirm', {'fields':list(values)})
        card = mutate('/publish')
        team = request.get(base+'/teams').json()[0]
        proposal = request.post(base+f"/cards/{card['id']}/proposals",headers=t,
            data=dict(team_id=team['id'],idea='Учебный прототип',plan='Проверим примеры',timeline='3 дня',prototype_url='https://example.com')).json()
        request.post(base+f"/proposals/{proposal['id']}/decision",headers=b,data={'action':'select'})
        page.add_init_script("localStorage.setItem('sana:last-business-card', " + json.dumps(card['id']) + ");")
        page.goto(args.url)
        page.get_by_role('button',name='Продолжить сохранённую карточку',exact=True).click()
        panel = page.locator('.bp-stages')
        try:
            panel.get_by_role('button',name='Зафиксировать условия этапа',exact=True).click(timeout=10000)
        except Exception:
            print(json.dumps({'errors':errors,'panel':panel.all_text_contents()}, ensure_ascii=True), flush=True)
            raise
        expect(panel).to_contain_text('Роль команды: отправить результат')
        panel.get_by_label('Ссылка на результат',exact=True).fill('https://example.com/result')
        panel.get_by_label('Что выполнено и как проверить',exact=True).fill('Реализован первый учебный вопрос.')
        panel.get_by_role('button',name='Отправить результат этапа',exact=True).click()
        expect(panel).to_contain_text('Роль бизнеса: проверить результат')
        panel.get_by_label('Что проверено или что нужно доработать',exact=True).fill('Добавьте второй ответ.')
        panel.get_by_role('button',name='Вернуть на доработку',exact=True).click()
        expect(panel).to_contain_text('Роль команды: доработать результат')
        panel.get_by_label('Что выполнено и как проверить',exact=True).fill('Оба ответа совпадают с учебными эталонами.')
        panel.get_by_role('button',name='Отправить результат этапа',exact=True).click()
        panel.get_by_label('Что проверено или что нужно доработать',exact=True).fill('Вручную проверены оба учебных ответа.')
        panel.get_by_role('button',name='Принять результат и начислить +10',exact=True).click()
        expect(panel.locator('.bp-stage-accepted')).to_contain_text('Баллы прогресса: 10')
        page.reload()
        page.get_by_role('button',name='Продолжить сохранённую карточку',exact=True).click()
        expect(page.locator('.bp-stage-accepted')).to_contain_text('Баллы прогресса: 10')
        retry = request.post(base+f"/proposals/{proposal['id']}/milestone",headers=b).json()
        assert retry == {'points':10,'already_awarded':True}
        assert not errors, errors
        browser.close()
    print('PASS: recover -> stage terms -> submit -> revision -> resubmit -> manual acceptance -> reload -> no duplicate points')


if __name__ == '__main__':
    main()
