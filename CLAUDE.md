@AGENTS.md

## Claude Code specifics

- Slash commands in `.claude/commands/`: `/kickoff`, `/hour`, `/judge`, `/submit`, `/codex`.
- Subagents in `.claude/agents/`: `ai-judge` (scores the repo like the organiser's AI judge), `codex-worker` (delegates a scoped task to Codex CLI via `codex exec`), `gemini-worker` (research via `agy -p`).
- Delegating implementation to Codex through `codex-worker` also produces the evidence required by rule 4 — log it in `docs/CODEX_LOG.md`.
- Respond to the user in Russian; keep code and commits in English.
