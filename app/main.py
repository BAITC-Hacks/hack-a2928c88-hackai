"""FastAPI-приложение. Один процесс отдаёт и API, и статический UI — один деплой, одна ссылка."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from . import agent, llm
from .readers import UnsupportedFile, to_text
from .schemas import Decision, RunRequest, RunResult

APP_NAME = os.getenv("APP_NAME", "HackAlem Project")
STATIC = Path(__file__).parent / "static"
SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"

app = FastAPI(title=APP_NAME)
RUNS: dict[str, RunResult] = {}  # в памяти: для демо достаточно, раскрыть в README


@app.get("/health")
def health():
    return {"ok": True, "mode": "mock" if llm.is_mock() else "live", "model": llm.MODEL}


@app.get("/api/samples")
def samples():
    if not SAMPLES.exists():
        return []
    exts = {".txt", ".md", ".csv", ".tsv", ".eml", ".json"}
    return [{"name": p.name, "text": p.read_text(encoding="utf-8")}
            for p in sorted(SAMPLES.iterdir()) if p.suffix.lower() in exts]


@app.post("/api/run", response_model=RunResult)
def run(req: RunRequest):
    res = agent.run(req)
    RUNS[res.run_id] = res
    return res


@app.post("/api/upload", response_model=RunResult)
async def upload(file: UploadFile):
    raw = await file.read()
    try:
        text = to_text(file.filename or "", raw)
    except UnsupportedFile as e:
        raise HTTPException(415, str(e))
    return run(RunRequest(text=text, source_name=file.filename or "upload"))


@app.post("/api/runs/{run_id}/decision", response_model=RunResult)
def decide(run_id: str, d: Decision):
    res = RUNS.get(run_id)
    if not res:
        raise HTTPException(404, "run not found")
    for f in res.findings:
        if f.id == d.finding_id:
            f.status = d.status
            return res
    raise HTTPException(404, "finding not found")


@app.get("/api/runs/{run_id}/report", response_class=PlainTextResponse)
def report(run_id: str):
    res = RUNS.get(run_id)
    if not res:
        raise HTTPException(404, "run not found")
    lines = [f"# Отчёт {run_id} ({res.mode})", "", res.extraction.summary, ""]
    for f in res.findings:
        lines.append(f"- [{f.status}] ({f.severity.value}, {f.produced_by}) {f.title}: {f.explanation}")
        for e in f.evidence:
            lines.append(f"    > {e.source} {e.locator}: «{e.quote}»")
    return "\n".join(lines)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
