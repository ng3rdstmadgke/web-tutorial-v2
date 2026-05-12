#!/bin/bash
function usage {
cat >&2 <<EOS
このプロジェクトの devcontainer に bash でログインします。
ホスト側のターミナルから実行してください。
日本語の入力・表示のため LANG=ja_JP.UTF-8 を渡します。

[usage]
  $0 [options]

[options]
 -h | --help:
   ヘルプを表示
 -u | --user <USER>:
   ログインユーザを指定 (デフォルト: vscode)
EOS
exit 1
}

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_FOLDER="$(cd "$SCRIPT_DIR/.." && pwd)"

CONTAINER_USER="vscode"
while [ "$#" != 0 ]; do
  case "$1" in
    -h | --help ) usage ;;
    -u | --user ) shift; CONTAINER_USER="$1" ;;
    *           ) echo "[error] $1 : 不正なオプションです" >&2; usage ;;
  esac
  shift
done

command -v docker >/dev/null 2>&1 || {
  echo "[error] docker コマンドが見つかりません" >&2
  exit 1
}

# devcontainer は devcontainer.local_folder ラベルにホスト側のワークスペースパスを持つ。
# このスクリプトの親ディレクトリ (= ホスト側のワークスペースパス) で起動中コンテナを引き当てる。
CONTAINER_ID="$(docker ps -q --filter "label=devcontainer.local_folder=$WORKSPACE_FOLDER" | head -n 1)"

if [ -z "$CONTAINER_ID" ]; then
  echo "[error] 起動中の devcontainer が見つかりません" >&2
  echo "        local_folder=$WORKSPACE_FOLDER" >&2
  echo "        VS Code で devcontainer を開いてから再実行してください。" >&2
  exit 1
fi

# devcontainer 側の PROJECT_DIR を作業ディレクトリとする (containerEnv で設定済み)
WORKDIR_OPT=()
PROJECT_DIR_IN_CONTAINER="$(docker exec "$CONTAINER_ID" printenv PROJECT_DIR 2>/dev/null | tr -d '\r' || true)"
[ -n "$PROJECT_DIR_IN_CONTAINER" ] && WORKDIR_OPT=(-w "$PROJECT_DIR_IN_CONTAINER")

exec docker exec -it \
  -u "$CONTAINER_USER" \
  "${WORKDIR_OPT[@]}" \
  -e LANG=ja_JP.UTF-8 \
  -e LC_ALL=ja_JP.UTF-8 \
  -e LANGUAGE=ja_JP \
  "$CONTAINER_ID" \
  bash