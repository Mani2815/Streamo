#!/bin/sh

# Start minio in the background
minio server /data --console-address ":9001" &
MINIO_PID=$!

# Wait for MinIO to start up
sleep 5

# Initialize buckets using mc
mc alias set streamo http://127.0.0.1:9000 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD}
mc mb streamo/streamo-raw || true
mc mb streamo/streamo-processed || true
mc mb streamo/streamo-quarantine || true

# Bring minio process back to foreground
wait $MINIO_PID
