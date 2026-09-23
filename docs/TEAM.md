# Две задачи разработки — AI Sana

Прежние задания на тестовые тексты и питч отменены. Оба человека пишут рабочие экраны. Vanilla JS, HTML и CSS, без React/npm. Backend, AI, хранение, формула рейтинга, общая страница, API-адаптер и деплой — Codex. Claude не редактирует файлы людей.

## Разработчик 1 — T-001: экран бизнеса (45–60 минут)

Файлы: **app/static/business.js**, **app/static/business.css**. Ветка: `team/business-ui`.

Сделать:
1. Поле описания и отрасли, кнопка «Уточнить задачу».
2. Показ минимум трёх вопросов от API и полей ответов; «Собрать карточку».
3. Редактируемые поля карточки, источник/цитата рядом с полем, отметка подтверждения человеком.
4. Рейтинг 0–100, уровень, семь составляющих, недостающее, изменение баллов после подтверждения.
5. Кнопка «Опубликовать» и сообщение об успехе. Низкий балл не запрещает публикацию подтверждённой карточки.

Экспорт: `export function mountBusiness(root, api, onPublished)`. DOM только внутри root. CSS ограничить классом `.business-panel`. Баллы не вычислять в JS; читать rating из API. После правки снять отметку подтверждения поля; отправлять изменения и отдельно подтверждения. Тексты/цитаты вставлять через textContent, не innerHTML.

Готово: можно пройти ввод → ответы → редактирование → подтверждение → публикация с переданным mock-адаптером; loading/error состояния видны; повторный клик на время запроса заблокирован. Не реализовывать AI, backend или собственную формулу.

## Разработчик 2 — T-002: каталог и отклики (45–60 минут)

Файлы: **app/static/catalog.js**, **app/static/catalog.css**. Ветка: `team/catalog-ui`.

Сделать:
1. Список опубликованных карточек по рейтингу; фильтры по отрасли и уровню готовности.
2. Просмотр карточки. Низкий балл отмечать «Нужны уточнения», но кнопку отклика оставлять доступной.
3. Выбор учебной команды из списка; форма отклика: идея, план, срок, ссылка на прототип.
4. Раздел бизнеса со списком откликов и кнопками «Выбрать» / «Отклонить» у каждого. Разрешены несколько выбранных команд; нет обязательного победителя.
5. У выбранной команды кнопка «Подтвердить этап», показ отдельных баллов прогресса, без повторного начисления на клиенте.

Экспорт: `export function mountCatalog(root, api)` возвращает `{refresh}`. DOM внутри root; CSS ограничить `.catalog-panel`. Порядок карточек и баллы брать из API. Отклики не ранжировать через AI. Не использовать чувствительные признаки участников.

Готово: видны оба фильтра, отправленный отклик появляется, ручное решение меняет статус; задача с рейтингом ниже 40 доступна; загрузка/ошибки показаны. Не реализовывать backend или автоматический выбор.

## Общий контракт для независимой работы

Методы `api` возвращают Promise. Это согласованный интерфейс будущего адаптера, **не уже работающие HTTP endpoints**. На backend и адаптер его реализует ведущий.

```js
// Экран бизнеса
api.createDraft({text, industry}) // -> {id}
api.clarifyDraft(draftId) // -> {questions:[{id,field,question}], mode:'live'|'mock'}
api.buildCard(draftId, {answers:{questionId:'текст'}}) // -> CardView
api.updateCard(cardId, {changes:{field:'значение'}}) // -> CardView, без подтверждения
api.confirmCard(cardId, {fields:['context','need']}) // -> CardView
api.publishCard(cardId) // -> CardView; вызвать onPublished()

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

## Чтобы не было конфликтов

- Каждый меняет только свои два файла. Общий index.html, schemas.py, rating.py, API, данные и журналы не трогать.
- Пока backend готовится, передавать локальный mock-объект api в своей проверочной странице; не встраивать синтетические ответы в рабочие модули. Проверочную страницу можно оставить вне коммита.
- Через 20 минут показать ведущему первый экран, через 45–60 — рабочий модуль и хеш коммита. Ведущий подключит модули на общей странице и проверит с backend.
- При проблемах с контрактом сразу сообщить ведущему; самостоятельно не менять имена методов и полей.
