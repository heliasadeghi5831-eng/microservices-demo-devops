ARG JDK_IMAGE
ARG JRE_IMAGE

FROM ${JDK_IMAGE} AS build

WORKDIR /workspace

COPY gradlew build.gradle settings.gradle ./
COPY gradle ./gradle

ARG GRADLE_PROXY_HOST
ARG GRADLE_PROXY_PORT=3128

ENV GRADLE_OPTS="-Dorg.gradle.internal.http.connectionTimeout=120000 -Dorg.gradle.internal.http.socketTimeout=120000 -Dhttp.proxyHost=${GRADLE_PROXY_HOST} -Dhttp.proxyPort=${GRADLE_PROXY_PORT} -Dhttps.proxyHost=${GRADLE_PROXY_HOST} -Dhttps.proxyPort=${GRADLE_PROXY_PORT}"

RUN sed -i 's/^networkTimeout=.*/networkTimeout=120000/' \
      gradle/wrapper/gradle-wrapper.properties && \
    chmod +x gradlew

RUN for attempt in 1 2 3; do \
      ./gradlew --no-daemon downloadRepos && exit 0; \
      echo "Gradle download failed, retrying..."; \
      sleep 10; \
    done; \
    exit 1

COPY src ./src

RUN ./gradlew --no-daemon installDist


FROM ${JRE_IMAGE} AS runtime

WORKDIR /app

RUN groupadd --gid 10001 appgroup && \
    useradd \
      --uid 10001 \
      --gid appgroup \
      --no-create-home \
      --shell /usr/sbin/nologin \
      appuser

COPY --from=build --chown=10001:10001 \
    /workspace/build/install/hipstershop/ ./

ENV PORT=9555
ENV DISABLE_STATS=1
ENV DISABLE_TRACING=1

USER 10001:10001

EXPOSE 9555

HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
  CMD ["bash", "-c", "exec 3<>/dev/tcp/127.0.0.1/${PORT:-9555}; exec 3>&-; exec 3<&-"]

ENTRYPOINT ["./bin/AdService"]
