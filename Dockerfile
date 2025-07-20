# Dockerfile (backend) – only the relevant bits
FROM python:3.12-slim
WORKDIR /app

# 1. Install Poetry
RUN pip install "poetry==1.8.2"

# 2. Tell Poetry to install into the *system* interpreter, not a venv
ENV POETRY_VIRTUALENVS_CREATE=false
COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-interaction --no-root        # deps go to /usr/local/bin

COPY . .

# 3. Launch through Poetry (so PYTHONPATH etc. are right)
CMD ["poetry", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
