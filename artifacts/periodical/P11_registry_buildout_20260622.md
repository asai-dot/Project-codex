# P11: 誌マスタ構築 + 決定的リゾルバ + 常設監査（A+B 実装結果）

```yaml
artifact: P11_registry_buildout
wo: WO-PERIODICAL-JOURNAL-REGISTRY v0.1
depends_on: [P9_backfill_result, P10_precision_audit]
applied_at: 2026-06-22 JST
migrations: [journal_registry_ddl, journal_registry_seed, journal_alias_and_crosswalk_seed,
             issue_id_resolver_view, periodical_audit_views,
             registry_fix_hiroba_and_add_journals, reconcile_hiroba_from_resolver,
             blj_formula_and_refine_false_split_audit, reconcile_blj_from_resolver]
intent: 解決ロジックをCSV/artifactからDBへ移管。新規データ自動canonical化＋ドリフト自動検知。
```

## 1. 構築物（A+B）
**A 誌マスタ + リゾルバ**
- `journal_registry`（29誌）: 全キー(ISSN-L/ISSN/NDLBibID/NCID)・通巻ルール・manifestationを集約。
- `journal_alias`: 旧字/号番ノイズ/合併号を吸収（誤スプリット予防）。
- `tsuukan_crosswalk`: 税経通信 NDL実値281行（増刊飛び保持）。
- `issue_id_resolved`（view）: issue_stage を decision論的に再解決。**新規行も通すだけで canonical/canonical_ym/held/unresolved が確定**。backfillは「viewと実体の差分リコンサイル」に一本化。

**通巻ルール taxonomy**
| rule | id生成 | 誌 |
|---|---|---|
| direct | key#issue_no（issue_noが通巻） | 判例時報・NBL・労働判例・判例集系・NCID4誌 等 |
| formula | key#（式で通巻算出） | jca(2016-01=703) / **blj(2019-01=130)** |
| ndl_actual | key#（crosswalk命中） | 税経通信 |
| ym_terminal | key#YYYY-MM（通巻なし） | ビジネス法務・ビジネスガイド・**法律のひろば** |

**B 常設監査ビュー（新データ着地時に自動再評価）**
`audit_false_merge` / `audit_false_split` / `audit_key_collision` /
`audit_tsuukan_monotonic` / `audit_resolver_drift` / `audit_unregistered`

## 2. 回帰テスト：resolver_drift = 0
リゾルバが M1/M2 の canonical 層を**完全再現**。DBへ移したロジックが手作業backfillと一致＝
新規データも同一規則で自動解決される保証。

## 3. 監査が即検出した「後にきく」実バグ2件（A+Bの真価）
P10の旧監査は4誌限定だったため見逃していた誤スプリットを、journal_id基盤の常設監査が摘出。

### (a) 法律のひろば — 巻内号を通巻と誤認
- legallib「第78巻**第6号**（2025年12月号）」→ issue_no=6 → `#6`、bencom ym → `#2025-12` に**分裂**。
- issue_no は巻内号で**巻が変わると振り直す**（79巻1号=2026-02）→ direct運用は将来 78巻6号と79巻6号が `#6` で**誤マージ**もする二重の罠。
- 修正: `ym_terminal` へ訂正。3行（#1/#3/#6）を ym へ統合（78巻3号はym欠落を2025-06補完し既存#2025-06へ合流）。

### (b) businesslawjournal — 通巻形とym形の分裂
- legallib 通巻 `#130` と bencom ym `#2019-01` が各月で**分裂**（18か月）。
- BLJは月刊で通巻連続（巻跨ぎ継続）。43通巻行が式 `130+(年-2019)×12+(月-1)` に**100%一致**（2017-08〜2021-02）検証。
- 修正: `formula` 採用。ym行18件を通巻へ**昇格統合**（精度を落とさず合流）。

### 副次: 監査定義の精緻化
`audit_false_split` を「同一(誌,年,月)に **ym形と通巻形が混在**」signature に変更。
旬刊/週刊（判例時報=月3号 等）の正常な月複数通巻を偽陽性にしない。

### 副次: registry網羅性
既存canonicalだが未登録だった主要3誌を追加（ISSNは既存idから実取得・推測なし）:
判例時報 0438-5888 / nbl 0287-9670（小文字整合）/ businesslawjournal **1882-7640**（seedメモ1882-6377は誤り）。
→ unregistered 1,172行 → **137行**（全て非誌：書籍・小newsletter・null）。

## 4. 最終状態（全監査クリーン）
| audit | 件数 |
|---|--:|
| false_merge | 0 |
| false_split | 0 |
| key_collision | 0 |
| tsuukan_monotonic | 0 |
| resolver_drift | 0 |
| unregistered_rows | 137（全て非誌） |

| status | 件数 |
|---|--:|
| canonical | 2,479 |
| canonical_ym | 163 |
| provisional_no_issn | 56 |
| provisional_ym | 36 |
| unassigned | 113 |
| **被覆(canonical+ym)** | **2,642 / 2,847 = 92.8%** |

## 5. 「後にきく」効果（恒久化されたもの）
1. **新規データ自動解決**: 月次の新号・新ソースは `issue_id_resolved` で即 canonical 化。手作業backfill不要。
2. **二重キー誤スプリット予防**: ISSN判明時は registry のキー1行更新で全行が正しい接頭辞へ（`audit_key_collision` が監視）。
3. **ドリフト自動検知**: 再ロードでprovisional戻り・通巻ズレ・新誌出現を監査viewが常時surface。
4. **誌別ルールの単一の真実**: 通巻有無・式・別manifestationの判断が registry に集約。CSV散在を解消。

## 6. 残・次レバー（外部入力 or 別WO）
- 人事の地図 / jcaaビジネスジャーナル / 法と哲学: キー採番・検証待ち（registry更新で即反映）。
- 税経通信2026（12行 canonical_ym）: NDL再取得で crosswalk 追補→通巻化。
- 合併号採番規約（労経速660・661）: auto_apply=false で隔離中。規約決定後に解決。
- `issue_stage` "audit only" コメント: 本マスタ＆昇格を本流パイプラインへ反映する経路は別WO（要owner確認）。
- セキュリティ別件: `biblio.*` 4テーブル RLS無効（advisor critical・periodical外）。
