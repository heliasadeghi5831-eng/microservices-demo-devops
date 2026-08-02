ARG PYTHON_IMAGE=python:3.12-slim-bookworm

FROM ${PYTHON_IMAGE} AS build

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120

WORKDIR /build

RUN python -m venv /opt/venv

ENV PATH=/opt/venv/bin:$PATH

COPY requirements.txt ./

RUN --mount=type=cache,id=recommendationservice-pip,target=/root/.cache/pip \
    pip install --no-compile -r requirements.txt

FROM ${PYTHON_IMAGE} AS runtime

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    PRODUCT_CATALOG_SERVICE_ADDR=productcatalogservice:3550 \
    DISABLE_PROFILER=1 \
    ENABLE_TRACING=0

RUN groupadd --gid 10001 recommendation \
    && useradd \
        --uid 10001 \
        --gid recommendation \
        --create-home \
        --shell /usr/sbin/nologin \
        recommendation

WORKDIR /app

COPY --from=build /opt/venv /opt/venv

COPY --chown=recommendation:recommendation recommendation_server.py ./
COPY --chown=recommendation:recommendation logger.py ./
COPY --chown=recommendation:recommendation demo_pb2.py ./
COPY --chown=recommendation:recommendation demo_pb2_grpc.py ./

EXPOSE 8080

USER recommendation

HEALTHCHECK --interval=10s --timeout=4s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import grpc; from grpc_health.v1 import health_pb2, health_pb2_grpc; channel=grpc.insecure_channel('127.0.0.1:8080'); response=health_pb2_grpc.HealthStub(channel).Check(health_pb2.HealthCheckRequest(), timeout=2); raise SystemExit(0 if response.status == health_pb2.HealthCheckResponse.SERVING else 1)"]

ENTRYPOINT ["python", "recommendation_server.py"]
