#!/bin/bash


docker rm -f ${PROJECT_NAME}-headroom-${HOST_USER}
docker run -d \
  --name ${PROJECT_NAME}-headroom-${HOST_USER} \
  --network $DOCKER_NETWORK \
  ghcr.io/chopratejas/headroom:latest

echo "export ANTHROPIC_BASE_URL=${PROJECT_NAME}-headroom-${HOST_USER}:8787"