# Lightweight Python base image.
FROM python:3.11-slim

WORKDIR /app

# Install the ZeroMQ Python binding (pyzmq).
RUN pip install --no-cache-dir pyzmq==26.0.3

# Copy the service source code.
COPY ordering_service.py .

# Run the orchestrator service on container start.
CMD ["python", "ordering_service.py"]
