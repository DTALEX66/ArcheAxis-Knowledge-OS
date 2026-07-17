ARG GO_IMAGE=golang:1.26.5-alpine3.23@sha256:622e56dbc11a8cfe87cafa2331e9a201877271cbff918af53d3be315f3da88cc
ARG CADDY_VERSION=v2.11.4

FROM ${GO_IMAGE} AS caddy-builder
ARG CADDY_VERSION
ENV CGO_ENABLED=0 \
    GOTOOLCHAIN=local \
    GOPROXY=https://proxy.golang.org \
    GOSUMDB=sum.golang.org
RUN go install -trimpath -ldflags="-s -w -buildid= -X github.com/caddyserver/caddy/v2.CustomVersion=${CADDY_VERSION}" github.com/caddyserver/caddy/v2/cmd/caddy@${CADDY_VERSION} \
    && go version -m /go/bin/caddy > /caddy.buildinfo \
    && mkdir -p /rootfs/etc/ssl/certs /rootfs/etc/caddy /rootfs/data /rootfs/config \
    && cp /etc/ssl/certs/ca-certificates.crt /rootfs/etc/ssl/certs/ca-certificates.crt

FROM scratch
COPY --from=caddy-builder /go/bin/caddy /usr/bin/caddy
COPY --from=caddy-builder /caddy.buildinfo /usr/share/caddy/caddy.buildinfo
COPY --from=caddy-builder /rootfs/etc /etc
COPY --chown=1000:1000 --from=caddy-builder /rootfs/data /data
COPY --chown=1000:1000 --from=caddy-builder /rootfs/config /config
ENTRYPOINT ["/usr/bin/caddy"]
CMD ["run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
