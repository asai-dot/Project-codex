# RUNBOOK — ローカルちゃん向け（NDLオフライン照合 R1→R2→R3）

このフォルダの機械処理は**全部スクリプト化済み**。あなた（ローカルちゃん）がやるのは
**ラスト1マイルの4ステップだけ**です。複雑な判断は不要。

## 前提
- Python 3.8+（標準ライブラリのみ。pip インストール不要）。
- NDL ダンプ（`ndl_all_records_*.csv` と `ndl_law_isbn.txt`）が Box Drive 同期で**ローカルに**ある。
  例: `~/Library/CloudStorage/Box-Box/浅井/.../NDL_書誌情報_raw`
  → クラウドのみのプレースホルダだと読めないので、**同期完了（実体ダウンロード済み）**を確認。
- ネットは不要。**ダンプ原本と索引を外部に出さない**（規約: external_egress=prohibited）。

## やること（順番に）

### ① 配管チェック（16GBの前に1回）
```bash
cd tools/ndl_offline
python3 selftest.py
```
最後に `SELFTEST PASS` が出ればOK。出なければ、出力をそのまま浅井さん（または上流のClaude）に貼って報告。

### ② 本番を一括実行
```bash
bash run_all.sh "<NDLダンプのフォルダの絶対パス>"
```
途中で1回だけ止まります。表示された `out/R1_probe_report.md` を開いて、
**isbn 列と ndl_bib_id 列が正しく検出されているか**だけ見てください。
- 正しければ Enter で続行（R2→R3 が自動で走る）。
- ズレていたら Ctrl-C。`out/R1_schema_map.json` の `column_roles` を手で直して、もう一度 `bash run_all.sh ...`。

### ③ 結果を戻す
`out/` の下記ファイルを浅井さん／監査へ渡す（コミットでも添付でもOK）:
- `R1_probe_report.md`, `R1_inventory.json`
- `R2_build_manifest.json`, `R2_rejects.tsv`（大きければ先頭100行で可）
- `R3_coverage_report.md`, `cohortA_isbn_candidates.tsv`

### ④ 外に出さないもの
- `out/ndl_isbn_index.tsv`（派生索引）と **ダンプ原本**は**ローカル保管のみ**。クラウド/外部に上げない。

## 困ったとき
- `csv が見つかりません` → パスが違う。Finder でフォルダを右クリック→パスをコピーして貼る。
- 文字化け/エンコーディングで止まる → そのままのエラー全文を報告。スクリプトは cp932/utf-8 等を自動試行します。
- 時間がかかる → 16GB なので数分〜十数分は正常。`scanned ...` が進んでいればOK。

## このパイプラインがやっていること（参考・読まなくてよい）
- R1: ファイル一覧・サイズ・SHA256、CSVのエンコーディング/区切り/列を自動判定（read-only）。
- R2: 全CSVをストリームし `ISBN13 → (NDL bibid, 版, 出版社, 年)` の索引を作成。
  同一ISBNに複数bibid（=版/刷違い）も検出。出所(source_file/row/snapshot)を各行に保持。原本は無改変。
- R3: 事務所蔵書のISBN（同梱 `input/cohortA_isbn.tsv`）を索引に当て、被覆率・新規解決見込み・
  新刊(freshness)抜けを算出。結果は全部 **candidate**（確定ではない）。
