FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install fastapi uvicorn grpcio grpcio-tools openai

# Copy the llm_service directory contents
COPY llm_service/ /app/

# Set PYTHONPATH to make module discoverable
ENV PYTHONPATH=/app

EXPOSE 8004

# Run the service directly (not as module)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]
