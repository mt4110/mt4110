#!/usr/bin/env bash
# グループ用トピックを各公開リポジトリへ付けるワンショットスクリプト。
# CI からは呼ばない。オーナーが手元で実行する。
# 引数なしは dry-run。実際に付けるときだけ: ./apply-topics.sh --apply
#
# 必要: python3。--check / --apply には github.com への gh ログインも必要。
# 既存のトピックは消さない（--add-topic のみ）。
# bash 3.2（macOS の /bin/bash）でも動く。

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
CONFIG="${ROOT}/groups.yml"
MODE=dry-run

if [[ "$#" -gt 1 ]]; then
  echo "Expected at most one argument." >&2
  exit 2
elif [[ "${1:-}" == "--apply" ]]; then
  MODE=apply
elif [[ "${1:-}" == "--check" ]]; then
  MODE=check
elif [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: $0 [--check|--apply]"
  echo "  引数なし   付ける予定の topic を表示するだけ（APIは変更しない）"
  echo "  --check    GitHub の状態を読み取り、変更予定を表示する（書き込みなし）"
  echo "  --apply    同じ確認のあと、必要な Topic のみ付ける"
  exit 0
elif [[ "${1:-}" != "" ]]; then
  echo "unknown argument: $1" >&2
  exit 2
fi

if ! command -v python3 >/dev/null; then
  echo "python3 が必要です" >&2
  exit 1
fi

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

# groups.yml の assignments を "owner/repo<TAB>topic" で出す。
python3 - "$CONFIG" > "$TMP" << 'PY'
import sys
from pathlib import Path
import importlib.util
config_path = Path(sys.argv[1]).resolve()
script = config_path.parent / "scripts" / "update_readme.py"
spec = importlib.util.spec_from_file_location("update_readme", script)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
cfg = mod.load_config(config_path)
owner = cfg["owner"]
for item in cfg.get("assignments") or []:
    print(f"{owner}/{item['repo']}\t{item['topic']}")
PY

LINES=()
while IFS= read -r line || [[ -n "$line" ]]; do
  [[ -z "$line" ]] && continue
  LINES+=("$line")
done < "$TMP"

if [[ ${#LINES[@]} -eq 0 ]]; then
  echo "assignments が空です: ${CONFIG}" >&2
  exit 1
fi

echo "対象 ${#LINES[@]} 件（config: ${CONFIG}）"
if [[ "$MODE" == dry-run ]]; then
  echo "dry-run です。変更しません。GitHub の状態も確認するには ./apply-topics.sh --check"
  echo
fi

if [[ "$MODE" != dry-run ]]; then
  if ! command -v gh >/dev/null; then
    echo "gh が必要です" >&2
    exit 1
  fi
  if ! login="$(gh api --hostname github.com user --jq .login)"; then
    echo "Could not verify GitHub account on github.com. No changes made." >&2
    exit 1
  fi
  if [[ "$login" != mt4110 ]]; then
    echo "Expected GitHub account mt4110." >&2
    exit 1
  fi
fi

# Read and validate every target before making any changes.
PENDING=()
for line in "${LINES[@]}"; do
  repo="${line%%$'\t'*}"
  topic="${line#*$'\t'}"
  if [[ "$MODE" == dry-run ]]; then
    printf '%s -> %s (live checks on --check or --apply)\n' "$repo" "$topic"
    continue
  fi
  metadata="$(gh api --hostname github.com "repos/${repo}" --jq '[.full_name, .visibility, (.fork|tostring), (.archived|tostring), ((.permissions.admin // false)|tostring), ((.topics // [])|join(","))] | join("|")')" || {
    echo "Could not read github.com/$repo. No changes made." >&2
    exit 1
  }
  IFS='|' read -r canonical visibility fork archived admin topics <<< "$metadata"
  if [[ "$canonical" != "$repo" || "$visibility" != public || "$fork" != false ]]; then
    echo "Refusing to edit invalid target: $repo" >&2
    exit 1
  fi
  if [[ "$archived" == true ]]; then
    echo "Skipping archived repository: $repo"
    continue
  fi
  if [[ "$archived" != false || "$admin" != true || "$topic" == group-archive ]]; then
    echo "Refusing to edit unexpected target: $repo" >&2
    exit 1
  fi
  already=0
  IFS=',' read -r -a existing <<< "$topics"
  for t in ${existing[@]+"${existing[@]}"}; do
    if [[ "$t" == "$topic" ]]; then
      already=1
    elif [[ "$t" == group-* ]]; then
      echo "Conflicting group topic on $repo: $t" >&2
      exit 1
    fi
  done
  if [[ "$already" -eq 1 ]]; then
    echo "Already assigned: $repo"
    continue
  fi
  if [[ "$MODE" == check ]]; then
    echo "Would add $topic -> github.com/$repo"
  fi
  PENDING+=("$line")
done
if [[ "$MODE" != apply ]]; then
  if [[ "$MODE" == check ]]; then
    echo "Preflight passed. No changes made."
  fi
  exit 0
fi
for line in ${PENDING[@]+"${PENDING[@]}"}; do
  repo="${line%%$'\t'*}"
  topic="${line#*$'\t'}"
  echo "adding $topic -> $repo"
  gh repo edit "https://github.com/$repo" --add-topic "$topic" || {
    echo "Stopped at $repo. Prior successful changes are retained; recheck before retrying." >&2
    exit 1
  }
done
