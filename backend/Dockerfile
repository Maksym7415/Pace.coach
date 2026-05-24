FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

EXPOSE 8080

CMD exec gunicorn src.api.app:app -k uvicorn.workers.UvicornWorker --bind :$PORT --workers 1 --threads 8 --timeout 0
