#!/usr/bin/env python3
"""Оркестратор для совместной работы Claude Code, Codex и Gemini (Antigravity) в одном репозитории.

Каждый агент получает отдельный git worktree и ветку, поэтому агенты не мешают друг другу.
Общая доска задач (coord/TASKS.md) и журнал (coord/LOG.md) лежат только в основной папке
репозитория и в ветки не коммитятся: так не возникает конфликтов слияния.

Команды (запускать из любой папки репозитория, Windows / Linux / macOS):
  python scripts/agents.py new    --title "Правило: сумма = кол-во × цена" [--owner codex]
  python scripts/agents.py run    --agent codex  --id T-002 [--task "доп. указания"] [--timeout 900]
  python scripts/agents.py run    --agent gemini --id T-003 --text      # только текстовый ответ, без правки кода
  python scripts/agents.py ask    --agent gemini "вопрос"                 # быстрый вопрос, ответ в coord/notes/
  python scripts/agents.py review --id T-002 --reviewer claude             # ревью ветки другим агентом
  python scripts/agents.py merge  --id T-002                               # слить ветку, прогнать тесты, убрать worktree
  python scripts/agents.py wt     --agent codex --id T-004                 # worktree для ручной интерактивной сессии
  python scripts/agents.py status
  python scripts/agents.py council --topic idea|arch|plan|demo [доп. вопрос]   # обсуждение → прожарка → консенсус
  python scripts/agents.py bg council --topic idea                           # любую команду — в фоне, лог в coord/notes/

Команды запуска агентов настраиваются в coord/agents.json (флаги CLI меняются между версиями).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

AGENTS = ("claude", "codex", "gemini")
DEFAULT_CMDS = {
    # {prompt} заменяется короткой строкой-указателем на файл задачи (без переносов и кавычек)
    "claude": ["claude", "-p", "{prompt}", "--permission-mode", "acceptEdits"],
    "codex": ["codex", "exec", "--skip-git-repo-check", "--full-auto", "{prompt}"],
    "gemini": ["agy", "-p", "{prompt}"],
}
# Режим «только ответ, без правки файлов»: для обсуждений, ревью, вопросов
DEFAULT_TEXT_CMDS = {
    "claude": ["claude", "-p", "{prompt}"],
    "codex": ["codex", "exec", "--skip-git-repo-check", "--sandbox", "read-only", "{prompt}"],
    "gemini": ["agy", "-p", "{prompt}"],
}
TEXT_ONLY_DEFAULT = {"gemini"}  # по умолчанию Gemini отвечает текстом; поменять в coord/agents.json
PROTECTED = ["coord/TASKS.md", "coord/LOG.md", "docs/CODEX_LOG.md", "docs/PROGRESS.md"]
STATUSES = ("todo", "doing", "review", "done", "blocked")


# ---------- git / пути ----------

def sh(args: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, check=check, text=True, capture_output=True,
                          encoding="utf-8", errors="replace")


def main_root() -> Path:
    common = sh(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"]).stdout.strip()
    return Path(common).parent


def wt_path(root: Path, agent: str, tid: str) -> Path:
    # внутри репозитория (папка в .gitignore): так worktree остаётся в песочнице Codex-ведущего
    return root / ".worktrees" / f"{agent}-{tid}"


def branch_name(agent: str, tid: str) -> str:
    return f"agent/{agent}/{tid}"


def now() -> str:
    return dt.datetime.now().strftime("%H:%M")


# ---------- конфигурация ----------

def load_cfg(root: Path) -> dict:
    p = root / "coord" / "agents.json"
    cfg = {"commands": dict(DEFAULT_CMDS), "text_commands": dict(DEFAULT_TEXT_CMDS),
           "text_only": sorted(TEXT_ONLY_DEFAULT)}
    if p.exists():
        user = json.loads(p.read_text(encoding="utf-8"))
        cfg["commands"].update(user.get("commands", {}))
        cfg["text_commands"].update(user.get("text_commands", {}))
        cfg["text_only"] = user.get("text_only", cfg["text_only"])
    return cfg


def resolve_cmd(cfg: dict, agent: str, prompt: str, text: bool = False) -> list[str]:
    tpl = cfg["text_commands" if text else "commands"][agent]
    exe = shutil.which(tpl[0])
    if not exe:
        sys.exit(f"Не найден CLI '{tpl[0]}' для агента {agent}. Установите его или поправьте coord/agents.json")
    return [exe] + [a.replace("{prompt}", prompt) for a in tpl[1:]]


# ---------- доска задач ----------

HEADER = "| id | title | owner | status | branch | updated |\n|---|---|---|---|---|---|\n"


def board_path(root: Path) -> Path:
    return root / "coord" / "TASKS.md"


def read_board(root: Path) -> list[dict]:
    p = board_path(root)
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*(T-\d+)\s*\|(.*)\|\s*$", line)
        if m:
            cells = [c.strip() for c in m.group(2).split("|")]
            cells += [""] * (5 - len(cells))
            rows.append(dict(id=m.group(1), title=cells[0], owner=cells[1], status=cells[2],
                             branch=cells[3], updated=cells[4]))
    return rows


def write_board(root: Path, rows: list[dict]) -> None:
    p = board_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    head = "# Доска задач\n\nОбновляется только скриптом `scripts/agents.py` или ведущим (Арман / Claude-lead) в основной папке. В ветках не редактировать.\n\n"
    body = "".join(f"| {r['id']} | {r['title'].replace('|', '/')} | {r['owner']} | {r['status']} | {r['branch']} | {r['updated']} |\n" for r in rows)
    p.write_text(head + HEADER + body, encoding="utf-8")


class BoardLock:
    """Простая межпроцессная блокировка доски: несколько `run` в разных терминалах не затрут друг друга."""
    def __init__(self, root: Path):
        self.p = root / "coord" / ".board.lock"

    def __enter__(self):
        import time
        self.p.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(200):
            try:
                self.fd = os.open(self.p, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                return self
            except FileExistsError:
                if time.time() - self.p.stat().st_mtime > 30:  # зависшая блокировка
                    self.p.unlink(missing_ok=True)
                time.sleep(0.05)
        raise TimeoutError("coord/.board.lock занят")

    def __exit__(self, *exc):
        os.close(self.fd)
        self.p.unlink(missing_ok=True)


def upsert(root: Path, tid: str, **fields) -> dict:
    with BoardLock(root):
        return _upsert(root, tid, **fields)


def _upsert(root: Path, tid: str, **fields) -> dict:
    rows = read_board(root)
    for r in rows:
        if r["id"] == tid:
            r.update({k: v for k, v in fields.items() if v is not None})
            r["updated"] = now()
            write_board(root, rows)
            return r
    r = dict(id=tid, title="", owner="", status="todo", branch="", updated=now())
    r.update({k: v for k, v in fields.items() if v is not None})
    rows.append(r)
    write_board(root, rows)
    return r


def get_task(root: Path, tid: str) -> dict:
    for r in read_board(root):
        if r["id"] == tid:
            return r
    sys.exit(f"Задача {tid} не найдена в coord/TASKS.md (создайте: agents.py new --title ...)")


def log(root: Path, msg: str) -> None:
    p = root / "coord" / "LOG.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text("# Журнал агентов\n\n", encoding="utf-8")
    with p.open("a", encoding="utf-8") as f:
        f.write(f"- {now()} {msg}\n")


def codex_log(root: Path, tid: str, title: str, files: str, result: str) -> None:
    p = root / "docs" / "CODEX_LOG.md"
    if p.exists():
        with p.open("a", encoding="utf-8") as f:
            f.write(f"| {now()} | {tid}: {title} | {files} | {result} |\n")


# ---------- запуск агента ----------

PROMPT_TMPL = """# Задача {tid} для агента {agent}

{title}

{extra}

## Контекст и правила
- Ты работаешь в команде агентов (Claude Code, Codex, Gemini) над одним репозиторием. Сначала прочитай `AGENTS.md` и `coord/README.md`.
- Рабочая папка: `{workdir}`. Ветка: `{branch}`. Работай только здесь.
- НЕ редактируй: {protected}. Их ведёт оркестратор.
- Делай минимальное изменение, которое решает задачу. Не добавляй фреймворки.
- В конце: `python -m pytest -q` должен быть зелёным.
- Итог напиши в файл `coord/tasks/{tid}.result.md`: что сделано, какие файлы изменены, как проверить, что осталось. Коммит делать не нужно — его сделает оркестратор.
"""

TEXT_TMPL = """# Задача {tid} для агента {agent} (текстовый ответ)

{title}

{extra}

Прочитай `AGENTS.md`, `docs/IDEA.md` и `docs/CASE.md`, если они есть. Файлы репозитория не меняй.
Ответ дай в stdout в формате Markdown. Факты без источника помечай «не подтверждено».
"""


def stream_run(cmd: list[str], cwd: Path, out_file: Path, timeout: int | None, echo: bool = True) -> int:
    out_file.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, MOCK=os.environ.get("MOCK", "1"))
    with out_file.open("w", encoding="utf-8") as out:
        try:
            p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace", env=env)
            assert p.stdout is not None
            for line in p.stdout:
                if echo:
                    sys.stdout.write(line)
                out.write(line)
            return p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            p.kill()
            out.write("\n[TIMEOUT]\n")
            return 124


def run_tests(cwd: Path) -> tuple[bool, str]:
    r = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=cwd, text=True, capture_output=True,
                       env=dict(os.environ, MOCK="1"), encoding="utf-8", errors="replace")
    tail = (r.stdout + r.stderr).strip().splitlines()[-1:] or [""]
    return r.returncode == 0, tail[0]


def ensure_worktree(root: Path, agent: str, tid: str) -> tuple[Path, str]:
    path, br = wt_path(root, agent, tid), branch_name(agent, tid)
    if path.exists():
        return path, br
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = sh(["git", "rev-parse", "--verify", "--quiet", br], cwd=root, check=False).returncode == 0
    args = ["git", "worktree", "add", str(path), br] if exists else ["git", "worktree", "add", "-b", br, str(path), "HEAD"]
    sh(args, cwd=root)
    return path, br


def cmd_run(a) -> None:
    root = main_root()
    cfg = load_cfg(root)
    task = get_task(root, a.id)
    text_mode = a.text or (a.agent in cfg["text_only"] and not a.edit)
    extra = a.task or ""
    if text_mode:
        workdir, br = root, ""
        pfile = root / "coord" / "notes" / f"{a.id}-{a.agent}.prompt.md"
        pfile.parent.mkdir(parents=True, exist_ok=True)
        pfile.write_text(TEXT_TMPL.format(tid=a.id, agent=a.agent, title=task["title"], extra=extra), encoding="utf-8")
        rel = pfile.relative_to(root).as_posix()
        upsert(root, a.id, owner=a.agent, status="doing")
        log(root, f"{a.agent} ← {a.id} (текст): {task['title']}")
        out = root / "coord" / "notes" / f"{a.id}-{a.agent}.md"
        rc = stream_run(resolve_cmd(cfg, a.agent, f"Read the file {rel} and answer it.", text=True), workdir, out, a.timeout)
        upsert(root, a.id, status="review" if rc == 0 else "blocked")
        log(root, f"{a.agent} → {a.id}: ответ в {out.relative_to(root).as_posix()} (rc={rc})")
        print(f"\nОтвет: {out}")
        return

    workdir, br = ensure_worktree(root, a.agent, a.id)
    pfile = workdir / "coord" / "tasks" / f"{a.id}.prompt.md"
    pfile.parent.mkdir(parents=True, exist_ok=True)
    pfile.write_text(PROMPT_TMPL.format(tid=a.id, agent=a.agent, title=task["title"], extra=extra, workdir=workdir,
                                        branch=br, protected=", ".join(f"`{p}`" for p in PROTECTED)), encoding="utf-8")
    upsert(root, a.id, owner=a.agent, status="doing", branch=br)
    log(root, f"{a.agent} ← {a.id}: {task['title']} [{br}]")
    out = workdir / "coord" / "tasks" / f"{a.id}.{a.agent}.log"
    rc = stream_run(resolve_cmd(cfg, a.agent, f"Read coord/tasks/{a.id}.prompt.md and complete the task described there."),
                    workdir, out, a.timeout)

    # защищённые файлы в ветке откатываем, чтобы не было конфликтов
    for p in PROTECTED:
        sh(["git", "checkout", "HEAD", "--", p], cwd=workdir, check=False)
    ok, tail = run_tests(workdir)
    sh(["git", "add", "-A"], cwd=workdir)
    changed = sh(["git", "diff", "--cached", "--name-only"], cwd=workdir).stdout.split()
    code_changed = [f for f in changed if not f.startswith("coord/tasks/")]
    if changed:
        sh(["git", "-c", "user.useConfigOnly=true", "commit", "-m", f"[{a.agent}] {a.id}: {task['title'][:60]}"],
           cwd=workdir, check=False)
    status = "review" if (rc == 0 and ok) else "blocked"
    upsert(root, a.id, status=status)
    log(root, f"{a.agent} → {a.id}: rc={rc}, tests={'OK' if ok else 'FAIL'} ({tail}), файлов={len(code_changed)}")
    if a.agent == "codex":
        codex_log(root, a.id, task["title"], ", ".join(code_changed[:6]) or "—", f"tests {'OK' if ok else 'FAIL'}")
    print(f"\n== {a.id}: {status}. Ветка {br}, worktree {workdir}")
    print(f"   Тесты: {tail}. Изменено: {', '.join(code_changed) or 'ничего'}")
    print(f"   Дальше: agents.py review --id {a.id} --reviewer <agent>  или  agents.py merge --id {a.id}")


def find_branch(root: Path, tid: str) -> tuple[str, str]:
    t = get_task(root, tid)
    if t["branch"]:
        return t["branch"], t["branch"].split("/")[1]
    for ag in AGENTS:
        br = branch_name(ag, tid)
        if sh(["git", "rev-parse", "--verify", "--quiet", br], cwd=root, check=False).returncode == 0:
            return br, ag
    sys.exit(f"Ветка для {tid} не найдена")


def cmd_review(a) -> None:
    root = main_root()
    cfg = load_cfg(root)
    br, author = find_branch(root, a.id)
    base = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root).stdout.strip()
    diff = sh(["git", "diff", f"{base}...{br}"], cwd=root).stdout
    if not diff.strip():
        sys.exit("Пустой diff — нечего ревьюить")
    rdir = root / "coord" / "reviews"
    rdir.mkdir(parents=True, exist_ok=True)
    pfile = rdir / f"{a.id}-{a.reviewer}.prompt.md"
    pfile.write_text(
        f"# Ревью {a.id} (автор: {author}, ревьюер: {a.reviewer})\n\n"
        f"Задача: {get_task(root, a.id)['title']}\n\n"
        "Прочитай AGENTS.md. Проверь diff ниже: баги, нарушение правил AGENTS.md (доказательства у находок, "
        "код считает, модель объясняет), лишний объём, отсутствие тестов. Файлы не меняй.\n"
        "Ответ: вердикт APPROVE или CHANGES, затем список конкретных замечаний (файл:строка → что исправить).\n\n"
        f"```diff\n{diff[:60000]}\n```\n", encoding="utf-8")
    out = rdir / f"{a.id}-{a.reviewer}.md"
    rel = pfile.relative_to(root).as_posix()
    log(root, f"{a.reviewer} ревьюит {a.id} ({author})")
    rc = stream_run(resolve_cmd(cfg, a.reviewer, f"Read the file {rel} and write the review it asks for.", text=True), root, out, a.timeout)
    verdict = "APPROVE" if "APPROVE" in out.read_text(encoding="utf-8", errors="replace") else "CHANGES?"
    log(root, f"{a.reviewer} → ревью {a.id}: {verdict} ({out.relative_to(root).as_posix()}, rc={rc})")
    print(f"\nРевью: {out} — {verdict}")


def cmd_merge(a) -> None:
    root = main_root()
    br, agent = find_branch(root, a.id)
    if sh(["git", "status", "--porcelain", "--untracked-files=no"], cwd=root).stdout.strip():
        # незакоммиченные правки в основной папке: сохраняем доску/журнал отдельным коммитом
        sh(["git", "add", "-A"], cwd=root)
        sh(["git", "commit", "-m", "chore(coord): board and log update"], cwd=root, check=False)
    r = sh(["git", "merge", "--no-ff", br, "-m", f"merge {br}"], cwd=root, check=False)
    if r.returncode != 0:
        upsert(root, a.id, status="blocked")
        log(root, f"merge {a.id}: КОНФЛИКТ — решить вручную")
        sys.exit("Конфликт слияния. Решите вручную (git status), затем git commit. Или: git merge --abort\n" + r.stdout + r.stderr)
    ok, tail = run_tests(root)
    if not ok and not a.force:
        sh(["git", "reset", "--hard", "HEAD~1"], cwd=root)
        upsert(root, a.id, status="blocked")
        log(root, f"merge {a.id}: тесты упали после слияния ({tail}) — слияние отменено")
        sys.exit(f"Тесты упали после слияния: {tail}. Слияние отменено. --force чтобы оставить")
    path = wt_path(root, agent, a.id)
    if path.exists():
        sh(["git", "worktree", "remove", "--force", str(path)], cwd=root, check=False)
    sh(["git", "branch", "-d", br], cwd=root, check=False)
    upsert(root, a.id, status="done", branch="")
    log(root, f"merge {a.id} ({agent}) в {sh(['git','rev-parse','--abbrev-ref','HEAD'], cwd=root).stdout.strip()}: tests {tail}")
    print(f"Слито: {br}. Тесты: {tail}")


def cmd_new(a) -> None:
    root = main_root()
    with BoardLock(root):
        rows = read_board(root)
        n = max([int(r["id"][2:]) for r in rows] + [0]) + 1
        tid = f"T-{n:03d}"
        _upsert(root, tid, title=a.title, owner=a.owner or "", status="todo")
    log(root, f"новая задача {tid}: {a.title}")
    print(tid)


def cmd_ask(a) -> None:
    root = main_root()
    tid = "Q-" + dt.datetime.now().strftime("%H%M%S")
    cfg = load_cfg(root)
    notes = root / "coord" / "notes"
    notes.mkdir(parents=True, exist_ok=True)
    pfile = notes / f"{tid}-{a.agent}.prompt.md"
    pfile.write_text(TEXT_TMPL.format(tid=tid, agent=a.agent, title=" ".join(a.question), extra=""), encoding="utf-8")
    out = notes / f"{tid}-{a.agent}.md"
    stream_run(resolve_cmd(cfg, a.agent, f"Read the file {pfile.relative_to(root).as_posix()} and answer it.", text=True), root, out, a.timeout)
    log(root, f"вопрос {a.agent}: {' '.join(a.question)[:80]} → {out.relative_to(root).as_posix()}")


def cmd_wt(a) -> None:
    root = main_root()
    get_task(root, a.id)
    path, br = ensure_worktree(root, a.agent, a.id)
    upsert(root, a.id, owner=a.agent, status="doing", branch=br)
    log(root, f"{a.agent} (интерактивно) ← {a.id} [{br}]")
    launch = {"claude": "claude", "codex": "codex", "gemini": "agy"}[a.agent]
    print(f"Worktree: {path}\nВетка: {br}\nЗапуск: cd \"{path}\" ; {launch}\n"
          f"Когда готово: закоммитить в ветке, затем python scripts/agents.py merge --id {a.id}")


def cmd_status(a) -> None:
    root = main_root()
    p = board_path(root)
    print(p.read_text(encoding="utf-8") if p.exists() else "Доска пуста: agents.py new --title ...")
    print("\nWorktrees:\n" + sh(["git", "worktree", "list"], cwd=root).stdout)
    lp = root / "coord" / "LOG.md"
    if lp.exists():
        print("Последние события:\n" + "\n".join(lp.read_text(encoding="utf-8").splitlines()[-8:]))
    cfg = load_cfg(root)
    print("\nCLI агентов: " + ", ".join(f"{k}={'OK' if shutil.which(v[0]) else 'нет ' + v[0]}" for k, v in cfg["commands"].items()))


# ---------- совет агентов: обсуждение → прожарка → консенсус ----------

COUNCIL_ROLES = {
    "codex": "Ведущий: главный инженер и архитектор команды. Смотришь на реализуемость за оставшееся время, риски интеграций, что можно проверить тестом, объём кода; в конце ты сводишь общее решение.",
    "claude": "Продукт и качество. Смотришь на ценность для пользователя, цельность сценария, соответствие кейсу и критериям, качество промптов агента и README.",
    "gemini": "Строгий судья хакатона и скептик. Смотришь глазами жюри и AI-судьи: чем это лучше обычного ChatGPT, откуда данные, честность метрик, вау-эффект демо.",
}

COUNCIL_TOPICS = {
    "idea": ("Выбор идеи решения для кейса трека",
             "Предложи ОДНУ идею: пользователь, боль, вход → выход, шаги агента, что проверяет код, что подтверждает человек, "
             "данные на сегодня, метрика и бейзлайн, чем лучше обычного запроса к модели, демо за 60 секунд, путь к пилоту. "
             "Оцени себя по IDEA_SCORING (templates или docs)."),
    "arch": ("Архитектура прототипа",
             "Предложи архитектуру поверх существующего каркаса (app/agent.py, app/rules.py, app/llm.py, app/readers.py): "
             "схемы данных, шаги конвейера, какие правила кодом, какие вызовы модели и с какими схемами, UI, данные, eval, деплой. "
             "Что НЕ делаем. Главные риски и как их снять за первый час."),
    "plan": ("План работ по часам и разбивка на задачи агентам",
             "Предложи план по часам до дедлайна и список задач. Каждая задача — строкой формата "
             "`TASK | <claude|codex|gemini> | <заголовок с критерием готовности>`. Задачи разных агентов не трогают одни файлы."),
    "demo": ("Демо и питч",
             "Предложи сценарий демо на 60–90 секунд, 3 слайда, ответы на 5 самых неудобных вопросов жюри, что показать в README."),
}

ANSWER_RULE = ("Формат ответа: весь итоговый ответ помести между строками `<<<ANSWER` и `ANSWER>>>`. "
               "Файлы репозитория не меняй. Пиши по-русски, конкретно, без воды.")


def extract_answer(raw: str) -> str:
    # Only standalone delimiter lines count. Agents may mention the markers
    # again in prose after their answer, which must not replace the answer.
    matches = list(re.finditer(r"^<<<ANSWER\s*\r?\n(.*?)^ANSWER>>>\s*$", raw, re.M | re.S))
    if matches:
        return matches[-1].group(1).strip()
    return raw.strip()[-12000:]


def council_context(root: Path) -> str:
    parts = []
    for rel in ("docs/CASE.md", "docs/TRACK.md", "docs/IDEA.md", "docs/ARCHITECTURE.md", "context/RULES.md"):
        p = root / rel
        if p.exists():
            parts.append(f"- `{rel}`")
    return "Прочитай: `AGENTS.md`, " + ", ".join(parts) + ". Кейс организаторов (`docs/CASE.md`) важнее всего остального."


def ask_many(root: Path, cfg: dict, agents: list[str], files: dict[str, Path], outs: dict[str, Path],
             timeout: int | None) -> dict[str, str]:
    from concurrent.futures import ThreadPoolExecutor

    def one(ag: str) -> tuple[str, str]:
        rel = files[ag].relative_to(root).as_posix()
        rc = stream_run(resolve_cmd(cfg, ag, f"Read the file {rel} and do exactly what it asks.", text=True),
                        root, outs[ag], timeout, echo=False)
        raw = outs[ag].read_text(encoding="utf-8", errors="replace")
        ans = extract_answer(raw)
        print(f"   · {ag}: {'ok' if rc == 0 else f'rc={rc}'} ({len(ans)} симв.)")
        return ag, ans if rc == 0 else f"[{ag} не ответил, rc={rc}]\n{ans[-2000:]}"

    with ThreadPoolExecutor(max_workers=len(agents)) as ex:
        return dict(ex.map(one, agents))


def cmd_council(a) -> None:
    root = main_root()
    cfg = load_cfg(root)
    agents = [x for x in (a.agents or "codex,claude,gemini").split(",") if x]
    missing = [x for x in agents if not shutil.which(cfg["text_commands"][x][0])]
    if missing:
        print(f"Нет CLI для: {', '.join(missing)} — они пропущены")
        agents = [x for x in agents if x not in missing]
    if len(agents) < 2:
        sys.exit("Для совета нужно минимум два агента с установленным CLI")
    title, focus = COUNCIL_TOPICS.get(a.topic, (a.topic, "Предложи решение."))
    question = " ".join(a.question or [])
    stamp = dt.datetime.now().strftime("%H%M")
    cdir = root / "coord" / "council" / f"{stamp}-{re.sub(r'[^a-zA-Z0-9_-]', '', a.topic)[:20] or 'topic'}"
    cdir.mkdir(parents=True, exist_ok=True)
    ctx = council_context(root)
    synth = a.synth if a.synth in agents else agents[0]
    log(root, f"совет «{title}» начат: {', '.join(agents)}, раундов критики {a.rounds}, итог — {synth} [{cdir.relative_to(root).as_posix()}]")
    print(f"== Совет: {title}\n   участники: {', '.join(agents)}; папка {cdir}")

    def write(name: str, text: str) -> Path:
        p = cdir / name
        p.write_text(text, encoding="utf-8")
        return p

    # Раунд 0: независимые предложения
    print("-- раунд 0: независимые предложения")
    files = {ag: write(f"r0-{ag}.prompt.md",
                       f"# Совет агентов: {title}\n\nТвоя роль: {COUNCIL_ROLES.get(ag, '')}\n\n{ctx}\n\n"
                       f"{('Вопрос: ' + question) if question else ''}\n\nЗадание: {focus}\n"
                       "Работай независимо: ты ещё не видишь предложения других.\n\n" + ANSWER_RULE) for ag in agents}
    current = ask_many(root, cfg, agents, files, {ag: cdir / f"r0-{ag}.log" for ag in agents}, a.timeout)
    for ag, t in current.items():
        write(f"r0-{ag}.md", t)

    # Раунды критики: каждый прожаривает остальных и улучшает своё
    for r in range(1, a.rounds + 1):
        print(f"-- раунд {r}: прожарка и доработка")
        files = {}
        for ag in agents:
            others = "\n\n".join(f"## Предложение {o}\n\n{current[o]}" for o in agents if o != ag)
            files[ag] = write(f"r{r}-{ag}.prompt.md",
                              f"# Совет агентов: {title} — раунд критики {r}\n\nТвоя роль: {COUNCIL_ROLES.get(ag, '')}\n\n{ctx}\n\n"
                              f"## Твоё текущее предложение\n\n{current[ag]}\n\n{others}\n\n"
                              "Задание:\n1. Жёстко прожарь КАЖДОЕ чужое предложение: 3–5 самых серьёзных слабостей "
                              "(реализуемость за время хакатона, ценность, данные, проверяемость, отличие от обычного ChatGPT, риск дисквалификации), "
                              "и что в нём сильного стоит забрать.\n2. Честно признай слабости своего.\n"
                              "3. Выдай улучшенное предложение (можно объединить лучшее из всех). Не соглашайся из вежливости.\n"
                              "Структура: `## Критика`, `## Что забираю`, `## Обновлённое предложение`.\n\n" + ANSWER_RULE)
        current = ask_many(root, cfg, agents, files, {ag: cdir / f"r{r}-{ag}.log" for ag in agents}, a.timeout)
        for ag, t in current.items():
            write(f"r{r}-{ag}.md", t)

    # Синтез и голосование
    decision = ""
    for attempt in range(1 + a.revisions):
        print(f"-- синтез ({synth})" + (f", доработка {attempt}" if attempt else ""))
        all_props = "\n\n".join(f"## {ag}\n\n{current[ag]}" for ag in agents)
        objections = "" if attempt == 0 else f"\n\n## Возражения к прошлой версии решения\n\n{objections_text}\n\n## Прошлая версия\n\n{decision}"
        sp = write(f"synth{attempt}.prompt.md",
                   f"# Совет агентов: {title} — итоговое решение\n\n{ctx}\n\n{all_props}{objections}\n\n"
                   "Задание: сформулируй ОДНО общее решение, с которым смогут согласиться все. Структура:\n"
                   "## Решение\n(конкретно, чтобы по нему можно было работать)\n## Почему так\n(3–5 пунктов, с опорой на критику)\n"
                   "## Что отвергли и почему\n## Риски и как снимаем\n## Разногласия\n(что осталось спорным, чья позиция)\n"
                   + ("## Задачи\nстроки `TASK | <claude|codex|gemini> | <заголовок с критерием готовности>`\n" if a.topic == "plan" else "")
                   + "\n" + ANSWER_RULE)
        res = ask_many(root, cfg, [synth], {synth: sp}, {synth: cdir / f"synth{attempt}.log"}, a.timeout)
        decision = res[synth]
        write(f"decision{attempt}.md", decision)

        print("-- голосование")
        vfiles = {ag: write(f"vote{attempt}-{ag}.prompt.md",
                            f"# Голосование: {title}\n\nТвоя роль: {COUNCIL_ROLES.get(ag, '')}\n\n## Итоговое решение\n\n{decision}\n\n"
                            "Ответь первой строкой ровно `AGREE` или `DISAGREE`. Затем до 5 строк: если DISAGREE — что именно "
                            "надо изменить, чтобы ты согласился; если AGREE — одна главная поправка (необязательная).\n\n" + ANSWER_RULE)
                  for ag in agents}
        votes = ask_many(root, cfg, agents, vfiles, {ag: cdir / f"vote{attempt}-{ag}.log" for ag in agents}, a.timeout)
        tally = {ag: (v.strip().splitlines()[0].upper() if v.strip().splitlines()
                      and v.strip().splitlines()[0].upper() in {"AGREE", "DISAGREE"}
                      else "UNAVAILABLE") for ag, v in votes.items()}
        print("   голоса: " + ", ".join(f"{k}={v}" for k, v in tally.items()))
        objections_text = "\n\n".join(f"### {ag}: {tally[ag]}\n{votes[ag]}" for ag in agents)
        if all(v == "AGREE" for v in tally.values()):
            break

    consensus = all(v == "AGREE" for v in tally.values())
    final = (f"# Решение совета: {title}\n\nВремя: {dt.datetime.now():%d.%m %H:%M}. Участники: {', '.join(agents)}. "
             f"Раундов критики: {a.rounds}. Консенсус: {'да' if consensus else 'нет — см. голоса'}.\n\n{decision}\n\n"
             f"## Голоса\n\n{objections_text}\n\n## Материалы\n\nПредложения и критика: `{cdir.relative_to(root).as_posix()}/`\n")
    dfile = write("DECISION.md", final)

    # Запись в документы проекта
    target = {"idea": "docs/IDEA.md", "arch": "docs/ARCHITECTURE.md", "plan": "docs/IDEA.md", "demo": "docs/PITCH.md"}.get(a.topic)
    if target and not a.no_apply:
        tp = root / target
        tp.parent.mkdir(parents=True, exist_ok=True)
        with tp.open("a", encoding="utf-8") as f:
            f.write(f"\n\n---\n\n<!-- council {cdir.name} -->\n{final}\n")
    added = []
    if a.topic == "plan" and not a.no_apply:
        for line in decision.splitlines():
            m = re.match(r"^\s*[-*]?\s*`?TASK\s*\|\s*(claude|codex|gemini)\s*\|\s*(.+?)`?\s*$", line)
            if m:
                with BoardLock(root):
                    rows = read_board(root)
                    tid = f"T-{max([int(r['id'][2:]) for r in rows] + [0]) + 1:03d}"
                    _upsert(root, tid, title=m.group(2).strip(), owner=m.group(1), status="todo")
                added.append(f"{tid} ({m.group(1)})")
    log(root, f"совет «{title}» завершён: консенсус={'да' if consensus else 'нет'}; решение {dfile.relative_to(root).as_posix()}"
        + (f"; в {target}" if target and not a.no_apply else "") + (f"; задачи {', '.join(added)}" if added else ""))
    print(f"\n== Итог: {dfile}\n   Консенсус: {'да' if consensus else 'НЕТ — решает человек'}"
          + (f"\n   Записано в {target}" if target and not a.no_apply else "")
          + (f"\n   Задачи на доске: {', '.join(added)}" if added else ""))


def cmd_bg(rest: list[str]) -> None:
    """Запустить команду agents.py в фоне (для ведущего агента: долгие советы и задачи не блокируют его)."""
    root = main_root()
    notes = root / "coord" / "notes"
    notes.mkdir(parents=True, exist_ok=True)
    out = notes / f"bg-{dt.datetime.now():%H%M%S%f}-{(rest[0] if rest else 'x')}.log"
    kw: dict = {}
    if os.name == "nt":
        kw["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    f = out.open("w", encoding="utf-8")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), *rest], cwd=root, stdout=f,
                            stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=env, **kw)
    log(root, f"фон: {' '.join(rest)[:80]} (pid {proc.pid}) → {out.relative_to(root).as_posix()}")
    print(f"Запущено в фоне, pid {proc.pid}. Лог: {out}\nПрогресс: python scripts/agents.py status  или  Get-Content -Wait {out}")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "bg":
        return cmd_bg(sys.argv[2:])
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("new"); p.add_argument("--title", required=True); p.add_argument("--owner")
    p = sub.add_parser("run"); p.add_argument("--agent", choices=AGENTS, required=True); p.add_argument("--id", required=True)
    p.add_argument("--task"); p.add_argument("--text", action="store_true", help="только текстовый ответ")
    p.add_argument("--edit", action="store_true", help="разрешить правку кода агенту из text_only")
    p.add_argument("--timeout", type=int, default=None)
    p = sub.add_parser("review"); p.add_argument("--id", required=True); p.add_argument("--reviewer", choices=AGENTS, required=True)
    p.add_argument("--timeout", type=int, default=None)
    p = sub.add_parser("merge"); p.add_argument("--id", required=True); p.add_argument("--force", action="store_true")
    p = sub.add_parser("ask"); p.add_argument("--agent", choices=AGENTS, required=True); p.add_argument("question", nargs="+")
    p.add_argument("--timeout", type=int, default=None)
    p = sub.add_parser("wt"); p.add_argument("--agent", choices=AGENTS, required=True); p.add_argument("--id", required=True)
    sub.add_parser("status")
    p = sub.add_parser("council", help="обсуждение всеми агентами: предложения → прожарка → консенсус")
    p.add_argument("--topic", default="idea", help="idea | arch | plan | demo | любая своя тема")
    p.add_argument("question", nargs="*", help="доп. вопрос/контекст")
    p.add_argument("--rounds", type=int, default=2, help="раундов взаимной критики")
    p.add_argument("--revisions", type=int, default=1, help="сколько раз переделывать решение при DISAGREE")
    p.add_argument("--agents", help="список через запятую, по умолчанию claude,codex,gemini")
    p.add_argument("--synth", default="codex", help="кто пишет итоговое решение (по умолчанию ведущий — codex)")
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--no-apply", action="store_true", help="не дописывать решение в docs и не создавать задачи")
    a = ap.parse_args()
    {"new": cmd_new, "run": cmd_run, "review": cmd_review, "merge": cmd_merge,
     "ask": cmd_ask, "wt": cmd_wt, "status": cmd_status, "council": cmd_council}[a.cmd](a)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
