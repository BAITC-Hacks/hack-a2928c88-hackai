"""Мини-оценка на размеченных примерах: python -m eval.run_eval

Кейс: eval/cases/*.json  {"name", "text", "expected_rule_ids": [...], "expected_keywords": [...]}
Пишет eval/report.md — положить цифры в README (раздел «Проверка»), честно указав размер набора
и MOCK/live. Сравнение с бейзлайном: запустить с BASELINE=1 (один промпт без правил).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import agent, llm  # noqa: E402
from app.schemas import RunRequest  # noqa: E402

CASES = sorted((ROOT / "eval" / "cases").glob("*.json"))


def main() -> int:
    rows, hit, total = [], 0, 0
    for p in CASES:
        case = json.loads(p.read_text(encoding="utf-8"))
        res = agent.run(RunRequest(text=case["text"], source_name=case.get("name", p.stem)))
        got_rules = {f.rule_id for f in res.findings if f.rule_id}
        blob = " ".join(f.title + " " + f.explanation for f in res.findings).lower()
        exp_r = set(case.get("expected_rule_ids", []))
        exp_k = [k.lower() for k in case.get("expected_keywords", [])]
        ok_r = exp_r <= got_rules
        ok_k = all(k in blob for k in exp_k)
        ok = ok_r and ok_k
        hit += ok
        total += 1
        rows.append(f"| {p.stem} | {'✅' if ok else '❌'} | {sorted(got_rules)} | {len(res.findings)} |")
    mode = "mock" if llm.is_mock() else f"live ({llm.MODEL}/{llm.MODEL_STRONG})"
    report = [f"# Eval ({mode})", "", f"Пройдено: **{hit}/{total}**", "",
              "| case | ok | rules | findings |", "|---|---|---|---|", *rows]
    out = ROOT / "eval" / "report.md"
    out.write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))
    return 0 if total == 0 or hit == total or os.getenv("EVAL_SOFT") == "1" else 1


if __name__ == "__main__":
    raise SystemExit(main())
