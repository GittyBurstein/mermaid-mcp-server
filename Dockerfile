FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY . /app

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

ENV PROJECT_ROOT="/project" \
    KROKI_BASE_URL="https://kroki.io" \
    KROKI_TIMEOUT="20" \
    MAX_FILE_CHARS="200000"

RUN mkdir -p /project

CMD ["python", "src/server/server.py"]
