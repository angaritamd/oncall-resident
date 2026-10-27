# Orthanc pinned by digest, running as the image's unprivileged "orthanc" user.
FROM orthancteam/orthanc:26.9.1@sha256:d2705f2c56547e55ce9bc2250fd22d05d326493b3f3d9fa191ecb7db8ca6b5a2
USER root
# a fresh named volume inherits this ownership
RUN mkdir -p /var/lib/orthanc/db && chown -R orthanc:orthanc /var/lib/orthanc/db \
 # the entrypoint writes a random /etc/hostid when missing; do it at build time so the root fs can be read-only.
 # gethostid() reads 4 raw bytes; it only seeds DCMTK UID generation (one Orthanc per image here).
 && head -c4 /dev/urandom > /etc/hostid \
 # enable plugins in the image: the entrypoint skips plugin files that already exist, so nothing is written
 # at runtime and no directory is both writable and executable
 && for lib in libOrthancDicomWeb.so libOrthancGdcm.so libOrthancExplorer2.so; do \
      cp /usr/share/orthanc/plugins-available/$lib /usr/share/orthanc/plugins/$lib; \
    done
USER orthanc
