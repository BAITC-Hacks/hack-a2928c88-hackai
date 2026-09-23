"""Проверить задеплоенный проект снаружи: python scripts/smoke_url.py https://....onrender.com"""
import sys, json, urllib.request

base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8000"
def get(p): return urllib.request.urlopen(base + p, timeout=60).read().decode()
print("health:", get("/health"))
assert "<html" in get("/").lower(), "UI не отдаётся"
req = urllib.request.Request(base + "/api/run", data=json.dumps({"text": "Тест: строка 1\nстрока 2"}).encode(),
                             headers={"Content-Type": "application/json"})
res = json.loads(urllib.request.urlopen(req, timeout=180).read())
print("run:", res["mode"], "findings:", len(res["findings"]))
print("OK — ссылка рабочая")
