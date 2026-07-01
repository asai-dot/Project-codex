# ORCH-JOURNAL-ISSN-RESOLVE order 20260701 — journal 段2 識別子外部照合(read-only提案)

- orch_id: ORCH-JOURNAL-ISSN-RESOLVE-20260701 / channel: jissn
- 親WO: `docs/alo/WO-JOURNAL-AUTHORITY-FIX_v0.1_20260701.md` 段2（owner GO 済 2026-07-01）
- 種別: **read-only 外部照合→提案のみ**。canonical/DB反映は owner GO（本発注では書かない）。
- 前提: producer の既存 NDL SRU / CiNii ツール（authority の `source=ndl_sru:cinii_crid` を生成した動くコード）を使う。head の手組みは broad-match/誤ISSNリスクのため不採用。

## 対象（24誌・head 実測で確定）
1. **held 10誌**（status=unresolved・`journal_authority_stage2_proposal_v0.1.csv`）: TKC税研時報/建築関係法令の研究/立命館大学法学部ニューズレター/保安と外勤/明治大学法科大学院ジェンダー法センター年報/訟務月報/永世中立/東洋法学会会報/月刊債権管理/軍事民論
2. **NCID→ISSN 昇格 14誌**（status=seed_ncid_fallback・32,301記事）: 判例評論/労働法律旬報/税理/法曹/速報判例解説/地方税/登記インターネット/民事月報/月刊登記先例解説集/研修/週刊法律新聞/労働法令通信/判例セレクト/警察時報

## やること（各誌）
NDL SRU + CiNii で **雑誌(serial)レコードを exact title＋出版者一致**で特定し、ISSN(あれば)を取得。

### verdict（必須・1誌1件）
- `ISSN_RESOLVED`: exact title＋出版者一致の serial に ISSN あり → ISSN併記＋evidence(NDL/CiNii record id, title, publisher)
- `ISSN_NOT_EXIST`: 該当 serial は実在するが ISSN 未付与（例: 判例評論=判例時報の合本付録で ISSN無し疑い）→ NCID維持
- `AMBIGUOUS`: 複数 serial 候補/出版者不一致 → 提案せず owner/head へ（silentに流さない）

### 【厳守】dup-ISSN ガード
取得 ISSN が既に authority の**別誌**(journal_canonical≠対象)に割当済なら **絶対に提案しない**→verdict=`COLLISION`＋衝突先を記載。
（例: 月刊債権管理に 1348-8953 は不可＝季刊事業再生と債権管理に割当済。v3にあった値は誤マージなので使わない）

## 入力(read-only)
- `.../casename-dict/artifacts/periodical/journal_authority_stage2_proposal_v0.1.csv`（held 10・375340e）
- `.../casename-dict/artifacts/periodical/d1_journal_issn_authority_ALL_resolved_v14.csv`（931行・dup-ISSNガードの照合元＝全 key_value）

## 出力（成果物・commit/push）
- `artifacts/periodical/journal_issn_resolve_proposal_v0.1.csv`: 24行 = 誌名+現status+verdict+提案ISSN/NCID+出版者+evidence(record id)+衝突先(あれば)
- `artifacts/periodical/journal_issn_resolve_report_v0.1.md`: verdict内訳・COLLISION件数・AMBIGUOUS一覧・ISSN_NOT_EXIST一覧

## 受入基準
- 24誌すべてに verdict。ISSN_RESOLVED は evidence(record id)必須。
- dup-ISSNガードを全件通過（COLLISION は提案に混ぜない）。
- exact title 一致でない候補は AMBIGUOUS（推測ISSNを本採用しない）。

## 安全（厳守）
- **read-only 外部照合のみ**（公開メタ取得。生payload取込・publishはしない=external_share不変）。
- authority本体・canonical・DB反映は owner GO（本発注は提案止まり）。
- 迷いは AMBIGUOUS で head へ。誤ISSN混入は致命的（join汚染）＝精度優先。
