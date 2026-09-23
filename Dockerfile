FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY data/samples ./data/samples
ENV PYTHONUNBUFFERED=1 DATABASE_PATH=/data/sana.sqlite3 SEED_DEMO=1 FALLBACK_TO_MOCK=1
RUN mkdir -p /data
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
