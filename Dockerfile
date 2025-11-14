# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the restore script
COPY 3_restore_messages.py .

# Create directories for volumes
RUN mkdir -p /app/backups /app/sessions

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the restore script
CMD ["python3", "3_restore_messages.py"]
