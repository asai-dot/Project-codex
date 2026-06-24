# P7: 解決ゲートの再定義 — canonical_ym 発見でP4/P6を訂正（read-only）

```yaml
artifact: P7_resolution_gate_correction
supersedes_headline_of: [P4_maxlift_drycompute, P6_lift_realcompute]
generated_at: 2026-06-20 JST
source: staging_periodical.issue_stage（read-only / mutation 0）
```

## 訂正の核心
issue_id の canonical 判定ゲートは **「キー(ISSN/NCID)の有無」だけ**。通巻は必須ではない。

| status | 件数 | id形式 | 意味 |
|---|--:|---|---|
| canonical | 1,833 | `issn:0287-9670#1082` | ISSN＋通巻 |
| **canonical_ym** | 90 | `issn:0287-6345#2023-01` | **ISSN＋年月（通巻不要・月刊で確定）** |
| provisional_ym | 534 | `jp:{名}#2026-05` | キー無＋年月 |
| provisional_no_issn | 277 | `jp:{名}#{通巻}` | キー無＋通巻 |
| unassigned | 113 | null | — |
| 総計 | 2,847 | | |

→ **provisional_ym + ISSN = canonical_ym**（通巻不要）。P4ドライ計算の「通巻欠＝canonical化不可」は誤り。

## 実リフト（確定seed適用・厳密集計）

| キー | provisional行 | →canonical(通巻) | →canonical_ym(年月) |
|---|--:|--:|--:|
| ISSN(confirmed) | 606 | 108 | 498 |
| NCID(裁可) | 110 | 110 | 0 |
| **solid 計** | **716** | 218 | 498 |
| ebook(法律時報e-book,別manifestation) | 36 | 36 | — |
| candidate(法と哲学,未検証) | 4 | 4 | — |

- **solid +716**（P6の+218は通巻必須を誤前提とした過小評価）。
- canonical 被覆: **1,923 → 2,639 / 2,847 = 67.5%→92.7%**（solid）。ebook+candidate確定で 2,679（94.1%）。
- 残: 168 = unassigned 113 ＋ 非seed誌の provisional 55。

## Track B（通巻抽出）の位置づけ訂正
- **解決の必須条件ではない**。最大ターゲットだった月刊（税経通信208・jcaジャーナル216・ビジネス法務66）は ISSN seed だけで canonical_ym 化する。
- Track B は **精度向上（月→通巻）のオプション**に降格。価値が出るのは「同一年月に複数号（臨時増刊等）」を区別したい場合のみ。
- 月内複数行（jca 77・税経 58）は実体は **bencom/legallib のクロスソース重複**（同一号）で、canonical_ym が正しく統合する対象＝望ましい挙動。真の増刊衝突は少数。

## 残ボトルネック（Track Bではない）
1. **unassigned 113**：issue_id 未付与。年月/通巻すら無い行の素性調査が先。
2. **非seed誌 provisional 55**：competition newsletter / asia&emerging 等、ISSN未付番の小規模newsletter。
3. **no-key seed誌**：人事の地図24（ISSN/NCID未取得・月刊なのでキーさえ来れば canonical_ym）/ jcaaビジネスジャーナル4（2025新刊・未付番）。

## owner判断事項（投げる前に調べ済み）
**canonical_ym（月精度）を月刊の終端状態として受容してよいか。**
- 受容するなら：Track B（通巻抽出）は不要。残作業は unassigned 113 と no-key 誌のキー採番のみ。被覆は即 ~93%。
- 通巻精度を要件とするなら：Track B を月刊にも適用。ただしデータ源は限定的（jcaはBox NDLコーパスに無し→lionbolt巻号アンカー＋暦算 or NDL再取得が要る）。
