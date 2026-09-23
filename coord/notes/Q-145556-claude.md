Checking done; writing answer.

# Q-145556: are the narrow fixes correct?

I only read files. Nothing edited, no tests run, no AI calls.

## Verdict on the fixes

| Item | Status | Why |
|---|---|---|
| **E1** seed `evidence={}` | ✅ correct | `main.py:102`. The snapshot is built after this, so `/api/cards` returns `{}`. `catalog.js:151-153` uses optional chaining, so no quote is rendered. The PATCH path (`main.py:226` `pop` on `{}`) is safe. The test `test_api.py:53` asserts `synthetic` and `evidence == {}` for all 5 cards. |
| **S3** non-JSON errors | ✅ correct | `api.js:12-17`. `catch {}` without a binding is ES2019, fine in modern browsers. It handles both a non-OK text/HTML response and a malformed 200. |
| **B3** | ✅ closed | The lead reports a live `provider=openai` on both questions and the card. That's enough to drop it (I didn't see it myself: based on the lead's report). |

Small caveats. None of these block:
- **E1 on an old DB:** `seed()` returns early if `meta/seeded` already exists (`main.py:90`). Any existing local `data/runtime/sana.sqlite3` keeps the old self-quoting evidence until you delete it. On Render, state resets on redeploy (no disk), so production is fine.
- **E1 in business UI:** if a seed card ever opens in `business.js`, every field shows «Источник не найден — заполните вручную» (`business.js:249`). That's accurate but noisy. Whether business can open seed cards: не подтверждено.
- **S3:** `fetch` itself rejecting on network loss still shows a raw `TypeError: Failed to fetch`. Low priority.

## Remaining actual blockers

1. **B1, still open in the code (human T-002).** `main.py:45` still has `prototype_url: HttpUrl` required. `catalog.js:193,197` still says «(необязательно)» and has `required=false`. Until T-002 changes it, a proposal with an empty link gets a 422. The message is readable («Укажите корректную ссылку…», `api.js:19-21`), so the flow doesn't crash. But the label contradicts the behaviour, and a judge who follows the label gets an error. Blocks the "team sends a proposal" step unless a URL is entered.
2. **B2, the deployed app is still mock.** `render.yaml:8-9` still has `MOCK: "1"`. Local live works; the public URL does not.
   - Risk: a `value` hard-coded in the Blueprint may overwrite a dashboard edit on the next Blueprint sync (Render sync behaviour: не подтверждено). Safer: captain sets `MOCK=0` in `render.yaml` too (plus `OPENAI_API_KEY` as `sync: false`), or doesn't re-sync the Blueprint.
   - After the switch: `GET /health` should show `configured_mode: "live-with-fallback"`, and one card on the public URL should show `provider=openai`. Then README should say live instead of mock.

Nothing else blocks. Still open from T-008, all LOW and none break the main scenario:
- **C1:** `warnings` leak into the public snapshot.
- **M1:** a new pending proposal can start with 10 points.
- **M2:** `decide` switches `selected` → `rejected` and keeps the points.
- **S2:** README should say state resets on redeploy.

## Before the checkpoint
- `python -m pytest -q` still needs to run. I didn't run it here, so no result.
- Check B1 again after T-002's commit: blank link → either an explicit "required" label or a successful 201.
