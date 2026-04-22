FROM python:3.11-slim
WORKDIR /app
RUN pip install poetry --break-system-packages
COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-root --only main
COPY . .
EXPOSE 8006 50055
CMD ["poetry", "run", "uvicorn", "memory.main:app", "--host", "0.0.0.0", "--port", "8006"]
