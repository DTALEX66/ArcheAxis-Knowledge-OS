# Cognitive-Loop-OS Docker image
FROM python:3.11-slim

WORKDIR /app

# Install system deps for document parsing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY config/ ./config/
COPY shared/ ./shared/
COPY shared-contracts/ ./shared-contracts/
COPY Knowledge-Base/ ./Knowledge-Base/
COPY Inspiration-Research/ ./Inspiration-Research/

# Create data directory
RUN mkdir -p /app/data /app/data/logs

EXPOSE 8000 8001 8002

# Default: start Cognitive-OS
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
