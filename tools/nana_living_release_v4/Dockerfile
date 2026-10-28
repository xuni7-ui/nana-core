# syntax=docker/dockerfile:1
# Exact locally qualified Nana/Debian13 image ID is checked by build_artifacts.py.
# This is not an AstrBot base. No host OpenSSL or system Python is changed.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
USER root
ARG CORE_SOURCE_COMMIT
ARG CORE_SHA256
ARG WEB_SHA256
# One offline layer avoids retaining copied archives in the delivered image.
RUN --mount=type=bind,source=.,target=/build,readonly \
    umask 022 \
 && cp /build/container_entry.py /usr/local/lib/nana/container_entry.py \
 && cp /build/loopback_relay.py /usr/local/lib/nana/loopback_relay.py \
 && python3 -I -B /build/unpack.py /build/core.tar.gz --destination "/opt/nana-core/runtime/core-releases/$CORE_SOURCE_COMMIT" --sha256 "$CORE_SHA256" \
 && python3 -I -B /build/extract_web.py /build/web.tar.gz "$WEB_SHA256" \
 && chown -R 999:999 "/opt/nana-core/runtime/core-releases/$CORE_SOURCE_COMMIT" \
 && python3 -B -c "import os,subprocess;os.setgid(999);os.setuid(999);subprocess.run(['/opt/nana-core/runtime/bin/python3','-I','-B','/opt/nana-core/runtime/core-releases/$CORE_SOURCE_COMMIT/bootstrap.py','install'],check=True)"
ENV NANA_CORE_RELEASE=/opt/nana-core/runtime/core-releases/${CORE_SOURCE_COMMIT}
USER 999:999
CMD ["verify"]
