# PLAN — DD-LAWSUBTRANS-001 production 実装計画 v0.1

- 作成: 2026-06-11 / owner: 浅井 / head: Project-codex (claude-code remote)
- 前提: 設計は accepted（v0.1.3, 監査4世代 PASS_WITH_NOTES, owner ratify済）。本計画は §7/§10 の
  「production は別ゲート・HOLD」を解除していくための工程表。**各フェーズの出口は GPT お目付け役
  gate ＋ owner ratify**（lawtime と同方針: design accept と production apply を分離）。

---

## 0. このスレッドから導かれた実装上の示唆（10点）

1. **クリティカルパスは lawtime**。本 DD の `formal_status` ミラー・`lawtime_resolved` 条件・MCP の
   formal_note はすべて lawtime resolved view に依存する。その lawtime v0.2.2 production DDL は
   `MODIFY_REQUIRED`（P0-1 既存行 backfill / P0-2 valid_to 側検査 / P0-3 claim_support 許容 status の
   絞り込み / P0-4 succession 多重マッチ gate）。**lawtime P0 を閉じない限り本 DD の production は
   始まらない**。最初の一手はここ。
2. **gate は「違反行を返す SQL view ＋ CI で空を assert」方式**が家風（lawtime D6 で確立済み）。
   本 DD の §4 13 gate も同形式で実装する。producer 内の Python 自己 gate は CI に残す（二重化）。
3. **物理 DDL の検証場所はある**。Supabase `alo-connect` の public schema は現在空。**branch を切って
   dry-run** すれば本番を汚さずに DDL・トリガ・gate・view を実機検証できる（lawtime の
   「branch dry-run → 全 gate PASS → 本番」方針と一致）。
4. **スキーマの未決はもう無い**。監査で確定済み: claim_support は view 導出（物理列なら
   `claim_support_consistent_with_view`）／T2 は物理 status なし・T3/T4 は物理 status ありだが
   **current view が正本（review-event 優先）**／evidence locator gate は reviewed/accepted/
   claim_support 対象限定／evidence_count は当面 `evidence_pointer_id IS NOT NULL`＝1。
   実装はこの決定を写経するだけでよい。
5. **producer→DB の ingest 層が未設計**。現 producer は JSONL 出力のみ。production では
   L0 raw（JSONL artifact＋snapshot_id）→ staging → T1–T6 の **冪等 ingest**（dedup_key 主導、
   TOCLEGALREF の `dedup_key = sha1(...)` パターンを踏襲）が必要。これが新規設計の最大物。
6. **閾値・cue の較正には実データが要る**。本リモート環境は e-Gov API が許可リスト外（403）。
   較正は (a) ネットワーク許可のある環境 or (b) 既存の `alo-kg/raw/egov_revisions/`（3,506 revisions
   取得済）を使う。**ゴールドセット**: lawdelta は 2017 債権法改正等の既知改正ペア、treatment/
   drafter cue は実判決・実一問一答で pattern_id 単位の precision を測る（Paxton 流の per-label
   P/R 公開方式）。
7. **人手ループ（curation）が安全弁の要**。accepted 昇格は T6 review-event（review_basis 必須）の
   専権、casetreatment→assembler は curator binding が前提。**binding キューと review-event 起票の
   最小運用**（JSONL キュー＋承認カードでよい。UI は後）を作らないと、candidates が積み上がるだけに
   なる（TOCLEGALREF A-04 と同じ轍）。
8. **CI に「producer は accepted / claim_support=true を出さない」「mcprender は unknown を根拠に
   しない」を恒久 gate 化**（監査 P0/P1 の 5・6）。リポジトリには CI workflow（ci.yml /
   data-quality-gate.yml）が既存なので、69 unit tests＋producer gate＋snapshot test を載せる。
9. **入力データの現実**: drafterintent の対象（一問一答・逐条解説）は PDF/書籍。L0 raw 化と本文抽出は
   別工程（既存 bib/TOC レーンと接続）。判例テキストは D1-Law 契約 355 件＋将来の法務省 民事判決 DB
   （2026年度運用開始予定）が基盤。**Phase 4 の本格運用は判例テキストの調達計画と同期**させる。
10. **これは事務所の判断資産**（MILESTONE §9）。よって production でも「形式は公的データから引用、
    実質は事務所の評価として出典・両論・review_basis 付きで保存」の分離を、テーブル所有権と
    バックアップ方針（評価データ＝最重要資産）に反映する。

---

## 1. フェーズ計画

### Phase P0 — lawtime v0.2.3 パッチ（前提解除）🔑
- lawtime v0.2.2 の P0-1〜P0-4 を閉じる production-DDL パッチを作成し、DDLAWTIME gate に再投函。
- 併せて **resolved lawtime view**（本 DD が参照する形式状態の単一窓口）の定義を確定。
- 出口: `DDLAWTIME_PASS*` ＋ owner ratify（production apply 可）。
- 規模感: 小（指摘は4点とも局所的。backfill 手順＋gate 2本＋CHECK 1本＋絞り込み1本）。

### Phase P1 — 本 DD の DDL ＋ gate の実 SQL 化（branch dry-run）
- Supabase `alo-connect` に branch を作成し、T1–T6 DDL・append-only トリガ・`v_*_current`
  （T2/T3/T4 同型、review-event 優先）・§4 13 gate を **violation-view 形式**で投入。
- 合成データ（本スレの fixture 群）で全 gate の検知力を確認（わざと違反を入れて検出されることまで）。
- 出口: dry-run レポートを gate=DDLAWSUBTRANS で監査 → owner ratify → **本番 DDL apply**。
- 規模感: 中。設計確定済みのため写経＋検証が主。

### Phase P2 — ingest 層（producer JSONL → DB、冪等）
- L0: producer artifact（JSONL＋summary）を snapshot_id 付きで raw 保存。
- staging→T1/T2/T5: dedup_key UPSERT（冪等）、`assertion_status` は candidate 起点、
  **accepted / claim_support=true を ingest が書けないことを DB 制約＋CI で二重に禁止**。
- assembler の dispute / review-event 出力 → T6 append（decided_by=assembler）。
- 出口: 同一入力 2 回流し込みで差分ゼロ（冪等性試験）＋全 gate 空 → 監査 → ratify。
- 規模感: 中〜大（新規設計の最大物）。

### Phase P3 — 実データ較正（ゴールドセット）
- lawdelta: 既知改正ペア（債権法改正・会社法分離等、`alo-kg/raw/egov_revisions/` 活用）で
  delta_kind の P/R を測り、閾値（SUBST_MIN/RENUMBER_SIM/含有系）を確定。名大の改め文 16 パターン・
  公式新旧対照表を**検証器**として使う。
- casetreatment / drafterintent: 実判決・実逐条解説 100〜数百件で pattern_id 単位 precision を測定、
  medium 昇格基準を数値で固定（TOCLEGALREF の quarantine 解除方式を踏襲）。
- 出口: 較正レポート＋閾値表 → 監査 → ratify（以後の閾値変更は版管理）。
- 規模感: 中。データ調達がボトルネック（e-Gov ネットワーク許可 or 既存 raw、判例テキスト）。

### Phase P4 — curation 運用（人手ループ）
- binding キュー（treatment→条文/法理）と accepted 昇格の **review-event 起票フロー**
  （approval_queue カード方式を流用。起票者・review_basis 必須）。
- 浅井さんの実務時間を最小化する設計: assembler が dispute を作った target だけをレビュー対象に
  する（全 candidate の人手レビューはしない）。
- 出口: 試験運用 1 サイクル（実案件由来でない題材で）→ 監査 → 運用開始。

### Phase P5 — MCP 統合（出口）
- mcprender を MCP サーバに接続。formal_note は **lawtime resolved view から自動取得**（手渡し廃止）。
- snapshot test: 「unknown を根拠にしない」「disputed は両論」「断定フレーズ無し」を出力固定化。
- claim_support の最終条件（§4）を view で導出し、出口はその view のみを見る。
- 出口: 出力 snapshot 監査 → owner ratify → 限定公開（所内）。

## 2. 順序と依存

```
P0(lawtime) ──► P1(DDL+gate) ──► P2(ingest) ──► P3(較正) ──► P5(MCP)
                                      └────► P4(curation) ──┘
```
P3 と P4 は P2 完了後に並行可。P5 は P3 の閾値確定と P4 の運用開始を待つのが安全。

## 3. 各フェーズ共通の運用規律

- 出口は毎回 **GPT お目付け役 gate（to_gpt 投函）＋ owner ratify**。production apply は ratify 後のみ。
- DB 書込みは P1 の本番 apply まではゼロ維持。以後も「branch dry-run → gate 空 → apply」。
- すべての判断は review-event / approval card / audit ledger に残す（resolution_log 思想）。

## 4. リスクと先回り

| リスク | 先回り |
|---|---|
| lawtime P0 が長引く | P1 の DDL 写経・gate SQL 化は lawtime 非依存部分（T1–T6 本体）から先行着手可 |
| e-Gov ネットワーク制約 | 既存 `alo-kg/raw/egov_revisions/`（3,506 revisions）で P3 の大半は賄える |
| 判例テキスト不足（P4） | D1-Law 355 件で開始、法務省 民事判決 DB（2026 年度〜）で拡張 |
| candidates 滞留 | dispute 形成 target のみ人手レビュー（P4 設計）＋ 滞留数を data-quality-gate で監視 |
| 解釈資産の毀損 | append-only＋deprecated 保持＋評価テーブルのバックアップ優先度を最上位に |
