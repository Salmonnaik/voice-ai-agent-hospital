FROM python:3.11-slim
WORKDIR /app
RUN pip install poetry --break-system-packages
COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-root --only main
COPY . .
EXPOSE 8007 50056
CMD ["poetry", "run", "uvicorn", "scheduler.main:app", "--host", "0.0.0.0", "--port", "8007"]
