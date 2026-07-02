---
worker_task_id: W-20260626-010
status: in_progress
lane: doing
updated_at: 2026-06-27
executor: owner-Mac（手動・nohupスイープ）＋ assistant（トリアージ/解析の先回り仕込み）
---

# 進捗メモ — D1文献編 全雑誌 完全網羅スイープ

## 実行状況（2026-06-27 12:54 時点）
- スイープ稼働中（Mac, `nohup bash /tmp/d1_full_sweep.sh`、単一書き手・`python3 -u`）。
- 入力: `/tmp/d1_all896.txt`（優先JSON 896誌、価値順だが**全部**取る value-blind）。
- 進捗: **119 / 896 誌 処理済み**（`grep -c '^###' ~/d1_full_sweep.log`）。
- 既取得の上位誌は冪等スキップ確認済み（例: 判例評論 5,888件/118p =「取得済118」を即スキップ）。
  小粒の長尾誌（特許研究66・環境法研究196・労働経済旬報352 …）に到達＝本番（未取得の埋め）進行中。
- ログ: `~/d1_full_sweep.log`（全件・追記）。スリープ抑止 `caffeinate -i -w <pid>` 推奨。
- ペース目安: 残り約2日弱。月曜には回り切る見込み。

## `総件数=0` の中間所見（要トリアージ）
スイープ中に出る 0件 は4種に分かれる。`tools/d1_bunken/triage_sweep_log.py` で自動仕分け可能:
- **① 括弧別名→ベース名で取得済**（無視可）: 例 法と政治〔関西学院大学〕=0 → 法と政治=578✓。
- **② 真ゼロ＝要・表記当て直し**（★本命）: 法学研究〔慶応〕・商事法務研究・法政研究〔九州大〕・
  知的財産法政策学研究・警察学論集・財政経済弘報・ジュリスト増刊 等。D1非収録 or 表記差。
- **③ Timeout/切替失敗 由来の0**（再試行候補・非収録ではない）: 法と政治〔関西学院大学〕
  （`Page.select_option: Timeout 30000ms`）等。
- **データ安全（再検索0だが取得済>0）**: 法学=0(取得済1165)・民事研修=0(取得済42)。既存データ無事。

## 回り切った後の段取り（STEP4）
1. `python3 tools/d1_bunken/triage_sweep_log.py ~/d1_full_sweep.log --tsv /tmp/d1_triage.tsv`
   → ②真ゼロ誌だけ抽出。③Timeout誌は再試行、②は別表記でリトライ。
2. 再パース `d1_bunken_parse_all.py` → ラベル `label_journals_v0.2.1.py`。
3. 新 unique_articles / 新カバレッジ%（/449,677）を 333,206・74.1% と比較。
4. `done/W-20260626-010_RESULT.md`（先頭 WORKER_PASS）に before/after・取得不能誌一覧・896外探索結果を記載。

## 注記
- 元データ無改変（追加のみ）。DB投入・canonical昇格・Box書込・削除はしていない（別ゲート）。
- assistant側は Mac に触れないため、解析/トリアージ tool の先回り作成のみ実施（このメモと triage script）。
  取得・パース・ラベルの実行は owner-Mac 側。
