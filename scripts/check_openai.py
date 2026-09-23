"""Проверить ключ и доступность моделей: python scripts/check_openai.py"""
import os, sys
from openai import OpenAI

if not os.getenv("OPENAI_API_KEY"):
    sys.exit("OPENAI_API_KEY не задан (см. .env.example)")
c = OpenAI()
ids = sorted(m.id for m in c.models.list())
print("Доступно моделей:", len(ids))
for want in (os.getenv("OPENAI_MODEL", "gpt-5.4-mini"), os.getenv("OPENAI_MODEL_STRONG", "gpt-5.5")):
    print(("OK   " if want in ids else "НЕТ  ") + want)
print("gpt-5*:", [i for i in ids if i.startswith("gpt-5")][:30])
r = c.responses.create(model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"), input="Ответь одним словом: работает?")
print("Тестовый ответ:", r.output_text)
