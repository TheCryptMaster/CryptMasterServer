FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
COPY cli ./cli
COPY migration ./migration

EXPOSE 2053

CMD ["python", "-m", "app.main"]
