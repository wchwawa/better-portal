# Experimental PS Portal one-way bitrate relay (portal_auto.py run) for Linux Docker hosts.
# Build context is the repository root; see deploy/docker/compose.yaml.
FROM alpine:3.22

LABEL org.opencontainers.image.title="ps5-portal-high-bitrate relay" \
      org.opencontainers.image.description="Experimental PS Portal -> PS5 Remote Play bitrate relay (auto mode)" \
      org.opencontainers.image.source="https://github.com/atameric/ps5-portal-high-bitrate" \
      org.opencontainers.image.licenses="MIT"

ARG SOURCE_REV=unknown
COPY portal_*.py protocol.py requirements.txt LICENSE /src/
COPY locales/ /src/locales/
COPY tests/ /src/tests/
COPY deploy/install-alpine.sh deploy/portal deploy/portal-bitrate.initd /src/deploy/
RUN PORTAL_CONTAINER=1 PORTAL_SOURCE_REV="$SOURCE_REV" sh /src/deploy/install-alpine.sh \
 && rm -rf /src /root/.cache

ENV PORTAL_CONTAINER=1
VOLUME ["/etc/portal-bitrate", "/var/lib/portal-bitrate-auto"]

# status.json is rewritten every 2 s while the relay runs.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD ["/usr/local/bin/portal", "health"]

ENTRYPOINT ["/usr/local/bin/portal"]
CMD ["service"]
