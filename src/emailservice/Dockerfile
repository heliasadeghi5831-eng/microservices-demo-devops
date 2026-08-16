# syntax=127.0.0.1:8081/docker-proxy/docker/dockerfile:1.7

ARG PYTHON_IMAGE=python:3.12-slim-bookworm

FROM ${PYTHON_IMAGE} AS dependencies

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}" \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120

WORKDIR /build

RUN python -m venv "${VIRTUAL_ENV}"

COPY requirements.txt ./

RUN --mount=type=cache,id=emailservice-pip,target=/root/.cache/pip \
    --mount=type=secret,id=pipconfig,target=/etc/pip.conf,required=true \
    PIP_CONFIG_FILE=/etc/pip.conf \
    pip install \
    --no-compile \
    --timeout 120 \
    --retries 10 \
    --requirement requirements.txt

FROM ${PYTHON_IMAGE} AS runtime

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    DISABLE_PROFILER=1

WORKDIR /app

RUN groupadd --gid 10001 appgroup && \
    useradd \
    --uid 10001 \
    --gid appgroup \
    --no-create-home \
    --shell /usr/sbin/nologin \
    appuser

COPY --from=dependencies --chown=10001:10001 \
    /opt/venv /opt/venv

COPY --chown=10001:10001 \
    email_server.py \
    order_consumer.py \
    logger.py \
    demo_pb2.py \
    demo_pb2_grpc.py \
    ./

COPY --chown=10001:10001 templates ./templates

USER 10001:10001

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import os,sys,grpc;from grpc_health.v1 import health_pb2,health_pb2_grpc;channel=grpc.insecure_channel('127.0.0.1:'+os.getenv('PORT','8080'));grpc.channel_ready_future(channel).result(timeout=2);response=health_pb2_grpc.HealthStub(channel).Check(health_pb2.HealthCheckRequest(),timeout=2);sys.exit(0 if response.status==health_pb2.HealthCheckResponse.SERVING else 1)"]

ENTRYPOINT ["python", "email_server.py"]
