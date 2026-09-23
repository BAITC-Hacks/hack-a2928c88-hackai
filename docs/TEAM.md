# Команда: роли и задачи по часам

Принцип: у каждого свой ноутбук, свой аккаунт Codex, свой git-аккаунт, свои файлы. Каждый может объяснить судьям, что сделал сам (п. 6.5, 9.3). Мерж в `main` делает Арман после зелёных тестов.

| Роль | Кто | Файлы | Баллы, за которые отвечает |
|---|---|---|---|
| A — ядро, архитектура, деплой | Арман | `app/agent.py`, `app/schemas.py`, `app/llm.py`, деплой | функциональность 25, техреализация 15 |
| B — данные, правила, проверка | Айдана | `app/rules.py`, `app/readers.py`, `data/`, `eval/`, `tests/` | применимость 15, функциональность 25 |
| C — продукт, README, питч, процесс | Нурсауле | `app/static/index.html`, `README.md`, `docs/` | проблема 15, развитие 20, README 10, Demo Day 20 |

Роли B и C распределены условно — поменять местами, если так удобнее. Если кто-то не тянет свою часть, минимум для каждого: собственные коммиты и понятный ответ судьям «что сделала я».

## Инструкция для Айданы (B) и Нурсауле (C) (5 минут, сделать до старта)

1. Поставить Python 3.12 и Git. Выполнить `git config --global user.name "<Имя Фамилия>"` и `git config --global user.email <почта с платформы>`.
2. Войти в Codex: `codex login`. Проверить: `codex exec "say hi"`.
3. После выдачи репозитория: `git clone <repo>` → `cd <repo>` → `python -m venv .venv` → `.venv\Scripts\activate` → `pip install -r requirements.txt`.
4. Свою ветку: `git checkout -b b-data` (B) или `git checkout -b c-product` (C).
5. Цикл работы:
   - открыть `codex` в папке репозитория;
   - вставить задачу из таблицы ниже (или задачу, которую дал Арман);
   - после выполнения: `python -m pytest -q`, всё зелёное → `git add -A` → `git commit -m "[codex] <что сделано>"` → `git push -u origin <ветка>`;
   - дописать строку в `docs/CODEX_LOG.md` (время, задача, файлы);
   - написать Арману: «запушил <ветка>, <что>».
6. Каждый час в :55 — короткая сверка: что готово, что вырезаем.

## Задачи по часам

Задачи для Codex — копировать как есть; `<...>` заполнить из `docs/IDEA.md`.

### Час 1 — разбор кейса и каркас
- **A:** `docs/CASE.md` → `/kickoff`, схемы и промпты под кейс, первый деплой, URL в README.
- **B:** найти или собрать 3 входа из кейса в `data/samples/`. Codex:
  > Read AGENTS.md and docs/IDEA.md. Add 3–5 labelled cases to eval/cases/*.json for the scenario in docs/IDEA.md, using files in data/samples/. Each case: name, text, expected_rule_ids (may be empty), expected_keywords (1–2 short stems), expected_issues (human-readable list). Do not change app/. Done when `MOCK=1 EVAL_SOFT=1 python -m eval.run_eval` runs.
- **C:** заполнить в `README.md` «Проблему» и «Решение» по `docs/IDEA.md`; подготовить 3 слайда по `docs/PITCH.md`.

### Час 2 — основной сценарий end-to-end
- **A:** агент работает на реальном примере, находки с цитатами.
- **B:** Codex:
  > Read AGENTS.md and docs/IDEA.md. In app/rules.py set REQUIRED_KEYS for the case and add 2 deterministic rules with @rule(...) for: <правило 1>, <правило 2>. Each rule returns Finding with evidence (source, quote, locator). Add unit tests in tests/test_rules.py. Do not touch app/agent.py. Done when `python -m pytest -q` is green.
- **C:** Codex:
  > Read AGENTS.md. In app/static/index.html set the title to "<название>" and the subtitle to "<пользователь + действие>". Add a counter of findings by severity above the list and a "Скачать отчёт" button that downloads /api/runs/{id}/report as .md via fetch+Blob. Keep it a single file, no frameworks. Done when the page works with MOCK=1.

### Час 3 — надёжность и человек в контуре
- **A:** ошибки API, fallback, вход через файл, ревью мержей B и C.
- **B:** Codex:
  > Read AGENTS.md. Add 2 more deterministic rules to app/rules.py for <...> with tests. Then run `MOCK=1 EVAL_SOFT=1 python -m eval.run_eval` and fix eval cases so rule-based expectations pass.
- **C:** каждые 20 минут открывать задеплоенную ссылку, проходить сценарий как пользователь, баги присылать A. Начать `docs/DEMO_SCRIPT.md`.

### Час 4 — измерение
- **A:** live-прогон eval с ключом, настройка промптов по ошибкам.
- **B:** бейзлайн — те же входы в обычный ChatGPT одним запросом, результаты в `eval/baseline.md`; таблица «наше против бейзлайна».
- **C:** раздел «Результаты проверки» в README (только цифры из `eval/report.md` и `eval/baseline.md`), «Ограничения», «Развитие»; запись резервного видео 60 секунд.

### Час 5 — подача (закончить за 30 минут до дедлайна)
- **A:** фриз кода за 45 минут до дедлайна; `python scripts/smoke_url.py <URL>`; тег `submission`.
- **B:** прогнать `prompts/judge.md` (свой Codex или Claude), список дешёвых правок отдать A и C.
- **C:** `docs/SUBMISSION_CHECKLIST.md`, `docs/DISCLOSURE.md`, `docs/CODEX_LOG.md`, форма подачи.

## Почасовой чекпоинт
Отвечает C: в :55 напоминает, A выполняет `scripts/checkpoint.* N "<результат>"` после мержа веток. Коммиты B и C до чекпоинта должны быть запушены.
