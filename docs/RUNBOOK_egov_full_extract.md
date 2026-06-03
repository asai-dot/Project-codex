# ローカルで全法令の法定定義（錨）をフル抽出する手順

クラウド側では Box から1ファイルずつ取るしかなく重い。**e-Gov 法令JSONがローカルにある環境
（alo-kg の raw コーパス等）で一括するのが正解**。このリポジトリの `phases/egov_definition_extract.py`
に `--dir` 一括モードを入れたので、1コマンドで回る。

---

## 0. 前提：このリポジトリを Mac に用意
```bash
cd ~/path/to/work
git clone <Project-codex の clone URL> Project-codex   # 既にあれば cd して pull
cd Project-codex
git fetch origin claude/gakuyo-headless-migrate-AuGAM
git checkout claude/gakuyo-headless-migrate-AuGAM
git pull origin claude/gakuyo-headless-migrate-AuGAM
python3 --version   # 3.8+ ならOK。標準ライブラリのみ。pip 不要
```

## 1. e-Gov 法令JSONのフォルダを特定する
Box の `egov_json`（alo-kg/raw 配下、158法令、ファイル名は `{law_id}_current.json`）を
**ローカルに持っている場所**を探す。alo-kg リポジトリを clone 済みなら、その中の raw フォルダ:
```bash
# 例: ファイル名パターンで探す（Mac）
find ~ -name '*_current.json' -path '*egov*' 2>/dev/null | head
# 見つかったディレクトリを控える。例:
#   ~/work/alo-kg/raw/egov_json/417AC0000000086_current.json ...
EGOV_DIR=~/work/alo-kg/raw/egov_json     # ← 自分の実パスに置き換え
ls "$EGOV_DIR"/*_current.json | wc -l    # 158 と出れば全揃い
```

### もしローカルに無い／一部しか無い場合
2通り。
- **(a) Box から取る**: Box Drive をマウントしているなら、その同期フォルダ内の
  `…/alo-kg/raw/egov_json` を `EGOV_DIR` に指定すればよい（実体はローカルにある）。
- **(b) e-Gov 法令APIから引き直す**（最新・確実）。law_id 一覧は本リポジトリの
  `data/egov/gakuyo_law_index.json` などにある。v2 JSON を law_id ごとに保存:
  ```bash
  mkdir -p "$EGOV_DIR"
  # law_id を1行ずつ書いた ids.txt を用意して:
  while read LID; do
    curl -s "https://laws.e-gov.go.jp/api/2/law_data/${LID}?response_format=json" \
      -o "$EGOV_DIR/${LID}_current.json"
    sleep 1   # 礼儀のためのウェイト
  done < ids.txt
  ```
  ※エンドポイント仕様は e-Gov 法令API v2 のドキュメント参照。取得JSONの構造（law_full_text の
  tag/attr/children ツリー）が同じなら抽出器はそのまま動く。

## 2. フル抽出（1コマンド）
```bash
cd ~/path/to/Project-codex
python3 phases/egov_definition_extract.py \
    data/egov/egov_statutory_definitions_ALL.jsonl \
    --dir "$EGOV_DIR" --glob '*_current.json'
```
標準エラーに法令ごとの件数と、末尾に総計（by confidence / by type）が出る。
出力 `data/egov/egov_statutory_definitions_ALL.jsonl` が**全法令の錨**。
各行: `term, definition, law_id, law_name, article, item, uri(egov:…), scheme=jp_statutory_definition,
authority_rank=100, source=egov, definition_type, confidence`。

- `--glob '*_current.json'` … ファイル名パターン。`*.json` でも可。
- 法令名は各JSONの LawTitle から自動。`(term, law_id, article)` で全法令横断 dedup。

## 3. 品質の使い分け（重要）
- `definition_type` が **`item_definition` / `inline_toha` / `paren_definition` = high** は
  そのまま錨に使える綺麗な法定定義（著作物・公衆送信・子会社 等）。
- **`paren_abbreviation` = medium** は「…（以下「X」という。）」型で、用語Xは綺麗だが
  **定義句の前方境界がfuzz**（截断ノイズ混在）。**suspect層で受け、auto_apply=false**。
  canonical に上げる前に目視 or 追加ルールで境界を直す。
```bash
# high だけ抜きたいとき:
python3 - <<'PY'
import json
hi=[json.loads(l) for l in open('data/egov/egov_statutory_definitions_ALL.jsonl')
    if json.loads(l)['confidence']=='high']
open('data/egov/egov_statutory_definitions_ALL_high.jsonl','w').write(
    ''.join(json.dumps(d,ensure_ascii=False)+'\n' for d in hi))
print(len(hi),'high anchors')
PY
```

## 4. 用語カードを全自動生成（任意）
錨ファイルを `--gold` に渡してカード化:
```bash
python3 phases/assemble_term_card.py 著作物 公衆送信 子会社 ... \
    --gold data/egov/egov_statutory_definitions_ALL.jsonl \
    --gakuyo data/gakuyo/gakuyo_all_entries.jsonl \
    --yuhikaku <有斐閣 all_entries.jsonl のローカルパス> \
    --jlt-csv  <JLT v19 CSV のローカルパス>
# 対象語を全錨の term から流すなら:
python3 - <<'PY'
import json,subprocess
terms=sorted({json.loads(l)['term'] for l in open('data/egov/egov_statutory_definitions_ALL.jsonl')})
subprocess.run(['python3','phases/assemble_term_card.py',*terms,
  '--gold','data/egov/egov_statutory_definitions_ALL.jsonl'])
PY
```

## 5. コミット（成果を残す）
```bash
git add data/egov/egov_statutory_definitions_ALL*.jsonl data/cards/
git commit -m "Full 158-law statutory-definition anchors (local run)"
git push origin claude/gakuyo-headless-migrate-AuGAM
```

---

## 想定される結果の目安
13法令で 534定義（high 216）。158法令フルなら **数千件規模の錨**になる見込み。
そこから scheme別に `alo_terms`（jp_statutory_definition / authority_rank=100）→ `alo_hubs`
（provisional→接続→canonical）へ投入する、というのが既存ALO設計の流れ。

## 詰まったら
- `find` で `*_current.json` が0件 → コーパスがローカルに無い。§1(b) で e-Gov API から取得。
- 一部JSONで `!! skip` が出る → そのファイルだけ壊れ/別形式。無視して続行（dedupと総計は健全）。
- 件数が極端に少ない → `--glob` がファイル名と合っていない。`ls "$EGOV_DIR" | head` で実名確認。
