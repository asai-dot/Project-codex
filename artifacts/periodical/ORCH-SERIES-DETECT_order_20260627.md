# ORCH-SERIES-DETECT — Worker Claude Code 発注: 連載シリーズ検出

```yaml
order: ORCH-SERIES-DETECT
from: Cloud Code Web (codex, head)
to: Worker Claude Code
priority: 中（L4と並行可・リソース衝突なし）
read-only: 入力読み取りのみ、新規派生CSVを生成して push。
ref: DD-PERIODICAL-002 (L4補助メタ)
no_conflict_with: ORCH-L4-COVERAGE-LIFT(authority CSV触らない), classify-full(Ollama不使用)
```

## 目的
記事タイトルから**連載シリーズ**を検出し、`series_id` で記事をクラスタリングする。
連載＝同一テーマの長期論考。下流で「同一連載の記事群を引く」「連載の前後号を辿る」が可能になる。
分類の「連載・コラム」種別とは独立（粗分類が連載か否か、本ORCHは具体的にどの連載かを特定）。

## 入力
- `artifacts/periodical/article_join_dryrun_v0.1.csv` (article_id, issue_id, journal_canonical, pub_year, title)
- 必要ならMacローカルの `build/labeled_v0.2.1/article_meta_labeled.jsonl`

## 処理
1. **シグナル抽出**（タイトル正規表現）:
   - `第(N)回|その(N)|（N）|\((N)\)|(N)\.|【N】|①②③…` の通し番号
   - `（上|中|下|前|後|完）|（前編|後編|終）` の分割記号
   - `続|続編|続報|続々|新|新連載|連載|連載完|連載第N回`
   - `〜を考える(N)|について(N)`等の連番
   - 末尾に `(完|終)` の終了マーカー
2. **同一誌内クラスタ化**:
   - `(journal_canonical, 共通プレフィックス/サフィックス除去後の正規化タイトル)` でグルーピング
   - 同一誌で連続する pub_year/issue_id をまたぐ、かつ正規化タイトルが類似(編集距離 or トークン一致≥0.8)するものを同シリーズに統合
   - 単発（1記事のみ）は series 化しない
3. **`series_id` 採番**: `series:{journal_canonical_slug}#{normalized_title_hash[:8]}` （安定）。
4. **連番付与**: 同シリーズ内で `pub_year, issue_id` 順に `seq_in_series` を振る。

## 出力
- `artifacts/periodical/article_series_v0.1.csv`:
  `series_id, article_id, journal_canonical, seq_in_series, title_normalized, signals_matched, confidence`
- `artifacts/periodical/article_series_summary_v0.1.json`:
  `total_series, articles_in_series, avg_series_length, top10_longest_series[]`

## 受入基準（head側で監査）
- 連載長 ≥ 3 のシリーズが**少なくとも50以上**検出されること（質的下限。法律雑誌なら本来かなり多い）。
- 同一 article_id が複数 series に属さない（採番衝突 0）。
- 連載トップ10の手目視で「明らかに別連載なのに統合」が無い（後で監査・FAILなら閾値調整）。
- confidence は正規表現マッチ強度・タイトル類似度・誌内連続性で 0-1。中央値 ≥ 0.6 推奨。

## 安全
- read-only。authority CSV を**触らない**。
- L4-COVERAGE-LIFT が同authorityを書き換え中でも、本ORCHは入力CSVだけ読むので衝突しない。
- 出力ファイル名は `series_*` 固定、L4と被らない。

## 実行
1. `cd /Users/yuta/Project-codex/.claude/worktrees/...`（適切なworktreeで実行、無ければ作成）。
2. `git pull --rebase`（force-push禁止）。
3. 処理スクリプト(`tools/periodical/detect_series.py`)が無ければ作成して同じcommitに含める。
4. 出力 + summary を push。
