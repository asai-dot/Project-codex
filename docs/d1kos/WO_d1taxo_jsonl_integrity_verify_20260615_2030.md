# WO-D1TAXO-002 — DD-D1TAXO-001 v3 取込前 JSONL バイト単位 整合検査

- 発注: 番頭（Claude Head） / owner: 浅井（承認済 2026-06-15）
- 担当: ワーカーちゃん（ローカル alo-ai。実 JSONL とローカル環境にアクセス可）
- 起票: 2026-06-15 20:30 JST
- 種別: 検証のみ（**read-only / DB 未投入 / ファイル非改変**）
- 位置づけ: 番頭側で A（内部整合・木構造＋件数）は全件 PASS 済み。ただし `.jsonl` 実体は
  クラウド側でテキスト取得できず**バイト単位の同一性・参照健全性が未検査**。本WOでそこを閉じ、
  DBA apply（受入パッケージ A1–A8、現 HOLD）前の信頼性ゲートにする。

## 対象ファイル（`app/data/pacsigny/iteration/`）

- 源: `d1law_live_taxonomy_20260612_nodes.jsonl`（55,074）
- 変換 v3:
  - `d1law_taikei_alo_terms_load_20260615_v3_alo_terms.jsonl`（49,733）
  - `..._v3_alo_term_labels.jsonl`（49,733）
  - `..._v3_alo_term_relations.jsonl`（38,910）
  - `..._v3_alo_d1law_taikei_extra.jsonl`（49,733）
  - `..._v3_statutes_candidates.jsonl`（5,341）
  - `..._v3_manifest.json`（各 sha256 / rows）

## 検査項目（全て決定論・自動）

1. **sha256 / 行数一致**: 各 JSONL の実 sha256 が manifest 記載と一致。行数が
   terms 49,733 / labels 49,733 / relations 38,910 / extra 49,733 / statutes 5,341、
   かつ `terms + statutes == 55,074`。
2. **term_uri 一意・1:1**: `alo_terms.term_uri` 重複 0。`labels` / `extra` の term_uri が
   terms に全て存在（orphan 0）し、各 term につき labels 1 件 / extra 1 件。
3. **relations 健全性**: `src_term_uri` / `dst_term_uri` がともに terms に存在（dst orphan 0）。
   `rel_type` は `skos_broader` のみ。自己参照 0。サイクル 0。
   **dst が statutes 側（L1–L3）でないこと**（同 scheme 縛り＝スキーム横断禁止の実体確認）。
4. **値域**: `status` に `canonical` 混入 0（v2 バグの再発防止。許容は active/deprecated/merged/review_dismissed）。
   `term_tier ∈ {1,2}`。
5. **labels 規律**: pref/ja が term 毎 1 件（`UNIQUE(term_id,lang)` 違反になる重複 0）。
   `normalized_text == NFC(label_text)`。
6. **排他**: `statutes_candidates.term_uri` が terms と重複しない（L1–L3 と L4–L11 が排他）。
7. **源との一致**: `nodes.jsonl` の L4–L11（level≥3）集合 == terms の `source_item_key` 集合
   （取りこぼし 0 / 混入 0）。L1–L3（level≤2）集合 == statutes_candidates。

## 参考（番頭が源 CSV で確認済の期待値）

- by_level: `{0:21,1:137,2:5183,3:10823,4:11440,5:8753,6:6158,7:6356,8:3021,9:1849,10:1333}`（計 55,074）
- L1–L3=5,341 / L4–L11=49,733 / skos_broader=level≥4=38,910

## 成果物（`from_worker/` または iteration へ）

- `VERIFY_d1taxo_v3_jsonl_integrity_<date>.md`（各項目 PASS/件数の表）
- 同 `..._result.json`（機械可読）
- NG があれば該当 term_uri/行のサンプル（最大 50 件）を添付

## 完了基準（DoD）

- 上記 7 項目すべて PASS、または NG 一覧を提示。
- read-only を厳守（DB 投入・ファイル改変・canonical/raw 変更は行わない。apply は引き続き HOLD）。

## 備考

- 本検査が全 PASS なら、受入パッケージ §3「RUNBOOK 検証」の機械的前提が満たされる
  （実 DDL 列整合・JSONL 取込形式は別途 DBA 確認）。
- 余力があれば C（再キャプチャ差分／raw HTML 再パース一致）も歓迎だが任意。
