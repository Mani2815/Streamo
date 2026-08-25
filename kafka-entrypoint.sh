#!/bin/bash
# Dynamically advertise the exact routable URL assigned by Render
export KAFKA_ADVERTISED_LISTENERS="PLAINTEXT://${RENDER_DISCOVERY_SERVICE}"
exec /etc/confluent/docker/run
