# AGENTS.md — HackAlem AI, 23.09.2026, Astana

Single source of truth for every coding agent in this repo (Codex, Claude Code, Gemini/Antigravity, Copilot).
`CLAUDE.md` and `GEMINI.md` only import this file. Keep this file current; update it when the plan changes.

## Mission

Ship, in 5 hours, one **working, deployed, agentic** prototype for the team's track that a judge can open by URL and verify without us present. Scoring (technical round, 100 pts): problem & value 15, **prototype functionality 25**, technical implementation 15, practical applicability 15, growth potential 20, **README & reproducibility 10**. AI judges may pre-score from the README and repo, so the README must stand alone.

Current task and idea: `docs/IDEA.md`. Track context: `docs/TRACK.md` (copied from `context/tracks/`). Official case text, when received, goes verbatim into `docs/CASE.md` and overrides everything else here.

## Hard rules (from the organiser's regulations — violations can disqualify)

1. **All competition work happens in the repository issued by edu.astanahub.com** (6.8). Do not push to other remotes.
2. **Hourly verifiable progress** (6.6, 12.x). Every hour ends with a commit + tag `hour-N` via `scripts/checkpoint.(ps1|sh)` and an entry in `docs/PROGRESS.md`. Never skip an hour, even with a partial result.
3. **Disclose pre-existing material** (6.4): this harness, libraries, models, datasets → `docs/DISCLOSURE.md`. Add every new external dataset/model/library there when you introduce it.
4. **Codex must be used in development.** Log meaningful Codex contributions in `docs/CODEX_LOG.md` (what task, which files). Commits authored mainly by Codex get the prefix `[codex]`.
5. **Deployed and reachable** (8.7–8.9): a live URL plus any credentials in README. The project must stay up during review 24–28.09. `FALLBACK_TO_MOCK=1` keeps the UI alive if the API fails, but the README must say what is mocked.
6. Honesty: no invented metrics, clients, pilots or integrations. Synthetic data, mocks and simulated integrations are labelled as such in UI and README.
7. Never commit secrets. `.env` is git-ignored; keys live only in env vars / hosting dashboard.

## Stack (already scaffolded — extend, don't replace)

- Python 3.12, FastAPI, Pydantic v2, OpenAI Responses API with Structured Outputs (`app/llm.py`).
- Single-page UI in `app/static/index.html` (no build step). One process, one deploy (Dockerfile / `render.yaml`).
- Pipeline in `app/agent.py`: extract (LLM, with evidence) → deterministic rules (`app/rules.py`) → semantic review (LLM) → human accepts/rejects → report.
- Principle: **the model explains, code computes.** Anything checkable by code (dates, sums, required fields, arithmetic, duplicates) is a rule, not a prompt.
- Every claim shown to the user carries evidence (source + verbatim quote + locator). The `R-QUOTE` rule rejects quotes that do not exist in the input.

## Commands

```bash
# setup (Windows PowerShell): .\scripts\dev.ps1     (Git Bash/Linux): ./scripts/dev.sh
python -m pytest -q                  # must stay green; MOCK=1 is forced in tests
MOCK=1 python -m eval.run_eval       # eval on eval/cases/*.json → eval/report.md
python scripts/check_openai.py       # key + model availability
python scripts/smoke_url.py <URL>    # verify the deployed link from outside
# input files: app/readers.py turns pdf/xlsx/csv/docx into text with [page N]/[sheet S row R]/[row R]/[para N] locators
./scripts/checkpoint.sh <hour> "<what is now verifiably done>"
```

## Working agreement for agents

- Before coding, read `docs/IDEA.md`, `docs/CASE.md` (if present) and the last entries of `docs/PROGRESS.md`.
- Work in small vertical slices that keep the app runnable. After each slice: `python -m pytest -q`.
- Prefer editing the existing files over adding frameworks. No React/Node build, no database server, no auth unless the case requires it.
- Scope guard: if a request is not on the critical path in `docs/IDEA.md` (section "MVP scope"), write it into "Later" instead of building it.
- Keep UI text in the user's language of the case (RU or KZ); code, identifiers and commits in English.
- When you add a sample input, put it in `data/samples/*.txt`; when you add a labelled case, put it in `eval/cases/*.json`.
- Do not rewrite `docs/PROGRESS.md` history; only append.
- If unsure between two approaches, pick the one that is faster to demo and easier to verify, and note the trade-off in `docs/IDEA.md` → "Decisions".

## Team

Humans, roles and hourly tasks: `docs/TEAM.md`. Each teammate runs their own Codex on their own laptop and commits from their own account.

## Parallel agents — ownership to avoid conflicts

| Agent | Default ownership |
|---|---|
| Codex | backend features in `app/` (agent, rules, schemas), tests |
| Claude Code | architecture, prompts, README/docs, review of Codex diffs, eval |
| Gemini / others | research, sample data, UI copy, pitch text |

Before touching a file owned by another agent, pull and check `git log -3 -- <file>`. Commit often with clear messages; never force-push `main`.

## Definition of done (submission)

`docs/SUBMISSION_CHECKLIST.md` — every box ticked, URL verified with `scripts/smoke_url.py` from a different network, README reviewed by the `ai-judge` pass (`prompts/judge.md`).
