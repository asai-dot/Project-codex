# P10: canonical 層 精度監査 + 誤スプリット回収（M1適用後）

```yaml
artifact: P10_precision_audit
depends_on: [P9_backfill_result, M1_backfill_issue_id, M2_falsesplit_recovery]
generated_at: 2026-06-22 JST
source: staging_periodical.issue_stage（監査=read-only / 回収=mutation 1行）
intent: 被覆率ではなく precision（誤マージ/誤スプリット防止）を最優先
```

## なぜこの作業を優先したか
残 unassigned(被覆率)を追うより、**M1で書いた718行の canonical 層に誤りが無いか**を先に検証する方が精度に効く。
canonical 層は dedup の土台で、ISSN誤り・通号式ズレ・増刊衝突が1つでも混ざると
**下流全体に系統誤差が伝播し、後から剥がせない**。113行の orphan より桁違いに重い。

## 監査結果（M1の canonical 層）

| 監査 | 方法 | 結果 |
|---|---|---|
| 誤マージ（別号が1idに衝突） | 通巻idごとの distinct(年月)>1 を検出 | **0件** ✓ |
| 誌内誤スプリット（同一年月が複数id） | (誌,年,月)ごとの distinct(id)>1 | **0件** ✓ |
| NCID通巻の号番衝突 | ncid:id ごとの distinct(issue_no)>1 | **0件** ✓ |
| NCID title差異 | ncid:id ごとの distinct(title)>1 | 1件＝**正マージ**（空白ゆれのみ） |

→ **M1の canonical 層は内部整合的**。捏造・衝突なし。

## 誤スプリット広域スキャン（seed誌名を含む非完全一致 journal_norm）
正規化ノイズで本来の誌から切り離された行を探索。

| 種別 | 件数 | 判定 |
|---|--:|---|
| jcaジャーナル[2025.11]号 | 1 | **真の誤スプリット → 回収**（#821へ3ソース統合） |
| 労働経済判例速報 660・661号 | 1 | 合併号 → **据置**（単独通巻id化は誤マージ риск） |
| XXXX年版重要労働判例総覧 等 | 12 | 書籍（誌でない）→ 対象外 |
| 法律時報e-book / 特別公開版 / 特別版 | 多数 | 別manifestation（P5準拠）→ 対象外 |

→ 大半が「正しく別物」。誤スプリットは実質 **jca 1件のみ**（有用な陰性結果）。

## unassigned 113 の素性棚卸し
| バケット | 件数 | 精度リスク |
|---|--:|---|
| 書籍系（総覧/読本/年版 等） | 68 | なし（誌でない） |
| キー無し・素性不明 | 45 | なし（年月/号番すら無く同定不能） |
| 年月あり/号番あり（誌候補） | **0** | — |

→ **unassigned に隠れた誌の号は0件**。回収可能な誤スプリットは無い＝精度リスク無し。

## 回収アクション（M2, 1行）
`jcaジャーナル[2025.11]号`（lionbolt）→ `issn:0386-3042#821`。
bencom/legallib の 2025-11号(既canonical)と**3ソース統合**を確認。

| source | title |
|---|---|
| bencom | JCAジャーナル 2025年11月号 |
| legallib | JCAジャーナル　2025年11月号 |
| lionbolt | JCAジャーナル　72巻11号［2025.11］号 |

## ステータス（M2適用後）
| status | 件数 |
|---|--:|
| canonical | 2,464 |
| canonical_ym | 178 |
| provisional_no_issn | 56 |
| provisional_ym | 36 |
| unassigned | 113 |
| **被覆(canonical+ym)** | **2,642 / 2,847 = 92.8%** |

## 結論
- M1の精度は健全（誤マージ/誤スプリット0）。
- 残 provisional/unassigned は **書籍・別manifestation・合併号・keyless orphan** で構成され、
  canonical化すると逆に精度を損なう（誤マージ риск）か、そもそも誌でない。
- すなわち **現状の canonical 境界が precision 最適**。次の被覆向上は「キー採番（人事の地図等）」
  という外部入力待ちで、内部処理で安全に動かせる精度レバーは出し切った。
