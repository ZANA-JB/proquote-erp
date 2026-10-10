FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PDF_STORAGE_PATH=/var/data/pdfs

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    fontconfig \
    fonts-dejavu-core \
    libffi8 \
    libgdk-pixbuf-2.0-0 \
    libharfbuzz-subset0 \
    libharfbuzz0b \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY Backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY Backend/app ./app
COPY Backend/alembic ./alembic
COPY Backend/alembic.ini ./alembic.ini
COPY REFERENCE/logo.jpeg ./REFERENCE/logo.jpeg

EXPOSE 10000

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers --forwarded-allow-ips='*'"]
