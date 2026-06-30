#!/usr/bin/env bash
# test_head_owner_log_gate.sh — head_owner_log_gate.py の自己検証(ACCEPT + 7 reject + alias lint)
# 実 git の祖先判定を使うため、本 repo の HEAD(=HEAD_OWNER_LOG を持つ commit)とその親を利用する。
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GATE="$HERE/tools/head_owner_log_gate.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

HEAD_C="$(git -C "$HERE" rev-parse HEAD)"
PARENT_C="$(git -C "$HERE" rev-parse HEAD~1)"
DIG="HOL-20260630-001"
# seed の active global_required
GREQ="[HOS-001, HOS-002, HOS-003, HOS-005]"

pass=0; fail=0
run() { # name expected_exit expected_substr orch result [extra...]
  local name="$1" exp_exit="$2" exp_sub="$3" orch="$4" res="$5"; shift 5
  local out rc
  out="$(python3 "$GATE" --orch "$orch" --result "$res" --repo "$HERE" "$@" 2>&1)"; rc=$?
  if [ "$rc" = "$exp_exit" ] && echo "$out" | grep -q "$exp_sub"; then
    echo "  PASS  $name (exit=$rc, '$exp_sub')"; pass=$((pass+1))
  else
    echo "  FAIL  $name (exit=$rc want=$exp_exit; want_substr='$exp_sub')"; echo "        out: $out"; fail=$((fail+1))
  fi
}

mkorch() { printf 'required_log_commit: %s\nrequired_digest_id: %s\nrequired_standing_ids: %s\n%s\n' "$1" "$2" "$3" "${4:-}" ; }
mkres()  { printf 'read_log_commit: %s\nread_digest_id: %s\nread_standing_ids: %s\n' "$1" "$2" "$3" ; }

# ACCEPT
mkorch "$HEAD_C" "$DIG" "$GREQ" > "$TMP/o_ok.md"
mkres  "$HEAD_C" "$DIG" "$GREQ" > "$TMP/r_ok.md"
run "ACCEPT" 0 "ACCEPT" "$TMP/o_ok.md" "$TMP/r_ok.md"

# 1 MISSING_DIGEST (read に digest 無し)
printf 'read_log_commit: %s\nread_standing_ids: %s\n' "$HEAD_C" "$GREQ" > "$TMP/r_miss.md"
run "MISSING_DIGEST" 1 "REJECT_MISSING_DIGEST" "$TMP/o_ok.md" "$TMP/r_miss.md"

# 2 STALE_DIGEST
mkres "$HEAD_C" "HOL-20260629-001" "$GREQ" > "$TMP/r_staled.md"
run "STALE_DIGEST" 1 "REJECT_STALE_DIGEST" "$TMP/o_ok.md" "$TMP/r_staled.md"

# 3 STALE_LOG_COMMIT (read が古い親 commit)
mkres "$PARENT_C" "$DIG" "$GREQ" > "$TMP/r_oldc.md"
run "STALE_LOG_COMMIT" 1 "REJECT_STALE_LOG_COMMIT" "$TMP/o_ok.md" "$TMP/r_oldc.md"

# 4 STANDING_UNREAD (read が HOS-001 を欠く)
mkres "$HEAD_C" "$DIG" "[HOS-002, HOS-003, HOS-005]" > "$TMP/r_unread.md"
run "STANDING_UNREAD" 1 "REJECT_STANDING_UNREAD" "$TMP/o_ok.md" "$TMP/r_unread.md"

# 5 REQUIRED_STANDING_OMITTED (ORCH が global_required HOS-005 を入れ忘れ)
mkorch "$HEAD_C" "$DIG" "[HOS-001, HOS-002, HOS-003]" > "$TMP/o_omit.md"
mkres  "$HEAD_C" "$DIG" "[HOS-001, HOS-002, HOS-003]" > "$TMP/r_omit.md"
run "REQUIRED_STANDING_OMITTED" 1 "REJECT_REQUIRED_STANDING_OMITTED" "$TMP/o_omit.md" "$TMP/r_omit.md"

# 6 STANDING_OVERFLOW (--log で active 21件の合成ログ)
{ for i in $(seq -w 1 21); do printf -- '- standing_id: HOS-9%s\n  applies_to: x | enforcement: task_scoped | status: active\n' "$i"; done; } > "$TMP/log_over.md"
run "STANDING_OVERFLOW" 1 "REJECT_STANDING_OVERFLOW" "$TMP/o_ok.md" "$TMP/r_ok.md" --log "$TMP/log_over.md"

# 7 INLINE_HISTORY (会話 inline 6行)
{ mkorch "$HEAD_C" "$DIG" "$GREQ"; for i in 1 2 3; do printf 'owner: ...\nhead: ...\n'; done; } > "$TMP/o_inline.md"
run "INLINE_HISTORY" 1 "REJECT_INLINE_HISTORY" "$TMP/o_inline.md" "$TMP/r_ok.md"

# 8 LINT_FIELD_ALIAS (旧 field 名)
printf 'required_log_commit: %s\ncontext_log_digest_id: %s\n' "$HEAD_C" "$DIG" > "$TMP/o_alias.md"
run "LINT_FIELD_ALIAS" 2 "LINT_FIELD_ALIAS" "$TMP/o_alias.md" "$TMP/r_ok.md"

echo ""
echo "RESULT: pass=$pass fail=$fail"
[ "$fail" = 0 ]
