# Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml poetry.lock README.md ./
RUN pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false \
    && poetry install --without dev --no-interaction --no-ansi --no-root
COPY . .
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
