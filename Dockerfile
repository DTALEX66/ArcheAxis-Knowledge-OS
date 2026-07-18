ARG PYTHON_IMAGE=python:3.11.15-slim-bookworm@sha256:b18992999dbe963a45a8a4da40ac2b1975be1a776d939d098c647482bcad5cba
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.11.28@sha256:0f36cb9361a3346885ca3677e3767016687b5a170c1a6b88465ec14aefec90aa
ARG SOURCE_DATE_EPOCH=315532800

FROM ${UV_IMAGE} AS uv-bin
FROM ${PYTHON_IMAGE} AS python-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_NO_PROGRESS=1 \
    SOURCE_DATE_EPOCH=315532800

WORKDIR /build
COPY --from=uv-bin /uv /usr/local/bin/uv

FROM python-base AS wheel-builder

COPY pyproject.toml uv.lock README.md ./
COPY app/ ./app/
COPY config/ ./config/
COPY shared/ ./shared/
COPY knowledge_base/ ./knowledge_base/
COPY inspiration_research/ ./inspiration_research/

RUN uv lock --check \
    && uv export --frozen --no-dev --no-emit-project --format requirements-txt --output-file /locked-requirements.txt \
    && uv export --frozen --only-group build --no-emit-project --format requirements-txt --output-file /locked-build-requirements.txt \
    && python -m pip install --no-cache-dir --require-hashes --requirement /locked-build-requirements.txt \
    && uv build --python /usr/local/bin/python --wheel --no-build-isolation --out-dir /wheels

FROM ${PYTHON_IMAGE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/home/cognitive \
    COGNITIVE_DATA_DIR=/app/data \
    COGNITIVE_DB_PATH=/app/data/cognitive_os.sqlite

WORKDIR /app

RUN groupadd --gid 10001 cognitive \
    && useradd --uid 10001 --gid cognitive --create-home --home-dir /home/cognitive cognitive \
    && mkdir -p /app/data /app/data/logs \
    && chown -R cognitive:cognitive /app /home/cognitive

COPY --from=wheel-builder /locked-requirements.txt /tmp/locked-requirements.txt
RUN python -m pip install --no-cache-dir --require-hashes --requirement /tmp/locked-requirements.txt \
    && rm -f /tmp/locked-requirements.txt

COPY --from=wheel-builder /wheels/ /wheels/
RUN python -m pip install --no-cache-dir --no-deps /wheels/cognitive_loop_os-*.whl \
    && python -m pip check \
    && python -m pip uninstall --yes setuptools wheel jaraco.context \
    && python -m pip uninstall --yes pip \
    && python -c "import importlib.util; assert all(importlib.util.find_spec(name) is None for name in ('pip', 'setuptools', 'wheel', 'jaraco'))" \
    && rm -rf /wheels

USER cognitive

EXPOSE 8000 8001

ENTRYPOINT ["python", "-m", "app.container_entrypoint"]
CMD ["core"]
