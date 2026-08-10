# syntax=127.0.0.1:8081/docker-proxy/docker/dockerfile:1.7

ARG PYTHON_IMAGE=python:3.12-slim-bookworm

FROM ${PYTHON_IMAGE} AS build

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=180

WORKDIR /build

RUN python -m venv /opt/venv

ENV PATH=/opt/venv/bin:$PATH

COPY requirements.txt ./

RUN --mount=type=cache,id=shoppingassistant-pip,target=/root/.cache/pip \
    --mount=type=secret,id=pipconfig,target=/etc/pip.conf,required=true \
    PIP_CONFIG_FILE=/etc/pip.conf \
    pip download \
    --dest /root/.cache/pip/wheelhouse \
    --retries 10 \
    --requirement requirements.txt

RUN --mount=type=cache,id=shoppingassistant-pip,target=/root/.cache/pip \
    pip install \
    --no-index \
    --find-links=/root/.cache/pip/wheelhouse \
    --no-compile \
    --requirement requirements.txt

FROM ${PYTHON_IMAGE} AS runtime

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --gid 10001 shoppingassistant && \
    useradd \
    --uid 10001 \
    --gid shoppingassistant \
    --create-home \
    --shell /usr/sbin/nologin \
    shoppingassistant

WORKDIR /app

COPY --from=build /opt/venv /opt/venv

COPY --chown=shoppingassistant:shoppingassistant \
    shoppingassistantservice.py \
    ./

USER shoppingassistant

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=4s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import http.client;c=http.client.HTTPConnection('127.0.0.1',8080,timeout=2);c.request('GET','/');r=c.getresponse();raise SystemExit(0 if r.status == 405 else 1)"]

ENTRYPOINT ["python", "shoppingassistantservice.py"]
