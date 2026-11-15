# The sidecar never constructs/runs a Core Store and has no native QQ addon.
FROM python:3.12.14-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e
WORKDIR /app
COPY requirements-nanalink.lock /app/requirements-nanalink.lock
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    pip install --no-cache-dir --requirement /app/requirements-nanalink.lock
COPY --chown=999:999 src/nana_core /app/src/nana_core
RUN mkdir -p /run/nanalink && chown 999:999 /run/nanalink && chmod 700 /run/nanalink
ENV PYTHONPATH=/app/src PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 999:999
ENTRYPOINT ["python", "-m", "nana_core.nanalink"]
