ARG GO_IMAGE

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

FROM scratch AS runtime

WORKDIR /app

COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=builder --chown=10001:10001 /out/frontend /app/frontend
COPY --chown=10001:10001 static /app/static
COPY --chown=10001:10001 templates /app/templates

ENV PORT=8080
ENV LISTEN_ADDR=0.0.0.0

USER 10001:10001

EXPOSE 8080

ENTRYPOINT ["/app/frontend"]