FROM nana-first-life/cloud-qualified:20261026-final
USER root
COPY core.tar.gz unpack.py /tmp/unified/
ARG CORE_SHA256
RUN mkdir -p /opt/nana-core/runtime/core-releases \
 && python3 -I /tmp/unified/unpack.py /tmp/unified/core.tar.gz --destination /opt/nana-core/runtime/core-releases/9217e3f3550dc5a875c42ac6de53035dd73deae2 --sha256 "$CORE_SHA256" \
 && chown -R 999:999 /opt/nana-core/runtime/core-releases/9217e3f3550dc5a875c42ac6de53035dd73deae2 \
 && rm -rf /tmp/unified
USER 999:999
RUN /opt/nana-core/runtime/bin/python3 -I -B /opt/nana-core/runtime/core-releases/9217e3f3550dc5a875c42ac6de53035dd73deae2/bootstrap.py install
ENV NANA_CORE_RELEASE=/opt/nana-core/runtime/core-releases/9217e3f3550dc5a875c42ac6de53035dd73deae2
CMD ["verify"]
