#!/usr/bin/env bash
# STEP4 ワンライナー: 再パース → ラベルv0.2.1 → 0件トリアージ → カバレッジ差分。
# スイープ（と任意で retry_truezero.sh）が終わった後に Mac で1回流す。
# 追加生成のみ（元RTF/manifestは触らない）。bash 3.2 互換。
set -uo pipefail
HOME_="${HOME}"
BUILD="${D1_BUILD:-$HOME_/ALOBookDX/事務所内本棚DX化計画/build/d1_bunken_article_meta_20260611}"
META="$BUILD/article_meta_all.jsonl"
LABELED="$BUILD/labeled_v0.2.1/article_meta_labeled.jsonl"
PARSER="${D1_PARSER:-$HOME_/ALOBookDX/事務所内本棚DX化計画/scripts/d1_bunken_parse_all.py}"
REPO="${ALO_REPO:-$HOME_/Project-codex}"
SWEEPLOG="${D1_SWEEPLOG:-$HOME_/d1_full_sweep.log}"
CONTRACT="${D1_CONTRACT:-449677}"
BASELINE="${D1_BASELINE:-333206}"

echo "===== STEP4 (1/4) 再パース ====="
cd "$HOME_" && python3 -u "$PARSER"

echo "===== STEP4 (2/4) ラベル v0.2.1 ====="
cd "$REPO"
python3 tools/d1_bunken/label_journals_v0.2.1.py "$META"

echo "===== STEP4 (3/4) 0件トリアージ ====="
python3 tools/d1_bunken/triage_sweep_log.py "$SWEEPLOG" --tsv /tmp/d1_triage.tsv | tail -40

echo "===== STEP4 (4/4) カバレッジ差分 ====="
python3 - "$BUILD" "$LABELED" "$CONTRACT" "$BASELINE" <<'PY'
import json,sys,os,glob
build,labeled,contract,baseline=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4])
uniq=None
for c in sorted(glob.glob(os.path.join(build,"*summary*.json")))+[os.path.join(build,"summary.json")]:
    if os.path.exists(c):
        try:
            d=json.load(open(c)); uniq=d.get("unique_articles") or d.get("unique") or uniq
        except Exception: pass
if uniq is None and os.path.exists(labeled):
    uniq=sum(1 for _ in open(labeled))
canon=set()
if os.path.exists(labeled):
    for l in open(labeled):
        try: canon.add(json.loads(l).get("journal_canonical",""))
        except Exception: pass
canon.discard("")
if not uniq:
    print("！unique_articles を特定できず（summary.json も labeled も無し）。パース出力を確認。"); sys.exit(0)
pct=100*uniq/contract; bpct=100*baseline/contract
print(f"unique_articles : {baseline:,} → {uniq:,}   (+{uniq-baseline:,})")
print(f"カバレッジ       : {bpct:.1f}% → {pct:.1f}%   (+{pct-bpct:.1f}pt) / 契約 {contract:,}")
print(f"canonical 誌数   : {len(canon):,}")
print(f"残り             : {contract-uniq:,} 件 ({100-pct:.1f}%)")
PY
echo "===== STEP4 完了。RESULT を done/W-20260626-010_RESULT.md に転記して alo-worker complete ====="
