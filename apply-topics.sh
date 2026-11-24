#!/usr/bin/env bash
# グループ用トピックを各公開リポジトリへ付けるワンショットスクリプト。
# CI からは呼ばない。オーナーが手元で実行する。
# 引数なしは dry-run。実際に付けるときだけ: ./apply-topics.sh --apply
#
# 必要: python3。--apply のときだけ gh にログインしていること（gh auth status）。
# 既存のトピックは消さない（--add-topic のみ）。
# bash 3.2（macOS の /bin/bash）でも動く。

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
CONFIG="${ROOT}/groups.yml"
APPLY=0

if [[ "${1:-}" == "--apply" ]]; then
  APPLY=1
elif [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: $0 [--apply]"
  echo "  引数なし   付ける予定の topic を表示するだけ（APIは変更しない）"
  echo "  --apply    gh repo edit --add-topic を実行する"
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
if [[ "$APPLY" -eq 0 ]]; then
  echo "dry-run です。変更しません。実行するときは ./apply-topics.sh --apply"
  echo
fi

if [[ "$APPLY" -eq 1 ]]; then
  if ! command -v gh >/dev/null; then
    echo "gh が必要です" >&2
    exit 1
  fi
  if ! gh auth status >/dev/null 2>&1; then
    echo "gh にログインしてから再実行してください（gh auth login）" >&2
    exit 1
  fi
  if [[ "$(gh api user --jq .login)" != mt4110 ]]; then
    echo "Expected GitHub account mt4110." >&2
    exit 1
  fi
fi

# Read and validate every target before making any changes.
PENDING=()
for line in "${LINES[@]}"; do
  repo="${line%%$'\t'*}"
  topic="${line#*$'\t'}"
  if [[ "$APPLY" -eq 0 ]]; then
    printf '%s -> %s (live checks on --apply)\n' "$repo" "$topic"
    continue
  fi
  metadata="$(gh api "repos/${repo}" --jq '[.full_name, .visibility, (.fork|tostring), (.archived|tostring), ((.permissions.admin // false)|tostring), ((.topics // [])|join(","))] | join("|")')" || exit 1
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
  PENDING+=("$line")
done
if [[ "$APPLY" -eq 0 ]]; then
  exit 0
fi
for line in ${PENDING[@]+"${PENDING[@]}"}; do
  repo="${line%%$'\t'*}"
  topic="${line#*$'\t'}"
  echo "adding $topic -> $repo"
  gh repo edit "$repo" --add-topic "$topic" || {
    echo "Stopped at $repo. Prior successful changes are retained; recheck before retrying." >&2
    exit 1
  }
done
