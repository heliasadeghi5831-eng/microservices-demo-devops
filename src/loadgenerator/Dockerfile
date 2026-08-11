# syntax=127.0.0.1:8081/docker-proxy/docker/dockerfile:1.7

ARG PYTHON_IMAGE=python:3.12-slim-bookworm

FROM ${PYTHON_IMAGE} AS build

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120

WORKDIR /build

RUN python -m venv /opt/venv

ENV PATH=/opt/venv/bin:$PATH

COPY requirements.txt ./

RUN --mount=type=cache,id=loadgenerator-pip,target=/root/.cache/pip \
    --mount=type=secret,id=pipconfig,target=/etc/pip.conf,required=true \
    PIP_CONFIG_FILE=/etc/pip.conf \
    pip install \
    --no-compile \
    --retries 10 \
    --requirement requirements.txt

FROM ${PYTHON_IMAGE} AS runtime

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LOCUST_LOCUSTFILE=/app/locustfile.py \
    LOCUST_HEADLESS=true \
    LOCUST_HOST=http://frontend:8080 \
    LOCUST_USERS=10 \
    LOCUST_SPAWN_RATE=1

RUN groupadd --gid 10001 loadgenerator && \
    useradd \
    --uid 10001 \
    --gid loadgenerator \
    --create-home \
    --shell /usr/sbin/nologin \
    loadgenerator

WORKDIR /app

COPY --from=build /opt/venv /opt/venv
COPY --chown=loadgenerator:loadgenerator locustfile.py ./

USER loadgenerator

STOPSIGNAL SIGINT

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import os; os.kill(1, 0)"]

ENTRYPOINT ["locust"]
