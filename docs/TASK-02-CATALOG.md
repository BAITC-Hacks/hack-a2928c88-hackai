# Разработчик 2 — T-002 / Nursaule: довести каталог, 25–35 минут

**Ветка:** team/catalog-ui. **Файлы:** app/static/catalog.js, app/static/catalog.css. Каталог уже интегрирован и прошёл базовый браузерный сценарий — сохранить работающую логику.

1. **Обязательная ссылка на прототип.** Убрать «необязательно», сделать prototype_url required, принимать только непустые HTTP(S) URL. Пустая ссылка и javascript: не отправляют запрос. Ошибка видна рядом с полем; введённые идея/план/срок не теряются. API уже проверяет ссылку, его менять не нужно.
2. **Фильтр отрасли без угадывания точного текста.** Сейчас свободный поиск отправляет строку в API, где требуется точное совпадение. Сделать select с пунктом «Все отрасли» и уникальными industry, полученными из api.listCards({}). Значения сохранять точно, как вернул сервер. После фильтрации список вариантов не сужать до одной выбранной отрасли; при refresh обновлять доступные варианты, сохраняя выбор, если он существует. Фильтр уровня сохранить; порядок карточек не пересчитывать в JS.
3. **Проверить и исправить граничные состояния.** Дать явные for/id или aria-label элементам select, чтобы подпись поля не включала текст всех options. Проверить «ничего не найдено → сброс фильтров», отклик на задачу <40, выбор нескольких, отклонение всех и повторное подтверждение этапа. На повторе баланс остаётся 10, читается с сервера. Если найдёте ошибку — исправить в своих файлах, не расширяя функционал.

**Приёмка:** пустая ссылка блокируется до API; оба фильтра работают совместно; сброс возвращает все задачи; новая опубликованная карточка появляется после refresh; отклик и ручное решение работают на локальном backend. Пришлите хеш коммита и краткий результат проверки. Не добавляйте автоназначение, новый рейтинг, backend или изменения общей страницы.

Перед работой сохраните свои изменения коммитом, выполните `git fetch origin`, затем в СВОЕЙ ветке `git merge origin/main`. Не используйте reset/force push. Команды запуска — ниже. Оба разработчика работают параллельно, каждый только в своих двух файлах.

Экспорт: `export function mountCatalog(root, api)` возвращает `{refresh}`. DOM внутри root; CSS ограничить `.catalog-panel`. Порядок карточек и баллы брать из API. Отклики не ранжировать через AI. Не использовать чувствительные признаки участников.

## Запуск и разделение ответственности

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Если .venv отсутствует, сначала `python -m venv .venv`. Для проверок используйте MOCK=1 в локальном .env (ключи не нужны). Открывайте http://127.0.0.1:8000. Это работающий API, не будущий контракт. Чужой экран может отсутствовать в вашей ветке — не создавайте его заново. Изменения локальной ветки не появляются на Render автоматически.

Codex: ревью и интеграция обоих коммитов, проверка полного сценария, адаптер/backend при необходимости, новый приватный образ и обновление деплоя. Четыре UI-файла остаются за владельцами. Коммиты, созданные преимущественно Codex, — с префиксом [codex].

## Общий контракт для независимой работы

Методы `api` возвращают Promise. Интерфейс реализован в app/static/api.js и app/main.py. Версии If-Match и demo-роли передаёт адаптер; экраны вызывают методы ниже.

```js
// Экран бизнеса
api.createDraft({text, industry}) // -> {id}
api.clarifyDraft(draftId) // -> {questions:[{id,field,question}], mode:'live'|'mock'}
api.buildCard(draftId, {answers:{questionId:'текст'}}) // -> CardView
api.updateCard(cardId, {changes:{field:'значение'}}) // -> CardView, без подтверждения
api.confirmCard(cardId, {fields:['context','need']}) // -> CardView
api.publishCard(cardId) // -> CardView; вызвать onPublished()
api.getCard(cardId) // -> актуальный CardView; только по явному действию при конфликте

// Каталог и отклики
api.listCards({industry:'', level:''}) // -> CardView[], по рейтингу
api.listTeams() // -> [{id,name,interests,skills,technologies}]
api.createProposal(cardId, {team_id,idea,plan,timeline,prototype_url}) // -> ProposalView
api.listProposals(cardId) // -> ProposalView[]
api.decideProposal(proposalId, {action:'select'|'reject'}) // -> ProposalView
api.confirmMilestone(proposalId) // -> {points:10, already_awarded:false}
```

`CardView = {id, industry, title, context, need, users, data, constraints, expected_result, success_criteria, contact, interaction_format, feedback_process, confirmed_fields:[], evidence:{field:{source_id,quote}}, rating:{total,level,items:[{key,label,maximum,earned,explanation}],missing_fields:[]}, published, synthetic, mode}`.

`ProposalView = {id, task_id, team_id, team_name, idea, plan, timeline, prototype_url, status:'pending'|'selected'|'rejected', progress_points}`.

Уровни: `draft` / `working` / `ready` / `priority`; русские подписи «Черновик» / «Рабочая» / «Готовая» / «Приоритетная». Синтетику и mock показывать явно. Проверяемая исходная схема в app/schemas.py; API-адаптер превратит её в CardView. Расширение внутренних подполей рейтинга не должно менять этот интерфейс без согласования с ребятами.
