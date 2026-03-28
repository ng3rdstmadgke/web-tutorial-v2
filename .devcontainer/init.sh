#!/bin/bash

mkdir -p ~/.ssh
mkdir -p ~/.aws
mkdir -p ~/.web-tutorial-v2/.claude
[ ! -f ~/.web-tutorial-v2/.claude.json ] && echo '{}' > ~/.web-tutorial-v2/.claude.json
mkdir -p ~/.web-tutorial-v2/.gemini
mkdir -p ~/.web-tutorial-v2/.kube
mkdir -p ~/.web-tutorial-v2/.config/helm

DOCKER_NETWORK=br-web-tutorial-v2-${USER}
NETWORK_EXISTS=$(docker network ls --filter name=$DOCKER_NETWORK --format '{{.Name}}')

if [ -z "$NETWORK_EXISTS" ]; then
  docker network create $DOCKER_NETWORK
fi