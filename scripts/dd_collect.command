#!/usr/bin/env bash
# DD パイプライン snapshot を採取 → 描画 → コミットする (Mac 番頭/ワーカー用)。
#
# 実フォルダ (Box 同期 / ~/alo-ai) を走査できる **Mac で実行**する。Finder で
# ダブルクリックすると Terminal が開いて走る (拡張子 .command)。CLI なら:
#   bash scripts/dd_collect.command            # 採取→描画→コミット
#   bash scripts/dd_collect.command --push     # さらに push まで
#   bash scripts/dd_collect.command --no-commit # 採取→描画のみ (試走)
#
# root は環境変数で上書き可 (無い root のステージは todo 表示になるだけで落ちない):
#   ALO_BOOKDX_ROOT  Box 同期の「事務所内本棚DX化計画」フォルダ実パス
#   ALO_ALO_ROOT     ~/alo-ai (既定)
#
# 出力する snapshot は **tracked パス** (build/ は .gitignore のため):
#   pipeline/pipeline_snapshot.json   ← これを日次でコミットすると差分=進捗の動きが追える
# ローカル閲覧用の HTML/MD は build/ (コミットされない)。
set -euo pipefail

DO_COMMIT=1
DO_PUSH=0
for a in "$@"; do
  case "$a" in
    --no-commit) DO_COMMIT=0 ;;
    --push)      DO_PUSH=1 ;;
    -h|--help)   sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown arg: $a (--push / --no-commit / --help)"; exit 2 ;;
  esac
done

# スクリプト位置からリポジトリ root へ (ダブルクリック時の cwd に依存しない)。
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

MANIFEST="pipeline/pipeline.json"
SNAPSHOT="pipeline/pipeline_snapshot.json"

PY="$(command -v python3 || command -v python)"
[ -n "$PY" ] || { echo "❌ python が見つかりません"; exit 1; }

# 存在する root だけ渡す。
ROOT_ARGS=(--root "repo=$REPO_ROOT")

ALO_ROOT="${ALO_ALO_ROOT:-$HOME/alo-ai}"
if [ -d "$ALO_ROOT" ]; then
  ROOT_ARGS+=(--root "alo=$ALO_ROOT")
else
  echo "⚠ alo root 無し: $ALO_ROOT (動的DB系ステージは todo 表示)"
fi

# bookdx は環境ごとにパスが違うので env 優先、無ければ典型パスを探索。
BOOKDX_ROOT="${ALO_BOOKDX_ROOT:-}"
if [ -z "$BOOKDX_ROOT" ]; then
  for cand in \
    "$HOME/Library/CloudStorage/Box-Box/浅井/claude/事務所内本棚DX化計画" \
    "$HOME/Box/浅井/claude/事務所内本棚DX化計画" \
    "$HOME/Box/事務所内本棚DX化計画"; do
    [ -d "$cand" ] && { BOOKDX_ROOT="$cand"; break; }
  done
fi
if [ -n "$BOOKDX_ROOT" ] && [ -d "$BOOKDX_ROOT" ]; then
  ROOT_ARGS+=(--root "bookdx=$BOOKDX_ROOT")
else
  echo "⚠ bookdx root 無し (ALO_BOOKDX_ROOT で指定可)。静的DB系ステージは todo 表示。"
fi

echo "▶ snapshot 収集 … roots: ${ROOT_ARGS[*]}"
# collect() が manifest を検証→不正なら exit 1 で止まる (描画/コミットへ進ませない)。
"$PY" scripts/pipeline_probe.py --manifest "$MANIFEST" "${ROOT_ARGS[@]}" --out "$SNAPSHOT"

mkdir -p build
"$PY" scripts/pipeline_dashboard.py --manifest "$MANIFEST" --snapshot "$SNAPSHOT" \
  --out-md build/dashboard.md --out-html build/dashboard.html
echo "▶ 画面: $REPO_ROOT/build/dashboard.html"

if [ "$DO_COMMIT" -eq 1 ]; then
  if git diff --quiet -- "$SNAPSHOT" && git ls-files --error-unmatch "$SNAPSHOT" >/dev/null 2>&1; then
    echo "= snapshot に変更なし (コミットしません)"
  else
    git add "$SNAPSHOT"
    git commit -q -m "dd snapshot: $(date '+%Y-%m-%d %H:%M') 採取"
    echo "✓ コミット: $SNAPSHOT"
    if [ "$DO_PUSH" -eq 1 ]; then
      BRANCH="$(git rev-parse --abbrev-ref HEAD)"
      git push -u origin "$BRANCH"
      echo "✓ push: $BRANCH"
    fi
  fi
fi

# Mac なら画面を開く。
command -v open >/dev/null 2>&1 && open build/dashboard.html || true
