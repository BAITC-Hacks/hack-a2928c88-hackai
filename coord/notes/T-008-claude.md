# T-008: review of the Codex backend (read-only)

I only read files. The repo is unchanged. **I did not run the tests:** both `pytest` calls were blocked by the permission prompt, so I have no pass/fail result.

Scope: `app/main.py`, `app/llm.py`, `app/store.py`, `app/rating.py`, `app/schemas.py`, `tests/test_api.py`, plus how `app/static/api.js` and `catalog.js` call the API.

## Blockers

### B1. HIGH: sending a proposal without a prototype link fails
- **Where:** `app/main.py:45`, where `prototype_url: HttpUrl` is required. The form says the link is optional: `app/static/catalog.js:193` has the label «Ссылка на прототип (необязательно)» and `:197` sets `required=false`.
- **What happens:** the student leaves the link blank, the frontend sends `prototype_url: ""`, and Pydantic rejects it with 422. `api.js:13` then shows «Укажите корректную ссылку…». The "team sends a proposal" step fails whenever there is no link.
- **Reproduce:** `POST /api/cards/T5/proposals` with `X-Demo-Role: team` and `{"team_id":"TM1","idea":"a","plan":"b","timeline":"c","prototype_url":""}` returns 422.
- **Fix, in the backend** (catalog.js belongs to T-002): use `prototype_url: HttpUrl | None = None` in `ProposalInput` and `Proposal` (`schemas.py:99`), and turn `""` into `None` with a before-validator. The case (CASE.md:46) lists the link among the proposal fields, so making it optional is a product decision. Either way, the backend and the UI have to agree.

### B2. HIGH for scoring (the app still works): the deployed app never calls an LLM
- **Where:** `render.yaml:8-9` sets `MOCK=1`, and `llm.py:102` skips every provider when `MOCK=1`.
- **What happens:** every card on the public URL gets `mode:"mock"`. AGENTS.md says OpenAI is required and must be the primary provider, so a judge who opens the URL will not see any AI step. The UI is honest about it (`catalog.js:105` shows «Демо · mock»).
- **Fix:** set `MOCK=0` and `OPENAI_API_KEY` in the Render dashboard, then run `scripts/check_openai.py` and one real `clarify` → `card` call.

### B3. MEDIUM: the live OpenAI call may never work
- **Where:** `llm.py:15-17` and `:120`. The `Extraction` schema has `questions` with `min_length=3, max_length=11`, and `NonEmpty` produces `minLength` on strings.
- **Risk (not confirmed):** OpenAI strict Structured Outputs may reject some of these schema keywords. If it does, every call silently falls back to NVIDIA, then to mock, and the only trace is `warnings`. I did not check this against the OpenAI docs.
- **Check:** one live `/clarify` with `MOCK=0`, then look at `provider` in the response and in `logs/llm_calls.jsonl`.

## Evidence that isn't backed by a real source

### E1. MEDIUM: the fixture cards' "evidence" just repeats their own fields
- **Where:** `main.py:101-102`. For the 5 seed cards, `quote = item[f]` and `source_id = "synthetic-fixture:<id>"`.
- **What happens:** `catalog.js:152-153` shows each field's text again as a blockquote with «Источник: synthetic-fixture:T1». There is no underlying source text, so the evidence proves nothing. The card does have a «Синтетический пример» badge, but a judge may read these quotes as real citations.
- **Fix:** either add source text to the fixture drafts (D1–D5) and quote from it, or return `evidence={}` for fixture cards so no quote is shown.

### E2. LOW: manual edits are shown the same way as sourced quotes
- **Where:** `main.py:228`. A manual edit gets `source_id="manual:…"` and `quote=value`.
- **What happens:** the catalog shows the business user's own text in the same «Источник» format. Nothing is invented, but it is circular.
- **Fix:** show «введено вручную» for the `manual:` prefix instead of a quote.

### E3. LOW: in mock mode, evidence is filled mechanically
- **Where:** `llm.py:54-55`. `need` gets the entire draft text (up to 20k characters) and `title` gets `text[:100]`, which cuts mid-word.
- Both are verbatim, so nothing is invented. But in the demo the title looks broken and `context` is always empty. The live path is checked by `validate_evidence` (substring match plus `source_id`), which is correct. Still, a 1-character quote passes, and nothing checks that a quote fits its field; only the human confirmation step catches that.

## Confirmation state: correct
- Confirmation stores the exact confirmed value, and `is_confirmed` requires `value == approval.value` (`rating.py:35`).
- Changing a field clears its confirmation (`rating.py:86-87`). Saving the same value keeps it.
- `If-Match` and a revision number protect against stale edits (`main.py:69-73`, `:205`).
- Publishing requires a title and every filled field to be confirmed (`:243`).
- The published snapshot stays frozen until the next publish, and `has_unpublished_changes` is computed correctly.
- The score counts only confirmed fields.
- `test_api.py:33-47` covers this.

Small issue:
- **C1. LOW:** `GET /api/cards/{id}` (`main.py:197-200`) has no role check and returns the unpublished live version, including `warnings` like `openai:AuthenticationError`. The public snapshot (`:247`) also includes `warnings` and `provider`. Removing `warnings` from the snapshot is enough.

## Repeated milestone awards: none found
- The milestone key is `(task_id, team_id, "prototype")`. `progress_points` is set to 10, not incremented (`main.py:296-303`), and it runs inside a `BEGIN IMMEDIATE` transaction. Repeating the call or running it in parallel does not add points (`test_api.py:50-70, 101-110`).

Two smaller issues:
- **M1. LOW:** a new proposal from a team that already has the milestone starts at `progress_points=10` while still `pending` (`:270`). Points show up before anyone selects it.
- **M2. LOW:** `decide` can switch a proposal from `selected` to `rejected` after the milestone (`:285`), and the points stay. There is also no `If-Match` there.

## Other
- **S1. LOW:** the default `app = create_app()` (`main.py:316`) creates `data/runtime/sana.sqlite3` when the module is imported, including during tests.
- **S2. INFO:** Render has no disk (`render.yaml:16`), so state resets on every redeploy. The `meta/seeded` flag means fixture changes won't reach an existing database. The README should mention both.
- **S3. LOW:** `api.js:11` calls `response.json()` even on a 500 that returns plain text, so the user sees a `SyntaxError` instead of a readable message.

## Before merging
1. **B1:** decide whether the prototype link is optional and align the backend with it. This is the only thing that breaks the end-to-end flow.
2. **B2/B3:** switch Render to `MOCK=0`, confirm that `provider=openai` appears on at least one card, and record the result in the README.
3. **E1:** stop showing the self-quoting fixture "evidence".
4. Run `python -m pytest -q` (not run in this review).
