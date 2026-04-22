FROM python:3.11-slim
WORKDIR /app
RUN pip install fastapi uvicorn grpcio grpcio-tools deepgram-sdk
COPY . .
EXPOSE 8003 50051
CMD ["python", "-m", "uvicorn", "stt_service.main:app", "--host", "0.0.0.0", "--port", "8003"]
