I've checked `api.js` and `business.js` against the backend and am writing up the result.

# Q-150640: follow-up review of `api.js` / `business.js` (read-only)

**Result: no blockers.** Both changes do what they should and break nothing. I did not edit any files, run anything or make any network requests. I read `app/static/api.js`, `app/static/business.js` and `app/main.py`, and only the error-handling parts of `catalog.js`. I did not reread `docs/IDEA.md` or `docs/CASE.md`, because this check only covers code.

## Checks

| What | Result | Where |
|---|---|---|
| A `fetch` network failure becomes a Russian message | OK. `try/catch` around `fetch` throws `Error('Нет связи с сервером…')`. `catch {}` without a variable (ES2019) works in every current browser. | `api.js:11-15` |
| HTTP errors carry `status` | OK. `error.status = response.status` is set before `throw`. | `api.js:28-30` |
| `business.js` reads the error defensively | OK. `e?.status === 409` works, and the regex on `e?.message \|\| ''` is kept as a fallback. It doesn't crash when `e` is not an `Error`. | `business.js:94`, `:96` |
| A 409 is never mistaken for a card conflict | OK. The backend has one other 409 on the business screen, "Сначала запросите уточняющие вопросы" (`main.py:171`). It can only happen before a card exists, and `state.card &&` blocks it. Once a card exists, a 409 on PATCH/confirm/publish comes only from `check_revision` (`main.py:73`). | `business.js:96`; `main.py:69-73`, `:202-205`, `:241` |
| A response lost after the server already saved | OK. The client keeps the old `revision`, so its next action gets a 409, now caught by status, and the reload flow starts. | `api.js:32`; `business.js:96-99` |
| Effect on `catalog.js` (T-002) | Nothing breaks. It uses `error?.message`, so the new Russian text just appears after "Не удалось выполнить действие." | `catalog.js:91`, `:266` |

## Minor notes (not blocking)

1. **The "data kept on screen" wording is too broad.** The network error message is shared, so the catalog shows it too, including when a list fails to load or a proposal is sent (`catalog.js:91`). There, "Введённые данные сохранены на экране" (entered data kept on screen) is not always true (not confirmed for the proposal form; I didn't check the catalog's DOM). A more neutral option: "Нет связи с сервером. Повторите запрос." (No connection to the server. Please try again.) Or the catalog could add its own wording.
2. **One error path still has no `status`.** When the server returns an error with a body that isn't JSON, such as a proxy's HTML 502/504, the code throws an `Error` without `status` (`api.js:19-21`). That doesn't affect the 409 check, because FastAPI always returns JSON. For consistency, `status` could be set there too.
3. **The 428 error is plain text.** If `If-Match` is missing, the 428 has no special handling. In practice the client catches this earlier with its own "Откройте актуальную карточку…" (open the current card first) message at `api.js:7`, which also has no `status`. That's fine as it is.
4. Items 3–4 from Q-150332 are unchanged and weren't part of this change: English `ValueError` text from `rating.py`/`main.py:222` reaches the UI, focus is lost after re-rendering, and there's no `maxlength`.
