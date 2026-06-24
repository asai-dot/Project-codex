# MF-1: G23 非配列 term_ids ガード パッチ（実装パケット／担当: コーデックスちゃん）

> 出所: `DD-D1TAXO-001 v0.6-R3 Pre-Apply 監査`（DDD1TAXO_PREAPPLY_CONDITIONAL_GO）の **canary ブロッカー MF-1**。
> 種別: **DDL design patch（apply は HOLD・owner gate）**。本書は仕様確定済みの drop-in パッチ＋受入基準。
> 役割分担: 番頭=仕様確定/レビュー/ゲート、**コーデックス=実 G23 gate view への適用＋smoke＋canary 実行**（ローカルの実ファイル/scratch Postgres にアクセスできる主体）。

## 問題（R2 の G23）

```sql
CROSS JOIN LATERAL jsonb_array_elements_text(
  COALESCE(path_elem->'term_ids', '[]'::jsonb)
) AS term_id_text
WHERE term_id_text ~ '^[0-9]+$'
```

`COALESCE(..., '[]')` は **NULL/欠落のみ**を守る。`term_ids` が **配列でない JSON（string `"123"` / object / number / boolean）** の場合、
`jsonb_array_elements_text()` が regex に到達する前に**エラーで落ちる**。非配列の「あり得るが不正な JSON」で落ちるゲートは
安全な pre-apply ゲートではない。

## パッチ（drop-in）

### P1. term_ids 展開を array-guard

```sql
CROSS JOIN LATERAL jsonb_array_elements_text(
  CASE
    WHEN jsonb_typeof(path_elem->'term_ids') = 'array'
      THEN path_elem->'term_ids'
    ELSE '[]'::jsonb
  END
) AS term_id_text
WHERE term_id_text ~ '^[0-9]+$'
```

### P2. taxonomy_paths 展開も同クラスで array-guard（外側）

```sql
CROSS JOIN LATERAL jsonb_array_elements(
  CASE
    WHEN jsonb_typeof(ca.taxonomy_paths) = 'array'
      THEN ca.taxonomy_paths
    ELSE '[]'::jsonb
  END
) AS path_elem
```

## 適用先 / 不変条件

- 適用先: v0.6-R3 の **G23 gate view 定義**（実ファイルは local の v0.6/R3 gate SQL。`OR REPLACE 禁止`規律に抵触しないやり方で——
  新 version の gate view を張り直す／migration note を添える）。
- 適用後も **数値変換ガード `term_id_text ~ '^[0-9]+$'` は維持**（P1 はその上流の shape 安全化）。
- 非配列 term_ids は「violation」ではなく「**空集合（0 件）**」として扱う（誤検出0）。

## 受入基準（DoD）

1. `MF1_G23_negative_smoke.sql`（同梱）が **エラーなく完走**し、非配列 6 形状で violation 0 / 配列のみ展開。
2. 戸籍法 canary で `G23 violation = 0` / `broader cycle = 0`。
3. raw label は不変（本パッチは検査のみ。データ非改変）。

## 注記

- ローカルの `apply_lowercase_v4_patch.py` は **v4 enumerator** であり MF-1 ではない。
  → コーデックスは **MF-1 が現 gate に未適用であることを先に確認**してから P1/P2 を当てる。
