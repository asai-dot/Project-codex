#!/usr/bin/env bash
# ②真ゼロ誌を「別表記候補」でリトライする（Mac側・owner_sanction W-20260626-010 範囲内）。
#   入力: /tmp/d1_triage.tsv の bucket=true_zero（無ければ候補TSVの original 全部）
#         + tools/d1_bunken/truezero_retry_candidates.tsv（手当て候補）
#   各誌の候補を左から試し、総件数>0 が出たら採用してその誌は打ち切り。全候補0なら「非収録確定」。
#   追加のみ・冪等（downloader 側でページスキップ）。bash 3.2(macOS既定) 互換。
set -uo pipefail
DL="${D1_DL:-$HOME/.gemini/antigravity/scratch/d1_bunken_downloader.py}"
REPO="${ALO_REPO:-$HOME/Project-codex}"
CAND="$REPO/tools/d1_bunken/truezero_retry_candidates.tsv"
TRIAGE="${D1_TRIAGE:-/tmp/d1_triage.tsv}"
LOG="${D1_RETRY_LOG:-/tmp/d1_retry_truezero.log}"; : > "$LOG"

lookup(){ awk -F'\t' -v k="$1" '!/^#/ && $1==k {print $2}' "$CAND"; }

try_one(){  # $1=候補表記 → 総件数>0 なら 0(成功)
  echo "  → try: $1" | tee -a "$LOG"
  out=$(python3 -u "$DL" "$1" 0 2>&1)
  echo "$out" | grep -E "総件数|完了|Timeout|失敗" | sed 's/^/     /' | tee -a "$LOG"
  echo "$out" | grep -q "総件数=[1-9]"
}

if [ -f "$TRIAGE" ]; then
  awk -F'\t' '$1=="true_zero"{print $2}' "$TRIAGE" > /tmp/_d1_tz.txt
else
  echo "（$TRIAGE 無し→候補TSVの original 全部を対象）" | tee -a "$LOG"
  awk -F'\t' '!/^#/{print $1}' "$CAND" > /tmp/_d1_tz.txt
fi

while IFS= read -r j; do
  [ -z "$j" ] && continue
  echo "### $j" | tee -a "$LOG"
  cands=$(lookup "$j")
  [ -z "$cands" ] && cands=$(printf '%s' "$j" | sed -E 's/[〔「『（(].*$//')
  rm -f /tmp/_d1_hit
  printf '%s\n' "$cands" | tr '|' '\n' | while IFS= read -r c; do
    c=$(printf '%s' "$c" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')
    [ -z "$c" ] && continue
    if try_one "$c"; then echo "  ✅ HIT: $c" | tee -a "$LOG"; echo "$c" > /tmp/_d1_hit; break; fi
  done
  [ -f /tmp/_d1_hit ] || echo "  ❌ 全候補0 → 非収録確定" | tee -a "$LOG"
done < /tmp/_d1_tz.txt
echo "RETRY_DONE" | tee -a "$LOG"
echo "ログ: $LOG"
