# Orthanc pinned by digest, running as the image's unprivileged "orthanc" user.
FROM orthancteam/orthanc:26.9.1@sha256:d2705f2c56547e55ce9bc2250fd22d05d326493b3f3d9fa191ecb7db8ca6b5a2
USER root
# a fresh named volume inherits this ownership
RUN mkdir -p /var/lib/orthanc/db && chown -R orthanc:orthanc /var/lib/orthanc/db \
 # the entrypoint writes a random /etc/hostid when missing; do it at build time so the root fs can be read-only
 && printf '%x' "$(shuf -i 268435456-4294967295 -n 1)" > /etc/hostid
USER orthanc
