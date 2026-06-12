# Lightweight Python base image.
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY monitoring/monitoring_service.py .
CMD ["python", "monitoring_service.py"]
