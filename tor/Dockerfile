FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        tor \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 9050

ENTRYPOINT ["/entrypoint.sh"]
