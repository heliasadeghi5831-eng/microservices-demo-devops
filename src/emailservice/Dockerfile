ARG PYTHON_IMAGE

FROM ${PYTHON_IMAGE} AS dependencies

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

WORKDIR /build

RUN python -m venv "${VIRTUAL_ENV}"

COPY requirements.txt ./

RUN python -m pip install \
      --no-cache-dir \
      --no-compile \
      --requirement requirements.txt


FROM ${PYTHON_IMAGE} AS runtime

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV DISABLE_PROFILER=1

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
