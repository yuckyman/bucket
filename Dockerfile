FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    libpng-dev \
    libgif-dev \
    libwebp-dev \
    libfreetype6-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff5-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy application code
COPY bucket/ ./bucket/

# Create necessary directories
RUN mkdir -p /app/data /app/output /app/templates

# Set environment variables
ENV PYTHONPATH=/app
ENV BUCKET_DB_PATH=/app/data/bucket.db
ENV BUCKET_OUTPUT_DIR=/app/output

# Expose port
EXPOSE 8000

# Default command
CMD ["bucket", "serve", "--host", "0.0.0.0", "--port", "8000"]