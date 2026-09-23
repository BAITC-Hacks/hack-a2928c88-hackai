"""Exercise recommendation letters in a local, disposable browser demo.

    python scripts/smoke_project_letters.py --url http://127.0.0.1:8009 --serve-isolated

Without --serve-isolated, the URL must point to an already running disposable
demo. Synthetic setup creates one selected proposal; all project/letter actions
then use the real UI. Requires the optional Playwright dev tool and Edge.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from urllib.parse import quote, urlsplit
from uuid import uuid4

import httpx
from playwright.sync_api import expect, sync_playwright


def check(base):
    with httpx.Client(base_url=base) as api:
        card = api.get('/api/cards').json()[0]
        team = api.get('/api/teams').json()[0]
        response = api.post('/api/cards/' + card['id'] + '/proposals',
            headers={'X-Demo-Role': 'team'}, json={
                'team_id': team['id'], 'idea': 'Synthetic letters browser test ' + str(uuid4())[:8],
                'plan': 'Build and verify a synthetic prototype', 'timeline': 'Three days',
                'prototype_url': 'https://example.com/letters-smoke'})
        assert response.status_code < 300, response.text
        proposal = response.json()
        response = api.post('/api/proposals/' + proposal['id'] + '/decision',
            headers={'X-Demo-Role': 'business'}, json={'action': 'select'})
        assert response.status_code < 300, response.text

    logs = Path(__file__).resolve().parents[1] / 'logs'
    logs.mkdir(exist_ok=True)
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(channel='msedge', headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
        page = context.new_page()
        errors, failures = [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('response', lambda response: failures.append((response.status, response.url)) if response.status >= 500 else None)
        page.goto(base + '/#community')
        identity = page.locator('.community-header select').nth(0)
        expect(identity.locator('option')).not_to_have_count(1)

        def settled():
            expect(page.locator('.project-letters')).to_have_attribute('aria-busy', 'false')
            assert not page.locator('.pl-error:visible').count(), page.locator('.pl-error:visible').all_text_contents()

        def select_actor(user):
            identity.select_option(user)
            expect(identity).to_be_enabled()
            settled()

        def open_project():
            expect(page.locator('.pl-project-choice')).to_have_count(1)
            page.locator('.pl-project-choice').click()
            expect(page.locator('.pl-detail > .pl-section')).not_to_have_count(0)
            settled()

        select_actor(team['id'] + ':captain')
        page.evaluate('(id) => dispatchEvent(new CustomEvent("community-open-project", {detail:id}))', proposal['id'])
        expect(page.locator('.pl-member-edit')).to_have_count(2)
        for index in range(2):
            page.locator('.pl-member-edit input[type=checkbox]').nth(index).check()
        page.locator('.pl-member-edit select').nth(0).select_option('developer')
        page.locator('.pl-member-edit select').nth(1).select_option('analyst')
        roster = page.locator('.pl-detail > .pl-section').nth(1)
        roster.locator('button[type=submit]').click()
        expect(roster.locator('button[type=button]')).to_have_count(1)
        roster.locator('button[type=button]').click()
        expect(roster.locator('button[type=button]')).to_have_count(0)
        select_actor(team['id'] + ':member')
        open_project()
        page.locator('.pl-detail > .pl-section').nth(1).locator('button').click()
        expect(page.locator('.pl-detail > .pl-section').nth(1).locator('button')).to_have_count(0)

        select_actor('demo-business')
        open_project()
        close_form = page.locator('form').filter(has=page.locator('input[value="closed_early"]'))
        close_form.locator('input[value="closed_early"]').check()
        close_form.locator('input[type=checkbox]').check()
        close_form.locator('button[type=submit]').click()
        expect(page.locator('.pl-question')).to_have_count(9)
        for question, value in [('q1', 'exceeds'), ('q4', 'meets'), ('q5', 'testing'), ('q6', 'yes'), ('q7', 'maybe')]:
            page.locator(f'[id$="-{question}-answer"]').select_option(value)
        page.locator('[id$="-q2-answer-1"]').check()
        page.locator('[id$="-q3-answer"]').check()
        page.locator('[id$="-q8-answer"]').check()
        evidence = 'The team built a working prototype and verified twenty labelled examples against the expected results.'
        page.locator('[id$="-q1-comment"]').fill('Useful and reproducible result.')
        page.locator('[id$="-q2-comment"]').fill(evidence)
        page.locator('[id$="-q9-comment"]').fill('Thank you for clearly documenting the validation method.')
        page.locator('.pl-assessment-form button[type=submit]').click()
        expect(page.locator('.pl-preview')).to_be_visible()
        page.locator('.pl-sentence').filter(has_text=evidence).click()
        assert page.evaluate('document.activeElement.id.endsWith("q2-comment")')
        page.locator('[id$="-q2-comment"]').fill(evidence + ' Updated after review.')
        expect(page.locator('.pl-preview')).to_have_count(0)
        page.locator('.pl-assessment-form button[type=submit]').click()
        expect(page.locator('.pl-preview')).to_be_visible()
        page.locator('.pl-preview input').nth(0).fill('Synthetic Project Owner')
        page.locator('.pl-preview input').nth(1).fill('Programme Manager')
        page.locator('.pl-preview button[type=submit]').click()
        expect(page.locator('.pl-letter-entry').filter(has=page.locator('.pl-row'))).to_have_count(1)
        settled()
        page.screenshot(path=str(logs / 'letters-real-issued-desktop.png'), full_page=True)

        # Reissue exactly the reviewed preview; previous immutable version remains.
        page.locator('[id$="-q9-comment"]').fill('An additional verified result was documented in the project report.')
        page.locator('.pl-assessment-form button[type=submit]').click()
        expect(page.locator('.pl-preview')).to_be_visible()
        page.locator('.pl-preview button[type=submit]').click()
        expect(page.locator('.pl-letter-entry').filter(has=page.locator('.pl-row'))).to_have_count(2)
        select_actor(team['id'] + ':member')
        expect(page.locator('.pl-copy')).to_have_count(2)
        current_copy = page.locator('.pl-copy').filter(has=page.locator('.pl-badge-issued'))
        old_copy = page.locator('.pl-copy').filter(has=page.locator('.pl-badge-replaced'))
        with page.expect_download() as item:
            current_copy.locator('button').first.click()
        pdf_path = logs / 'letters-real-personal.pdf'
        item.value.save_as(str(pdf_path))
        assert pdf_path.read_bytes().startswith(b'%PDF')
        verify_url = current_copy.locator('a').get_attribute('href')
        assert context.request.get(base + verify_url + '?format=json').json()['status'] == 'valid'
        old_url = old_copy.locator('a').get_attribute('href')
        assert context.request.get(base + old_url + '?format=json').json()['status'] == 'replaced'
        current_copy.locator('input[type=checkbox]').check()
        settled()
        expect(current_copy.locator('input[type=checkbox]')).to_be_checked()
        # A shareable profile exposes only the explicitly visible copy.
        profile_page = context.new_page()
        own_profile = page.locator('.pl-copies > .pl-public-profile').get_attribute('href')
        profile_page.goto(base + own_profile)
        expect(profile_page.locator('a[href*="/verify/"]')).to_have_count(1)
        assert verify_url in profile_page.locator('a[href*="/verify/"]').get_attribute('href')
        assert old_url not in profile_page.content()
        assert evidence not in profile_page.locator('body').inner_text()
        profile_page.close()
        current_copy.locator('summary').click()
        current_copy.locator('textarea').fill('Please verify the named role against the recorded project roster.')
        current_copy.locator('button[type=submit]').click()
        expect(current_copy.locator('textarea')).to_have_value('')

        # Hold an authenticated response, switch identity, then release old data.
        page.evaluate('''() => {
            const original = window.fetch; let once = true;
            window.fetch = async (...args) => {
                const response = await original(...args);
                if (once && args[0] === '/api/projects') {
                    once = false;
                    return new Promise(resolve => { window.releaseOldProjects = () => resolve(response); });
                }
                return response;
            };
        }''')
        page.locator('.pl-head button').click()
        page.wait_for_function('typeof window.releaseOldProjects === "function"')
        identity.select_option('other-business')
        expect(identity).to_be_enabled()
        expect(page.locator('.pl-copy')).to_have_count(0)
        page.evaluate('window.releaseOldProjects()')
        settled()
        expect(page.locator('.pl-copy')).to_have_count(0)
        expect(page.locator('.pl-project-choice')).to_have_count(0)

        select_actor(team['id'] + ':captain')
        open_project()
        consent = page.locator('.pl-consent input[type=checkbox]')
        consent.check()
        settled()
        expect(consent).to_be_checked()
        public = context.request.get(base + '/api/teams/' + quote(team['id']) + '/project-recommendations').json()
        assert len(public) == 1 and set(public[0]) == {'project_id', 'prototype_fate', 'result_comment'}, public
        expect(page.locator('.pl-public-reviews')).to_contain_text('Useful and reproducible result.')
        team_profile = page.locator('.pl-public-reviews > .pl-public-profile').get_attribute('href')
        profile_page = context.new_page()
        profile_page.goto(base + team_profile)
        expect(profile_page.locator('body')).to_contain_text('Useful and reproducible result.')
        assert evidence not in profile_page.locator('body').inner_text()
        assert 'An additional verified result' not in profile_page.locator('body').inner_text()
        profile_page.close()
        expect(page.locator('.pl-question')).to_have_count(0)
        page.locator('.community-header select').nth(1).select_option('kk')
        page.set_viewport_size({'width': 390, 'height': 844})
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        page.screenshot(path=str(logs / 'letters-real-kk-mobile.png'), full_page=True)

        page.set_viewport_size({'width': 1440, 'height': 1000})
        select_actor('demo-business')
        open_project()
        revoke = page.locator('.pl-revoke').first
        revoke.locator('summary').click()
        revoke.locator('textarea').fill('Synthetic verification: the letter is revoked for a recorded factual correction.')
        revoke.locator('button[type=submit]').click()
        expect(page.locator('.pl-revoke')).to_have_count(0)
        assert context.request.get(base + verify_url + '?format=json').json()['status'] == 'revoked'
        assert not errors, errors
        assert not failures, failures
        print(json.dumps({'result': 'PASS', 'confirmed_members': 2, 'issued_versions': 2,
            'pdf_bytes': pdf_path.stat().st_size, 'verification': ['valid', 'replaced', 'revoked'],
            'browser_errors': errors, 'server_errors': failures, 'mobile_overflow': False,
            'actor_switch_during_request': 'isolated', 'public_profile_fields': ['prototype_fate', 'result_comment'],
            'public_pages': ['visible-copy-only', 'consented-q1-q5-only'],
            'screenshots': ['logs/letters-real-issued-desktop.png', 'logs/letters-real-kk-mobile.png'],
            'pdf': 'logs/letters-real-personal.pdf'}, ensure_ascii=True))
        browser.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8009')
    parser.add_argument('--serve-isolated', action='store_true')
    args = parser.parse_args()
    parsed = urlsplit(args.url)
    if (parsed.scheme != 'http' or parsed.hostname not in {'localhost', '127.0.0.1', '::1'}
            or parsed.path not in {'', '/'} or parsed.query or parsed.fragment or parsed.username):
        parser.error('This smoke creates synthetic records: use a disposable localhost demo only')
    base = args.url.rstrip('/')
    server, thread = None, None
    if args.serve_isolated:
        import uvicorn
        workspace = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(workspace))
        scratch = Path(tempfile.mkdtemp(prefix='sana-letters-ui-')).resolve()
        assert scratch.is_relative_to(Path(tempfile.gettempdir()).resolve())
        os.environ.update(MOCK='1', COMMUNITY_DEMO='1', DATABASE_PATH=str(scratch / 'demo.sqlite3'), APP_PUBLIC_URL=base)
        from app.main import app
        server = uvicorn.Server(uvicorn.Config(app, host=parsed.hostname, port=parsed.port or 80, log_level='error'))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        for _ in range(100):
            if server.started:
                break
            if not thread.is_alive():
                raise RuntimeError('Isolated server could not bind; select another free local port')
            time.sleep(.1)
        if not server.started:
            raise RuntimeError('Isolated server did not start')
    try:
        check(base)
    finally:
        if server:
            server.should_exit = True
            thread.join(timeout=3)


if __name__ == '__main__':
    main()
