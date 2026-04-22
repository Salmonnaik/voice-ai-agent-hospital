FROM python:3.11-slim
WORKDIR /app
RUN pip install poetry --break-system-packages
COPY pyproject.toml ./
RUN poetry install --no-root --only main
COPY . .
EXPOSE 8002 50052
CMD ["poetry", "run", "python", "-m", "orchestrator.main"]
