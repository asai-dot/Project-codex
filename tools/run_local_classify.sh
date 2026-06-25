#!/usr/bin/env bash
# run_local_classify.sh — ORCH-LOCAL-ARTICLE-TYPE をローカルちゃん(QEN)で実行するドライバ。
#   input(article_id,title) を CHUNK 行ずつに切り分け、各チャンクを dispatch_local.sh で QEN に投入し結合。
#   使い方(Mac): OLLAMA_MODEL=<QENモデル> ./tools/run_local_classify.sh
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$REPO" || exit 1
IN="artifacts/periodical/article_join_dryrun_v0.1.csv"
OUT="artifacts/periodical/article_type_local_v0.1.csv"
# CHUNK は1チャンクの行数。spec 既定は 400 だが、30bモデルは 400行だと出力が途中で
# 切れる実測（run-report 20260625）。30bで回す時は CHUNK=40〜50 を推奨（env で上書き）。
WORK="$(mktemp -d)"; CHUNK="${CHUNK:-400}"
PROMPT='次の各行は タブ区切りで id<TAB>タイトル。各行をちょうど1つの種別に分類し、id<TAB>種別 だけを1行ずつ返せ。種別は次のいずれかの語そのもの: 判例評釈,論説・論文,解説,立法・改正解説,座談会・対談,判例紹介,書評,資料,連載・コラム,その他。迷ったら その他。説明文は出力しない。'

[ -f "$IN" ] || { echo "入力なし: $IN（git pull 済か確認）" >&2; exit 2; }
# OLLAMA_MODEL 未指定なら ollama list から QEN を自動検出。
# 正規の「ローカルちゃん」は qwen3:30b（localchan-dispatch skill）。qwen2.5(7B) は分類が全件
# 「その他」へ倒れる実測があるため 30b を優先する（run-report 20260625 参照）。
if [ -z "${OLLAMA_MODEL:-}" ]; then
  _models="$(ollama list 2>/dev/null | awk 'NR>1{print $1}')"
  OLLAMA_MODEL="$(printf '%s\n' "$_models" | grep -iE 'qwen3.*30b|qwen.*30b' | head -1)"
  [ -z "$OLLAMA_MODEL" ] && OLLAMA_MODEL="$(printf '%s\n' "$_models" | grep -iE 'qwen3' | head -1)"
  [ -z "$OLLAMA_MODEL" ] && OLLAMA_MODEL="$(printf '%s\n' "$_models" | grep -iE 'qwen|qen' | head -1)"
  [ -z "$OLLAMA_MODEL" ] && OLLAMA_MODEL="qwen3:30b"
  export OLLAMA_MODEL; echo "[classify] モデル自動検出: $OLLAMA_MODEL（30b優先）"
fi
# article_id(1列目), title(末尾列) を id<TAB>title へ。CSVヘッダ位置に依存しないようpythonで抽出。
python3 - "$IN" "$WORK/ids.tsv" <<'PY'
import csv,sys
rd=csv.DictReader(open(sys.argv[1],encoding="utf-8"))
with open(sys.argv[2],"w",encoding="utf-8") as w:
    for r in rd:
        aid=(r.get("article_id") or "").strip(); t=(r.get("title") or "").replace("\t"," ").strip()
        if aid and t: w.write(f"{aid}\t{t}\n")
PY
# LIMIT を指定するとパイロット（先頭 N 行のみ）。例: LIMIT=2000 ./tools/run_local_classify.sh
if [ -n "${LIMIT:-}" ]; then head -n "$LIMIT" "$WORK/ids.tsv" > "$WORK/ids.head" && mv "$WORK/ids.head" "$WORK/ids.tsv"; OUT="artifacts/periodical/article_type_local_pilot_v0.1.csv"; echo "[classify] パイロット: 先頭 $LIMIT 行"; fi
total=$(wc -l < "$WORK/ids.tsv"); echo "[classify] 対象 $total 行, $CHUNK 行/チャンク, model=${OLLAMA_MODEL:-qwen2.5}"
split -l "$CHUNK" "$WORK/ids.tsv" "$WORK/c_"
: > "$OUT.tmp"; n=0
for f in "$WORK"/c_*; do
  n=$((n+1)); echo "[classify] chunk $n ($(wc -l <"$f")行)"
  ./tools/dispatch_local.sh "$PROMPT" "$f" >> "$OUT.tmp" 2>/dev/null || echo "[classify] chunk $n 失敗(継続)"
done
# 正規化: 'id<TAB>type' 行だけ拾い、ヘッダ付与。
# 注: macOS の BSD grep は -P(PCRE) 非対応のため、抽出・整形は awk 一本に統一（移植性）。
{ echo "article_id,type,source"; awk -F'\t' 'NF>=2{i=$1;t=$2;gsub(/^[ \t]+|[ \t]+$/,"",i);gsub(/^[ \t]+|[ \t]+$/,"",t);if(i!=""&&t!="")print i","t",qen"}' "$OUT.tmp"; } > "$OUT"
echo "[classify] 出力 $OUT ($(($(wc -l <"$OUT")-1))行)。commit/push して head監査へ。"
rm -rf "$WORK"
