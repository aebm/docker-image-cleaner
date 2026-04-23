# =============================================================================
# Arguments (must be before first FROM to be available in all stages)
# =============================================================================
ARG GO_VERSION=1.21.5
ARG VERSION=0.0.0

# =============================================================================
# Build Stage
# =============================================================================
FROM golang:${GO_VERSION}-bookworm AS building-stage

WORKDIR /build

# Copy dependency files first for better layer caching
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY docker-image-cleaner.go ./

# Build static binary with stripped symbols
RUN CGO_ENABLED=0 go build \
    -ldflags="-s -w" \
    -o docker-image-cleaner docker-image-cleaner.go

# =============================================================================
# Package Stage
# =============================================================================
FROM debian:bookworm-slim AS packaging-stage

ARG VERSION

RUN apt-get update && \
    apt-get install -y --no-install-recommends dpkg && \
    rm -rf /var/lib/apt/lists/*

COPY bifer-docker-image-cleaner /package/bifer-docker-image-cleaner
COPY --from=building-stage /build/docker-image-cleaner \
    /package/bifer-docker-image-cleaner/usr/local/sbin/

RUN chmod 755 /package/bifer-docker-image-cleaner/DEBIAN/postinst && \
    chmod +x /package/bifer-docker-image-cleaner/usr/local/sbin/docker-image-cleaner && \
    sed -i -e "s/Version:.*/Version: ${VERSION}/" \
        "/package/bifer-docker-image-cleaner/DEBIAN/control"

WORKDIR /package
RUN dpkg-deb -Z gzip --build --root-owner-group bifer-docker-image-cleaner && \
    mv bifer-docker-image-cleaner.deb bifer-docker-image-cleaner_${VERSION}.deb

# =============================================================================
# Export Stage
# =============================================================================
FROM scratch AS export-stage

ARG VERSION
COPY --from=packaging-stage /package/bifer-docker-image-cleaner_${VERSION}.deb /