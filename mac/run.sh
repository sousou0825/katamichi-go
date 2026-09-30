#!/bin/bash
# Mac の launchd から1分ごとに呼ばれる．最新の seen.json を取ってから確認し，結果を GitHub に保存する．
set -eu
export PATH=/opt/homebrew/bin:/usr/bin:/bin
cd "$(dirname "$0")/.."
git fetch -q && git reset -q --hard origin/main
export NTFY_TOPIC=$(/usr/bin/python3 -c 'import json,os;print(json.load(open(os.path.expanduser("~/Library/Application Support/katamichi-go/config.json")))["ntfy_topic"])')
/usr/bin/python3 check.py
./sync.sh
