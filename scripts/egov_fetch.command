#!/usr/bin/env bash
# e-Gov 条文各号を read-only 取得する (Mac 番頭/owner 用・ダブルクリック1発)。
#
# やること: 作業ブランチに合わせる → 最新化 → _targets.json の対象を取得 →
#           raw + 各号 anchor を保存 → そのまま push。**人手のコピペ不要**。
# Finder でダブルクリック (拡張子 .command) すると Terminal が開いて走る。CLI なら:
#   bash scripts/egov_fetch.command            # 取得→commit→push まで
#   bash scripts/egov_fetch.command --no-push  # 取得→commit のみ (push しない)
#   bash scripts/egov_fetch.command --dry       # 取得のみ (commit しない・数字だけ見る)
#
# 取得対象を増やすには pipeline/egov_raw/_targets.json に {law_id,article,paragraph,out} を足す。
# read-only(GET)のみ。法令構造は e-Gov 正本を consume、こちらは last-mile(anchor 正規化)だけ。
set -euo pipefail

BRANCH="claude/pipeline-collect-validation-EnNJM"
MODE="push"
for a in "$@"; do
  case "$a" in
    --no-push) MODE="commit" ;;
    --dry) MODE="dry" ;;
  esac
done

# リポルートへ (このスクリプトは scripts/ 配下)。
cd "$(dirname "$0")/.." || { echo "リポルートに移動できません"; exit 1; }

echo "▶ ブランチを $BRANCH に合わせて最新化…"
git stash -q 2>/dev/null || true
git checkout -q "$BRANCH"
git pull -q --ff-only origin "$BRANCH" || {
  echo "⚠ fast-forward できません。ローカルが分岐しています。出力を番頭に貼ってください。"; exit 1; }

echo "▶ e-Gov 取得 (read-only)…"
python3 scripts/egov_fetch.py --targets pipeline/egov_raw/_targets.json \
    --raw-dir pipeline/egov_raw --out pipeline/egov_raw

if [ "$MODE" = "dry" ]; then
  echo "✅ 取得のみ (--dry)。commit/push はしていません。"
  exit 0
fi

if git diff --quiet -- pipeline/egov_raw && git diff --cached --quiet -- pipeline/egov_raw; then
  echo "ℹ 変更なし (前回と同じ)。commit しません。"
  exit 0
fi

git add pipeline/egov_raw
git commit -q -m "e-Gov raw + 各号 anchor 取得 (egov_fetch.command)"
echo "✅ commit 済。"
if [ "$MODE" = "push" ]; then
  git push -q && echo "✅ push 済 ($BRANCH)。番頭が後続(床突合)を引き取れます。"
else
  echo "ℹ --no-push 指定。push は手動で: git push"
fi
