# syntax=127.0.0.1:8081/docker-proxy/docker/dockerfile:1.7

ARG JDK_IMAGE
ARG JRE_IMAGE

FROM ${JDK_IMAGE} AS build

WORKDIR /workspace

COPY gradlew build.gradle settings.gradle ./
COPY gradle ./gradle

ENV GRADLE_OPTS="-Dorg.gradle.internal.http.connectionTimeout=120000 -Dorg.gradle.internal.http.socketTimeout=120000"

RUN mkdir -p /root/.gradle && \
    chmod +x gradlew

RUN --mount=type=cache,id=adservice-gradle-cache,target=/root/.gradle/caches \
    --mount=type=cache,id=adservice-gradle-wrapper,target=/root/.gradle/wrapper \
    --mount=type=secret,id=gradleproperties,target=/root/.gradle/gradle.properties,required=true \
    --mount=type=secret,id=gradleinit,target=/run/secrets/nexus.init.gradle,required=true \
    for attempt in 1 2 3; do \
      ./gradlew \
        --no-daemon \
        --init-script /run/secrets/nexus.init.gradle \
        downloadRepos && exit 0; \
      echo "Gradle download failed, retrying..."; \
      sleep 10; \
    done; \
    exit 1

COPY src ./src

RUN --mount=type=cache,id=adservice-gradle-cache,target=/root/.gradle/caches \
    --mount=type=cache,id=adservice-gradle-wrapper,target=/root/.gradle/wrapper \
    --mount=type=secret,id=gradleproperties,target=/root/.gradle/gradle.properties,required=true \
    --mount=type=secret,id=gradleinit,target=/run/secrets/nexus.init.gradle,required=true \
    ./gradlew \
      --no-daemon \
      --init-script /run/secrets/nexus.init.gradle \
      installDist


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
