# DD-LAWTIME-001 v0.2.3 production-DDL パッチ（v0.2.2 MODIFY_REQUIRED P0-1〜P0-4 の閉鎖）

> **id**: `DD-LAWTIME-001` / **version**: v0.2.3 (production-DDL patch) / **status**: candidate
> **supersedes_review**: v0.2.2（gate DDLAWTIME → `DDLAWTIME_MODIFY_REQUIRED`, 2026-06-08）
> **owner**: 浅井 / **author**: Project-codex (claude-code remote) / **recorded_at**: 2026-06-11
> **scope**: v0.2.2 の DDL に対する**差分パッチのみ**（v0.2.1 design・v0.2.2 の採用方向は不変）。
> 加えて、DD-LAWSUBTRANS-001 が依存する **resolved lawtime view** を定義する（P1 接続点）。

---

## P0-1. 既存 statute edge の backfill → 制約検証の順序

問題: `temporal_status` 既定 NULL のまま `ck_law_ref_two_tier` を即時 ADD すると、既存の
statute edge（`as_of_basis` 既定 'unknown'）が `temporal_status='unchecked'` 要件に違反する。

解: **NOT VALID → backfill → VALIDATE** の3段で適用する。

```sql
-- (1) 列追加は v0.2.2 のまま（claim_support_eligible DEFAULT false 等）。
-- (2) 制約は NOT VALID で先置き（新規行にのみ即時適用）
ALTER TABLE alo_edges ADD CONSTRAINT ck_law_ref_two_tier CHECK (
  edge_type NOT IN ('cites_statute','statute_ref','applies_statute')
  OR ( (as_of_basis <> 'unknown' AND as_of_date IS NOT NULL
          AND (cited_law_id IS NOT NULL OR cited_law_work_id IS NOT NULL))
    OR (as_of_basis = 'unknown' AND as_of_date IS NULL AND resolved_law_revision_id IS NULL
          AND temporal_status = 'unchecked' AND claim_support_eligible = false) )
) NOT VALID;

-- (3) 既存 statute edge の backfill（unknown 系を unchecked に揃える）
UPDATE alo_edges
SET temporal_status = 'unchecked'
WHERE edge_type IN ('cites_statute','statute_ref','applies_statute')
  AND as_of_basis = 'unknown'
  AND temporal_status IS NULL;

-- (4) backfill 完了後に全行検証
ALTER TABLE alo_edges VALIDATE CONSTRAINT ck_law_ref_two_tier;
```

検収 gate（migration 専用・一時）:
```sql
CREATE VIEW gate_backfill_unknown_unchecked AS
  SELECT edge_id FROM alo_edges
  WHERE edge_type IN ('cites_statute','statute_ref','applies_statute')
    AND as_of_basis='unknown' AND (temporal_status IS DISTINCT FROM 'unchecked');
-- 合格: 0件（VALIDATE 前に空であること）
```

## P0-2. resolved 版の as_of カバレッジ両端検査（valid_to 側の追加）

問題: `gate_no_current_law_for_historical_citation` は `as_of_date < valid_from` のみ検査し、
**版の失効後**（`as_of_date >= valid_to`）に旧版を当てる誤りを検出できない。

解: 半開区間 `[valid_from, valid_to)` の**両端**を検査する gate に置換。

```sql
CREATE OR REPLACE VIEW gate_resolved_revision_covers_asof AS
  SELECT e.edge_id
  FROM alo_edges e
  JOIN alo_statutes s ON s.law_revision_id = e.resolved_law_revision_id
  WHERE e.as_of_basis <> 'unknown' AND e.as_of_date IS NOT NULL
    AND (
         (s.valid_from IS NOT NULL AND e.as_of_date <  s.valid_from)   -- 施行前に当てた
      OR (s.valid_to   IS NOT NULL AND e.as_of_date >= s.valid_to)     -- 失効後に当てた
    );
-- 旧 gate_no_current_law_for_historical_citation は本 view に統合（名称は残す場合 alias）
```

## P0-3. claim_support 許容 status の絞り込み（current / superseded のみ）

問題: claim_support に `pre_enactment / unenforced / repealed` を通すのは、通常の条文根拠として危険。

解: **初期運用は current / superseded に限定**（GPT 提示の選択肢のうち狭める側を採用）。
repealed 等を「状態主張」（〜は廃止済みである、という主張）として使う需要は、将来
`status_assertion` 用の別フラグ/別 edge_type として切り出す（本パッチでは導入しない＝安全側）。

```sql
CREATE OR REPLACE VIEW gate_claim_support_requires_resolved_lawtime AS
  SELECT e.edge_id FROM alo_edges e
  WHERE e.edge_type IN ('cites_statute','statute_ref','applies_statute')
    AND e.claim_support_eligible = true
    AND ( e.resolved_law_revision_id IS NULL
       OR e.temporal_status IS NULL
       OR e.temporal_status NOT IN ('current','superseded')             -- ★絞り込み
       OR e.temporal_caveat <> 'none'
       OR NOT EXISTS (SELECT 1 FROM alo_law_ref_temporal_eval_event v
                      WHERE v.edge_id = e.edge_id) );
```

## P0-4. succession 多重マッチ検出 gate（resolver の暗黙選択を可視化）

問題: 同一 Work・同一 as_of に複数 succession 行が有効な場合、`fn_resolve_law_reference_at` が
`ORDER BY ... LIMIT 1` で黙って1件を選ぶ。

解: authoritative（reviewed/confirmed）行同士の**期間重なり**を違反として返す gate を追加。
重なりが正当（merge/split の多対多）な場合は同一 `lineage_event_id` で束ねられているはずなので除外。

```sql
CREATE VIEW gate_succession_no_ambiguous_overlap AS
  SELECT a.succession_id AS succession_id_a, b.succession_id AS succession_id_b
  FROM alo_law_succession_edge a
  JOIN alo_law_succession_edge b
    ON a.law_work_id = b.law_work_id
   AND a.succession_id < b.succession_id
   AND a.relation_type <> 'unknown' AND b.relation_type <> 'unknown'
   AND a.confidence IN ('reviewed','confirmed')
   AND b.confidence IN ('reviewed','confirmed')
   -- 半開区間の重なり（NULL は開区間として扱う）
   AND (a.valid_from IS NULL OR b.valid_to IS NULL OR a.valid_from < b.valid_to)
   AND (b.valid_from IS NULL OR a.valid_to IS NULL OR b.valid_from < a.valid_to)
  WHERE a.law_id <> b.law_id                                  -- 別 law_id が同時に有効＝曖昧
    AND (a.lineage_event_id IS DISTINCT FROM b.lineage_event_id  -- 同一イベント束ねは除外
         OR a.lineage_event_id IS NULL);
-- 合格: 0件。違反が出た場合は valid_from/to の補正 or lineage_event_id での束ねを要する。
```

## R-1. resolved lawtime view（DD-LAWSUBTRANS-001 の接続点。本パッチで新設）

LAWSUBTRANS の `formal_status` ミラー整合 gate・MCP formal_note が参照する**形式状態の単一窓口**。

```sql
-- 法令（law_id）単位の現在形式状態
CREATE VIEW v_lawtime_formal_status AS
  SELECT s.law_id,
         CASE
           WHEN bool_or(s.revision_status = 'CurrentEnforced') THEN 'in_force'
           WHEN bool_or(s.revision_status = 'Repeal')          THEN 'repealed'
           WHEN bool_or(s.revision_status = 'PreviousEnforced')THEN 'superseded'
           WHEN bool_or(s.revision_status = 'UnEnforced')      THEN 'not_yet_in_force'
           ELSE 'unknown'
         END AS formal_status,
         max(s.valid_from) FILTER (WHERE s.revision_status='CurrentEnforced') AS current_from
  FROM alo_statutes s
  GROUP BY s.law_id;
-- 注: 'expired' / 'annulled' は e-Gov ソースに直接対応値が無いため本 view では産出しない。
--     必要になれば附則/官報由来の上書きテーブルを別途設ける（LAWSUBTRANS 側 enum は受け口を維持）。

-- statute edge 単位の解決済み状態（as_of 付き参照の窓口）
CREATE VIEW v_lawtime_resolved_ref AS
  SELECT e.edge_id, e.cited_law_work_id, e.cited_law_id, e.as_of_basis, e.as_of_date,
         e.resolved_law_revision_id, e.temporal_status, e.temporal_caveat,
         (e.resolved_law_revision_id IS NOT NULL
          AND e.temporal_status IS NOT NULL
          AND e.temporal_status <> 'unchecked') AS lawtime_resolved
  FROM alo_edges e
  WHERE e.edge_type IN ('cites_statute','statute_ref','applies_statute');
```

## 適用順（migration）

1. v0.2.2 の D1/D3/D4（succession / resolver / eval_event）— 変更なし
2. D2 列追加 → **P0-1**（NOT VALID → backfill → 検収 gate 空 → VALIDATE）
3. gate 群: v0.2.2 の各 view ＋ **P0-2 置換** ＋ **P0-3 置換** ＋ **P0-4 新設**
4. **R-1** view 新設
5. branch dry-run で全 gate 空 → 監査 → owner ratify → 本番 apply

## 変更なし（明記）

- 値域・テーブル定義・二段 resolver の関数シグネチャ・append-only トリガは v0.2.2 のまま。
- resolver の `LIMIT 1` 自体は維持（挙動変更はせず、曖昧ケースを P0-4 gate で**事前に空にする**運用）。

## changelog
- v0.2.3 (2026-06-11): v0.2.2 `DDLAWTIME_MODIFY_REQUIRED` の P0-1〜P0-4 を閉鎖。
  ①NOT VALID→backfill→VALIDATE の migration 順序＋検収 gate。②resolved 版カバレッジの両端検査。
  ③claim_support を current/superseded に限定（状態主張フラグは将来切り出し）。
  ④succession 期間重なりの曖昧検出 gate。＋ LAWSUBTRANS 接続用 resolved lawtime view（R-1）新設。
