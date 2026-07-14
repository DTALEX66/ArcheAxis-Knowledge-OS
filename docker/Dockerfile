# Legacy-compatible Docker entry point. Build from repository root:
#   docker build -f docker/Dockerfile .
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY config/ ./config/
COPY shared/ ./shared/
COPY shared-contracts/ ./shared-contracts/
COPY knowledge_base/ ./knowledge_base/
COPY inspiration_research/ ./inspiration_research/
COPY Inspiration-Research/ ./Inspiration-Research/

RUN groupadd --gid 10001 cognitive \
    && useradd --uid 10001 --gid cognitive --create-home --home-dir /home/cognitive cognitive \
    && mkdir -p /app/data /app/data/logs \
    && chown -R cognitive:cognitive /app /home/cognitive

ENV HOME=/home/cognitive \
    COGNITIVE_DATA_DIR=/app/data

USER cognitive
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
