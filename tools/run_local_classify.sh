#!/usr/bin/env bash
# run_local_classify.sh — ORCH-LOCAL-ARTICLE-TYPE をローカルちゃん(QEN)で実行するドライバ。
#   input(article_id,title) を CHUNK 行ずつに切り分け、各チャンクを dispatch_local.sh で QEN に投入し結合。
#   使い方(Mac): OLLAMA_MODEL=<QENモデル> ./tools/run_local_classify.sh
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$REPO" || exit 1
IN="artifacts/periodical/article_join_dryrun_v0.1.csv"
OUT="artifacts/periodical/article_type_local_v0.1.csv"
WORK="$(mktemp -d)"; CHUNK="${CHUNK:-400}"
PROMPT='次の各行は タブ区切りで id<TAB>タイトル。各行をちょうど1つの種別に分類し、id<TAB>種別 だけを1行ずつ返せ。種別は次のいずれかの語そのもの: 判例評釈,論説・論文,解説,立法・改正解説,座談会・対談,判例紹介,書評,資料,連載・コラム,その他。迷ったら その他。説明文は出力しない。'

[ -f "$IN" ] || { echo "入力なし: $IN（git pull 済か確認）" >&2; exit 2; }
# article_id(1列目), title(末尾列) を id<TAB>title へ。CSVヘッダ位置に依存しないようpythonで抽出。
python3 - "$IN" "$WORK/ids.tsv" <<'PY'
import csv,sys
rd=csv.DictReader(open(sys.argv[1],encoding="utf-8"))
with open(sys.argv[2],"w",encoding="utf-8") as w:
    for r in rd:
        aid=(r.get("article_id") or "").strip(); t=(r.get("title") or "").replace("\t"," ").strip()
        if aid and t: w.write(f"{aid}\t{t}\n")
PY
total=$(wc -l < "$WORK/ids.tsv"); echo "[classify] 対象 $total 行, $CHUNK 行/チャンク, model=${OLLAMA_MODEL:-qwen2.5}"
split -l "$CHUNK" "$WORK/ids.tsv" "$WORK/c_"
: > "$OUT.tmp"; n=0
for f in "$WORK"/c_*; do
  n=$((n+1)); echo "[classify] chunk $n ($(wc -l <"$f")行)"
  ./tools/dispatch_local.sh "$PROMPT" "$f" >> "$OUT.tmp" 2>/dev/null || echo "[classify] chunk $n 失敗(継続)"
done
# 正規化: 'id<TAB>type' 行だけ拾い、ヘッダ付与
{ echo "article_id,type,source"; grep -P '^\S+\t\S+' "$OUT.tmp" | awk -F'\t' '{print $1","$2",qen"}'; } > "$OUT"
echo "[classify] 出力 $OUT ($(($(wc -l <"$OUT")-1))行)。commit/push して head監査へ。"
rm -rf "$WORK"
