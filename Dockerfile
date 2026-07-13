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
COPY pyproject.toml .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY config/ ./config/
COPY shared/ ./shared/
COPY shared-contracts/ ./shared-contracts/
COPY knowledge_base/ ./knowledge_base/
COPY Inspiration-Research/ ./Inspiration-Research/

# Create data directory and drop root privileges
RUN groupadd --gid 10001 cognitive \
    && useradd --uid 10001 --gid cognitive --create-home --home-dir /home/cognitive cognitive \
    && mkdir -p /app/data /app/data/logs \
    && chown -R cognitive:cognitive /app /home/cognitive

ENV HOME=/home/cognitive \
    COGNITIVE_DATA_DIR=/app/data

USER cognitive

EXPOSE 8000 8001

# Default: start Cognitive-OS
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
