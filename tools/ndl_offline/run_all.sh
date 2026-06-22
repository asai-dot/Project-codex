#!/usr/bin/env bash
# ローカルちゃん用オーケストレータ。機械処理は全部この中。
# 使い方:  bash run_all.sh "<NDLダンプのフォルダ>"
# 例:      bash run_all.sh "$HOME/Library/CloudStorage/Box-Box/.../NDL_書誌情報_raw"
set -euo pipefail
cd "$(dirname "$0")"

DUMP_DIR="${1:-}"
if [ -z "$DUMP_DIR" ]; then
  echo "使い方: bash run_all.sh \"<NDLダンプのフォルダ>\""; exit 2
fi
if [ ! -d "$DUMP_DIR" ]; then
  echo "!! フォルダが見つからない: $DUMP_DIR"; exit 2
fi

echo "=== STEP 1/3: R1 probe（スキーマ/inventory/hash）==="
python3 r1_probe.py "$DUMP_DIR"

echo
echo ">>> ここで out/R1_probe_report.md を一度見てください。"
echo ">>> isbn / ndl_bib_id 列が正しく検出されていれば Enter。違えば Ctrl-C して"
echo ">>> out/R1_schema_map.json の column_roles を手で直してから再実行。"
read -r _

echo "=== STEP 2/3: R2 build index（ISBN→bibid 索引・約16GBストリーム）==="
python3 r2_build_index.py "$DUMP_DIR"

echo "=== STEP 3/3: R3 coverage（cohort-A 被覆・候補）==="
python3 r3_coverage.py

echo
echo "=== 完了。out/ の下記を浅井さん/監査へ戻してください ==="
echo "  R1_probe_report.md / R1_inventory.json"
echo "  R2_build_manifest.json / R2_rejects.tsv（先頭だけでOK）"
echo "  R3_coverage_report.md / cohortA_isbn_candidates.tsv"
echo "※ ndl_isbn_index.tsv とダンプ原本は外部に出さない（external_egress=prohibited）。"
