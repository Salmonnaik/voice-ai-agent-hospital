FROM python:3.11-slim
WORKDIR /app
RUN pip install fastapi uvicorn grpcio grpcio-tools elevenlabs azure-cognitiveservices-speech
COPY . .
EXPOSE 8005 50054
CMD ["python", "-m", "uvicorn", "tts_service.main:app", "--host", "0.0.0.0", "--port", "8005"]
