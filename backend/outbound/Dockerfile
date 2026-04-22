FROM python:3.11-slim
WORKDIR /app
RUN pip install poetry --break-system-packages
COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-root --only main
COPY . .
CMD ["poetry", "run", "celery", "-A", "outbound.tasks", "worker", "--loglevel=info", "-c", "8", "-Q", "outbound_calls"]
