ARG GO_IMAGE
ARG RUNTIME_IMAGE

FROM ${GO_IMAGE} AS builder

WORKDIR /src

RUN apk add --no-cache git ca-certificates

COPY go.mod go.sum ./

ARG GOPROXY=https://proxy.golang.org,direct
ENV GOPROXY=${GOPROXY}

RUN go mod download

COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build \
    -trimpath \
    -ldflags="-s -w" \
    -o /out/frontend \
    .

FROM ${RUNTIME_IMAGE} AS runtime

RUN apk add --no-cache ca-certificates && \
    addgroup -S -g 10001 appgroup && \
    adduser -S -D -H -u 10001 -G appgroup appuser

WORKDIR /app

COPY --from=builder /out/frontend /app/frontend
COPY --chown=10001:10001 static /app/static
COPY --chown=10001:10001 templates /app/templates

ENV PORT=8080
ENV LISTEN_ADDR=0.0.0.0

USER 10001:10001

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8080/_healthz || exit 1

ENTRYPOINT ["/app/frontend"]
