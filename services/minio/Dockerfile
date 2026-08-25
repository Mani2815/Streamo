FROM minio/mc:RELEASE.2025-08-13T08-35-41Z as mc

FROM minio/minio:RELEASE.2024-03-30T09-41-56Z

COPY --from=mc /usr/bin/mc /usr/local/bin/mc
COPY entrypoint.sh /entrypoint.sh

# Change to root to change permissions, then back if needed.
# minio image usually runs as root by default anyway or has root perms to chmod.
USER root
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
