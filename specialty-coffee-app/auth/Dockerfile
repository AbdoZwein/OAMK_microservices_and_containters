# Lightweight Python base image.
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY common_log.py .
COPY auth/auth_service.py .
CMD ["python", "auth_service.py"]
