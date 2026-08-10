# syntax=127.0.0.1:8081/docker-proxy/docker/dockerfile:1.7

ARG NODE_IMAGE

FROM ${NODE_IMAGE} AS dependencies

WORKDIR /app

COPY package.json package-lock.json ./

RUN --mount=type=secret,id=npmrc,target=/root/.npmrc \
    npm ci --omit=dev && \
    npm cache clean --force

FROM ${NODE_IMAGE} AS runtime

WORKDIR /app

RUN groupadd --gid 10001 appgroup && \
    useradd \
    --uid 10001 \
    --gid appgroup \
    --no-create-home \
    --shell /usr/sbin/nologin \
    appuser

COPY --from=dependencies --chown=10001:10001 \
    /app/node_modules ./node_modules

COPY --chown=10001:10001 \
    package.json \
    index.js \
    server.js \
    charge.js \
    logger.js \
    ./

COPY --chown=10001:10001 proto ./proto

ENV NODE_ENV=production
ENV PORT=50051

USER 10001:10001

EXPOSE 50051

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["node", "-e", "const net=require('net');const port=Number(process.env.PORT||50051);const s=net.connect({host:'127.0.0.1',port},()=>{s.end();process.exit(0)});s.setTimeout(2000);s.on('timeout',()=>{s.destroy();process.exit(1)});s.on('error',()=>process.exit(1));"]

ENTRYPOINT ["node", "index.js"]
