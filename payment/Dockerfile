# Lightweight Python base image (slim = small image, fits the container idea).
FROM python:3.11-slim

# Working directory inside the container.
WORKDIR /app

# Install the ZeroMQ Python binding (pyzmq) used for messaging.
RUN pip install --no-cache-dir pyzmq==26.0.3

# Copy the service source code into the image.
COPY payment_service.py .

# Run the service when the container starts.
CMD ["python", "payment_service.py"]
