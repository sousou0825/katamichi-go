#!/bin/bash
# seen.json と new_items.log をコミットして push する．
# Mac と GitHub Actions が同時に push して衝突したら，両方の内容を合わせてやり直す．
set -eu
cd "$(dirname "$0")"
files="seen.json"; [ -f new_items.log ] && files="$files new_items.log"
git add $files
git diff --cached --quiet && exit 0
git commit -qm "update seen"
for i in 1 2 3; do
  git push -q && exit 0
  tmp=$(mktemp -d)
  cp $files "$tmp/"
  git fetch -q && git reset -q --hard origin/main
  python3 - "$tmp" <<'PY'
import json, sys
from pathlib import Path
tmp = Path(sys.argv[1])
seen = set(json.loads(Path("seen.json").read_text())) | set(json.loads((tmp / "seen.json").read_text()))
Path("seen.json").write_text(json.dumps(sorted(seen), ensure_ascii=False, indent=1))
if (tmp / "new_items.log").exists():
    old = Path("new_items.log").read_text().splitlines() if Path("new_items.log").exists() else []
    lines = sorted(set(old) | set((tmp / "new_items.log").read_text().splitlines()))
    Path("new_items.log").write_text("\n".join(lines) + "\n")
PY
  rm -rf "$tmp"
  git add seen.json; [ -f new_items.log ] && git add new_items.log
  git commit -qm "update seen (merge)"
done
exit 1
