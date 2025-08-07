FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    libxml2 \
    libxslt1.1 \
    libjpeg62-turbo \
    libpng16-16 \
    libgif7 \
    libwebp7 \
    libfreetype6 \
    libharfbuzz0b \
    libfribidi0 \
    liblcms2-2 \
    libopenjp2-7 \
    libtiff6 \
    libcairo2 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    fonts-dejavu \
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