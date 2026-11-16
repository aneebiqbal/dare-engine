# MediaMTX ships a distroless image with no shell, so Docker cannot run wget or
# curl for a health check. This thin wrapper adds curl and copies the binary in.
FROM bluenviron/mediamtx:latest AS upstream
FROM alpine:3.21

RUN apk add --no-cache curl

COPY --from=upstream /mediamtx /mediamtx
ENTRYPOINT ["/mediamtx"]
