# Lightweight Python base image.
FROM python:3.11-slim

WORKDIR /app

# Install the ZeroMQ Python binding (pyzmq).
RUN pip install --no-cache-dir pyzmq==26.0.3

# Copy the service source code.
COPY subscriber_service.py .

# Run the subscriber service on container start.
CMD ["python", "subscriber_service.py"]
