# syntax=docker/dockerfile:1
# The base digest is public upstream Debian13, not the old AstrBot image.
FROM debian:13-slim@sha256:62bd423aeee912639ca8ee681c2b762cb3e25137e0a92b20be455898a9f034ad AS runtime-base
RUN --mount=type=secret,id=system_ca,required=true \
    apt-get -o Acquire::https::CaInfo=/run/secrets/system_ca update \
 && apt-get -o Acquire::https::CaInfo=/run/secrets/system_ca install -y --no-install-recommends \
      ca-certificates python3 libssl3t64 zlib1g libffi8 passwd \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --gid 999 nana-core \
 && useradd --uid 999 --gid 999 --no-create-home --shell /usr/sbin/nologin nana-core \
 && mkdir -p /opt/nana-core/runtime /opt/nana-core/data /opt/nana-core/logs /opt/nana-core/backups \
 && chown 999:999 /opt/nana-core/data /opt/nana-core/logs /opt/nana-core/backups \
 && chmod 0700 /opt/nana-core/data /opt/nana-core/logs /opt/nana-core/backups
COPY --chmod=0644 container_entry.py /usr/local/lib/nana/container_entry.py
RUN chmod 0755 /usr/local/lib/nana && chmod 0644 /usr/local/lib/nana/container_entry.py
USER 999:999
WORKDIR /opt/nana-core
ENTRYPOINT ["/usr/bin/python3", "-I", "/usr/local/lib/nana/container_entry.py"]
# Safe default never creates or opens a Subject. Missing candidate fails closed.
CMD ["verify"]

# Full image requires the ACTUAL supplied non-sensitive runtime archive.
# Do not synthesize a replacement or mark its qualification complete without it.
FROM runtime-base AS qualified-runtime
USER root
ARG RUNTIME_SHA256
ARG CORE_SHA256
ARG CORE_SOURCE_COMMIT
COPY runtime.tar.gz core.tar.gz /tmp/nana-input/
COPY --chmod=0644 extract_runtime.py /usr/local/lib/nana/extract_runtime.py
RUN python3 -I /usr/local/lib/nana/extract_runtime.py /tmp/nana-input/runtime.tar.gz "$RUNTIME_SHA256" \
 && /opt/nana-core/runtime/bin/python3 -I /usr/local/lib/nana/container_entry.py verify
COPY unpack_core.py /tmp/nana-input/unpack_core.py
RUN python3 -I /tmp/nana-input/unpack_core.py /tmp/nana-input/core.tar.gz \
      --destination "/opt/nana-core/runtime/core-releases/$CORE_SOURCE_COMMIT" --sha256 "$CORE_SHA256" \
 && chown -R 999:999 /opt/nana-core/runtime/core-releases \
 && rm -rf /tmp/nana-input
USER 999:999
RUN /opt/nana-core/runtime/bin/python3 -I "/opt/nana-core/runtime/core-releases/$CORE_SOURCE_COMMIT/bootstrap.py" install
ENV NANA_CORE_RELEASE=/opt/nana-core/runtime/core-releases/${CORE_SOURCE_COMMIT}
# Production command is explicitly 'serve' AFTER independent approval/activation.
CMD ["verify"]
