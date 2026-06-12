# Lightweight Python base image.
FROM python:3.11-slim
WORKDIR /app
# Install dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Shared logging helper used by the service.
COPY common_log.py .
# Service source code.
COPY gateway/gateway_service.py .
CMD ["python", "gateway_service.py"]
