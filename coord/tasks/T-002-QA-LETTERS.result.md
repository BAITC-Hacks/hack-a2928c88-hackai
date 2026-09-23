# T-002 — Questions and project recommendations

Implemented by Codex for the user-supplied five-page Sana Hub PDF. The actual PDF describes public card questions and questionnaire-based recommendation letters. The existing readiness/AI interview flow remains covered by regression checks.

## Delivered

- Q&A: per-student daily limit, similar questions, answer revisions, duplicate links, private decline/moderation reasons, subscriptions, exact-answer field suggestion and explicit transfer requiring renewed field confirmation.
- Transactional in-app outbox: hourly question digests, one 72-hour unanswered reminder, questionnaire reminders on days 3/7/14, recipient-only inbox.
- Project lifecycle, captain roster and individual confirmation; nine-question assessment with server validation and a 30-day submission window.
- Versioned RU/KK/EN phrase templates with source-linked preview, literal comments, immutable individual PDFs/QR, reissue/revoke, verification, visibility, public consent and moderator complaints.
- RU/KK interfaces integrated into card catalog, business editor and the new cooperation workspace. Public profiles expose only consented data.
- Opaque server sessions for explicitly labelled demo accounts. Existing legacy demo role endpoints remain demo endpoints. This is not production authentication.

## Files and ownership

Core: `app/community.py`, `app/questions.py`, `app/question_suggestion.py`, `app/project_letters.py`, `app/letter_pdf.py`, integration in `app/main.py`.

UI: new community/questions/project-letters modules and styles; small integration changes in business/catalog/index. Documentation: `docs/COMMUNITY.md`, README, `.env.example`. Tests: community, questions, question suggestion and project letters. Reproducible browser checks: `scripts/smoke_questions.py`, `scripts/smoke_project_letters.py`.

## Verification

- Full pytest run: 138 passed before final public-profile checks were added; final total is recorded in the PR.
- Q&A real API browser smoke: passed, including isolated drafts, owner answer/edit, reconfirmation transfer, duplicate source, notifications and Kazakh/mobile.
- Letters real API browser smoke: passed, including source edits, role/version race protection, PDF download, all verification statuses, complaint, consent, mobile and delayed response isolation after identity switch.
- Existing `scripts/smoke_e2e.py --mode mock`: passed (readiness 0 → 100 → 80 → 100, manual selection, milestone without regression).
- PDF Cyrillic/Kazakh text, QR and page layout visually checked; local PDF speed test passes. New AI selector uses a stubbed SDK in tests; no paid live-provider call or public deployment was made.

## Operational boundaries

Set `APP_PUBLIC_URL` to the actual HTTPS origin before issuing shared PDFs. Persist and back up SQLite: the current Render configuration is ephemeral. Notifications remain inside the application. Templates are translated; original business comments remain verbatim. Integration with real identity provisioning is required before production use. See `docs/COMMUNITY.md` for reproduction and acceptance mapping.

Work is prepared on the separate branch `team/questions-recommendations`; merging and deployment are separate actions.
