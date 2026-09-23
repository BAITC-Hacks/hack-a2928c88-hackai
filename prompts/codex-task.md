# Шаблон задачи для Codex (`codex exec`)

```
Context: read AGENTS.md and docs/IDEA.md first.
Goal: <одна конкретная возможность, видимая пользователю или тестом>
Files you may change: <список>
Do not change: <список>, do not add new frameworks.
Done when: <тест/команда, которая проходит>, `python -m pytest -q` is green.
Constraints: keep evidence (source+quote+locator) on every finding; model explains, code computes.
```

После выполнения — запись в `docs/CODEX_LOG.md`: время, задача, файлы, результат тестов.
