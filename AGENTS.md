# AGENTS.md — HackAlem AI, 23.09.2026, Astana

## Active case override — track 07 Education / AI Sana

`docs/CASE.md` is now present and authoritative. Jury scoring is **20/15/25/15/10/10/5**, as recorded in `coord/notes/scoring-07.md`; the generic scoring below is historical. Old `context/*/track-07.md` describes fintech and MUST NOT be used as this case's context.

Current application status: only domain schemas and readiness rating in `app/`, with tests. The FastAPI/UI/LLM/deploy scaffold described below is a prepared external harness, NOT an existing working app in this checkout. Reuse current files; do not assume `app/llm.py` or a deployment exists. Idea awaits captain confirmation before architecture/plan councils and implementation assignments.

Gemini is unavailable (Antigravity unauthenticated; Gemini CLI IneligibleTierError). Do not count its failures as votes or factual research. Claude and Codex responses are in `coord/council/1327-idea/`.

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

- Python 3.12, FastAPI, Pydantic v2. Models via `app/llm.py`:
  - **OpenAI** (primary, required by the hackathon; team has $50 credits): Responses API + Structured Outputs.
  - **NVIDIA build.nvidia.com / NIM** (fallback; $50 tokens): OpenAI-compatible chat completions, JSON schema in prompt + Pydantic validation + one repair retry.
  - Chain on failure: `LLM_PROVIDER` → `FALLBACK_PROVIDER` → mock (`FALLBACK_TO_MOCK=1`). Budget guard: `MAX_CALLS_PER_HOUR`, `MAX_INPUT_CHARS`. Every call logged to `logs/llm_calls.jsonl`; each run reports which provider answered (`trace` step `models`, `mode` live/partial/mock).
  - Config in `.env` (template `.env.example`), loaded by `app/__init__.py`. Never commit keys. Keep OpenAI primary; use NVIDIA for fallback or for a clearly separate step (e.g. embeddings/vision) and disclose it.
- Single-page UI in `app/static/index.html` (no build step). One process, one deploy (Dockerfile / `render.yaml`).
- Pipeline in `app/agent.py`: extract (LLM, with evidence) → deterministic rules (`app/rules.py`) → semantic review (LLM) → human accepts/rejects → report.
- Principle: **the model explains, code computes.** Anything checkable by code (dates, sums, required fields, arithmetic, duplicates) is a rule, not a prompt.
- Every claim shown to the user carries evidence (source + verbatim quote + locator). The `R-QUOTE` rule rejects quotes that do not exist in the input.

## Editor

VS Code with the Codex extension (lead) and the Claude Code extension. Tasks: Ctrl+Shift+P → "Run Task" (`.vscode/tasks.json`): setup, run live/MOCK, tests, eval, key check, council, board, checkpoint, smoke.

## Commands

```bash
# setup (Windows PowerShell): .\scripts\dev.ps1     (Git Bash/Linux): ./scripts/dev.sh
python -m pytest -q                  # must stay green; MOCK=1 is forced in tests
MOCK=1 python -m eval.run_eval       # eval on eval/cases/*.json → eval/report.md
python scripts/check_openai.py       # OpenAI + NVIDIA keys and model availability
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

## Multi-agent protocol (Claude Code + Codex + Gemini in one repo)

Full protocol: `coord/README.md`. Orchestrator: `python scripts/agents.py` (new / run / review / merge / ask / wt / status / council / bg).

**Codex is the lead agent.** Claude Code and Gemini are sub-agents launched by Codex through `scripts/agents.py`. Lead playbook: `prompts/lead.md`.

| Agent | Role | Default ownership |
|---|---|---|
| Codex (**lead**) | plan, task breakdown, core backend, reviews, merges, checkpoints, council synthesis | `app/agent.py`, `app/schemas.py`, `app/llm.py`, rules, tests, deploy |
| Claude Code (sub) | product & quality | README/docs, product-agent prompts, UI copy, eval cases, code reviews, AI-judge self-check |
| Gemini / Antigravity `agy` (sub) | research & skeptic | facts and sources, synthetic data, pitch text, second-opinion reviews |

If you are Codex: you are the lead — follow `prompts/lead.md`. If you are Claude Code or Gemini: you work on the task you were given (task file in `coord/tasks/` or `coord/notes/`); do not merge, do not create tasks, do not launch other agents unless the human asks you directly.

Rules for every agent:
- One task = one id on `coord/TASKS.md` = one branch `agent/<agent>/<id>` = one git worktree in `.worktrees/<agent>-<id>`. Work only in your worktree. Long operations: `python scripts/agents.py bg <command>`.
- Never edit `coord/TASKS.md`, `coord/LOG.md`, `docs/CODEX_LOG.md`, `docs/PROGRESS.md` from a task branch; the orchestrator owns them.
- Finish every task with `coord/tasks/<id>.result.md`: what changed, files, how to verify, what is left.
- Need another agent? Ask through the orchestrator, e.g. `python scripts/agents.py ask --agent gemini "<question>"` or `... review --id <id> --reviewer claude`. Do not call other agents' CLIs directly.
- Changes that affect the main scenario get a cross-review by a different agent before `merge`.
- Irreversible decisions (idea, architecture, plan, demo) go through the council: `python scripts/agents.py council --topic idea|arch|plan|demo` — independent proposals, cross-critique, synthesis, vote. Decisions land in `coord/council/*/DECISION.md` and the topic doc. When you take part in a council, criticise hard and concretely; do not agree out of politeness.
- Merges and hourly checkpoints happen only in the main checkout.

## Definition of done (submission)

`docs/SUBMISSION_CHECKLIST.md` — every box ticked, URL verified with `scripts/smoke_url.py` from a different network, README reviewed by the `ai-judge` pass (`prompts/judge.md`).
