# Development compatibility image only. Never deployed to the Nana host.
FROM ubuntu@sha256:534baea6a22c03a63003dbc8dbe78fe34bc0d7e595d9a9dc9834884ff530eb55
RUN --mount=type=secret,id=proxy_ca,required=true \
    SSL_CERT_FILE=/run/secrets/proxy_ca apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3.12 python3.12-venv libsqlite3-0 git && \
    rm -rf /var/lib/apt/lists/*
RUN /usr/bin/python3.12 -I -S -c 'import sys,sysconfig,platform; assert sys.version_info[:3]==(3,12,3); assert sysconfig.get_config_var("SOABI")=="cpython-312-x86_64-linux-gnu"; assert platform.libc_ver()==("glibc","2.39")'
