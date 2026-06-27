# RESULT — DDLAWREF: statute-citation edge_type vocabulary 照合（lawtime v0.2.4）

> 種別: **RESULT**（DDLAWREF v0.1 設計監査 RESULT からの抽出）
> 日付: 2026-06-27
> 元 REQUEST: `docs/dd/DD-LAWTIME-001_v0.2.4_DDLAWREF_vocab_reconcile_REQUEST.md`（Box file_id `2309304297318`）
> RESULT 出典: Box `gpt_ometsuke/from_gpt` / `DDLAWREF_v0.1_20260623_RESULT.md`（file_id `2305640889317`、2026-06-26 更新、label: **DDLAWREF_PASS_WITH_NOTES**）
> 注意: 本 RESULT は DDLAWREF v0.1 設計監査の RESULT から関連箇所を抽出したもの。
>       vocab reconcile REQUEST（file_id `2309304297318`）の**直接 RESULT はまだ未着**。

---

## 1. 回答サマリ（REQUEST §3 の4問に対して）

| 問い | 回答 | ソース |
|---|---|---|
| **Q1. statute-citation edge_type の値** | `cites_statute` / `delegates_to` / `references` / `implements` (lawtime 共有4種) | §3.3 |
| **Q2. alo_edges に載るか別テーブルか** | **`alo_edges`** で正しい（"形式事実 edge として `alo_edges` / link layer に引き取る方針は正しい"） | §2.1 |
| **Q3. dst_uri URI 規約** | **未言及** — 直接 REQUEST RESULT 待ち | — |
| **Q4. 投入時期** | production DDL / DB write: **HOLD** 継続 | §4 |

---

## 2. DDLAWREF v0.1 確定 edge_type 全量（§2.1）

| edge_type | 用途 | lawtime 共有 |
|---|---|---|
| `cites_statute` | 条文→法令参照 | ✅ §3.3 |
| `delegates_to` | 委任（法律→政令→省令） | ✅ §3.3 |
| `references` | 条文間参照（同一法内・別法間） | ✅ §3.3 |
| `implements` | 実施・根拠関係 | ✅ §3.3 |
| `reads_as` | 読替え専用（準用・みなし・読替え）| ⬜ temporal semantics 未確認、Q3 pending |
| `authority_basis` | 根拠条文 | ⬜ §3.3 共有リストに含まず |
| `cites_administrative_guidance` | 告示・通達・ガイドライン | ⬜ 行政解釈レイヤ（法令とは authority が違う） |

---

## 3. §3.3 統合管理指示（lawtime 直結）

> DDLAWREF の edge_type taxonomy は lawtime と統合管理する。
> 特に **`cites_statute`、`references`、`delegates_to`、`implements` は
> lawtime 側の citation edge と共有語彙にすること**。
> edge_type registry を作り、各 edge_type について definition / allowed src_type /
> allowed dst_type / temporal evaluation required / claim_support default /
> evaluation layer handoff rule を定義する。

→ `lawtime.citation_edge_type_v20260624` ビューがそのまま統合管理の器となる。

---

## 4. lawtime への反映（2026-06-27 実施）

`migrations/lawtime/placement_v0.2.4/200_gates.sql` の `citation_edge_type_v20260624` を更新：

**変更前（v0.2.3 から踏襲の placeholder）:**
```sql
('cites_statute'), ('statute_ref'), ('applies_statute')
```

**変更後（DDLAWREF v0.1 RESULT §3.3 確定値）:**
```sql
('cites_statute'), ('delegates_to'), ('references'), ('implements')
```

対応:
- `statute_ref` → `references`（DDLAWREF v0.1 語彙）
- `applies_statute` → `implements`（DDLAWREF v0.1 語彙）
- `delegates_to` 追加（§3.3 共有リストに含む）

---

## 5. 未解決（直接 REQUEST RESULT 待ち）

- **Q3: dst_uri URI 規約**（statute-citation edge の dst_uri が `alo:law:jp:…` work URI 体系に乗るか）
  → `fn_resolve_law_reference_at(work_uri, as_of)` の入口が work URI であるため、確認が必要。
  → 直接 REQUEST (file_id `2309304297318`) の RESULT を待つ。

- **`reads_as` の lawtime 帰属**（法的読替えの temporal 評価が lawtime 対象か）
  → 現在 `citation_edge_type_v20260624` に含めず。DDLAWREF 側からの clarification を待つ。

- **edge_type registry 作成**（§3.3 が要求する joint registry）
  → DDLAWREF / lawtime の共同作業。本件は lawtime の scope 外。

---

## 6. Gate 状況（RESULT 反映後）

| gate | 状態 |
|---|---|
| G-INT-1/G-INT-2 | 語彙更新済み。母屋に citation edge 0 のため vacuously 空（production まで inert）|
| production apply（PHASE D） | **HOLD**（schema 的には GO / 実用上 inert）|
| lawsubtrans re-point（PHASE E） | **HOLD** |
