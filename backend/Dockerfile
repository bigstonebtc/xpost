FROM python:3.12-slim

WORKDIR /app

# バージョン表示（VERSION を最後に変更したコミットの日付・更新履歴）を git から読むため
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
