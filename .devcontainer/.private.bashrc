#!/bin/bash

source <(docker completion bash)
source <(kubectl completion bash)
source <(helm completion bash)
complete -C '/usr/local/bin/aws_completer' aws

source <(uv generate-shell-completion bash)
source <(uvx --generate-shell-completion bash)

PATH="$PATH:$PROJECT_DIR/bin"

export AWS_REGION=ap-northeast-1
export AWS_DEFAULT_REGION=ap-northeast-1

# 共通のセットアップスクリプトを実行
source ${PROJECT_DIR}/.devcontainer/conf/common/setup.sh

# .devcontainer/.envのexport
if [ -f "${PROJECT_DIR}/.devcontainer/.env" ]; then
  envs=$(cat ${PROJECT_DIR}/.devcontainer/.env | grep -v -e "^$" -e "^ *#" | sed -e "s| *#.*$||" | xargs)
  if [ -n "$envs" ]; then
    export $envs
  fi
fi

# pnpm
export PNPM_HOME="${HOME}/.local/share/pnpm"
case ":$PATH:" in
  *":$PNPM_HOME:"*) ;;
  *) export PATH="$PNPM_HOME:$PATH" ;;
esac