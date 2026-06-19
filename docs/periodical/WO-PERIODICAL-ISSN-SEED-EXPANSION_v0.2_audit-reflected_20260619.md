# WO: 雑誌号同定の ISSN seed 拡張 v0.2（GPTPRO監査反映版）

```yaml
wo_id: WO-PERIODICAL-ISSN-SEED-EXPANSION-20260618
version: v0.2 (audit-reflected)
supersedes: v0.1 (docs/periodical/WO-PERIODICAL-ISSN-SEED-EXPANSION_v0.1_20260618.md)
reflected_at: 2026-06-19 JST
audit_result: 20260618_WO-PERIODICAL-ISSN-SEED-EXPANSION_v0.1_GPTPRO_AUDIT_RESULT.md (Box 2294721582313)
verdict: DESIGN_PASS_WITH_NOTES
gate: READ_ONLY_STRICT + STAGING_ONLY（production apply / canonical promotion は HOLD・owner ratify待ち）
supabase_project: nixfjmwxmgugiiuqfuym
```

> v0.1 の設計方向・スコープ・データ破損ゼロ担保・フェーズ構成は**全て維持**。
> 本 v0.2 は GPTPRO監査(2026-06-19, DESIGN_PASS_WITH_NOTES)の **required_patches 5点と
> adversarial_findings** を反映した差分。production系 HOLD は不変。

## A. 監査の結論（要約）

- final_gate: **DESIGN_PASS_WITH_NOTES**
- GO: P1 lane split（read-only artifact）/ P2 seed draft / P3 Mac worker NDL抽出 / P4 staging dry-run（issue_id_v2 比較）
- HOLD: production apply / DDL・migration / canonical promotion / accepted edge / `jp:`→`issn:`本固定 / 外部公開

## B. required_patches の反映（v0.2で確定）

| # | 監査指摘 | v0.2 反映 |
|---|---|---|
| P-1 | 全 `jp:` 号IDに `provisional_uri=true` を明示 | P1/P4 の出力・view に **`provisional_uri` フラグ列を必須**化。`issn:` は false、`jp:`/unassigned は true。レポートにも明記 |
| P-2 | P1出力の前に lane_hint 値を定義 | **lane_hint enum = `real_journal` / `yearbook` / `newsletter` / `unknown` の4値に確定**（§C）。判定規則も固定 |
| P-3 | rejected seed 行は issue_id_v2 生成に絶対使わない | ゲート `gate_issn_seed_evidence` を **「`confirmed` のみ canonical 生成可。`review`/`rejected` は候補表示限定」**に明文化。rejected は生成器入力から物理的に除外 |
| P-4 | 改称誌テストケースを P4 サンプルに追加 | P4 の誤同定監査サンプルに **改称・ISSN-L統合・旧字異表記（例 警察學論集↔警察学論集）の検体を必須**で含める |
| P-5 | 大量誌の層化FPサンプル（ランダム50だけにしない） | P4 を **「ランダム50 ＋ 大量誌（jca/税経通信/判例時報 等）層化サンプル各誌上限N」**の2層に変更 |

adversarial_findings の追加対応:
- 94%は**目標値**であり P4 dry-run 確定まで「達成」と言わない（v0.1 §7 既記載を再確認）。
- seed行は `valid_from/valid_to` + `renamed_from/renamed_to` 必須（§4 既設計を維持・強調）。
- 増刊・別冊・e-book・年合本は通巻連続性チェックを壊す → continuity gate は**例外種別を NULL 扱いで通す**（落とさず可視化）。
- `authority.publication`（記事タイトル層）を**号レベル authority に転用しない**（号同定は ISSN seed 起点に限定）。

## C. lane_hint 定義（P-2 / P1出力の前提・確定）

判定順（上から評価、最初に当たったものを採用）:

1. `unknown` … `journal_norm` が NULL または空
2. `newsletter` … `journal_norm` が `newsletter|ニュースレター` を含む（ISSN無しが通常 → seed対象外）
3. `yearbook` … `年版 / 令和N年 / 平成N年 / 20XX年版` 等の年版パターン（書籍/yearbookレーンへ → seed対象外）
4. `real_journal` … 上記以外（ISSN seed の対象母集団）

**v0.2 追補（実測で判明した漏れ）**: `…年度版` / `<昭和NN年度版>` / 極端に長い書名（体系書・実務書）が
`real_journal` に漏れることを確認（例: 「現代法律実務の諸問題(下)<昭和62年度版>」「設例と申告書記載例で理解する…賃上げ促進税制のすべて2024-2027年度版」）。
→ P1 では **`年度版` パターンと「書名長 > 閾値」を `yearbook` 寄せ＋`needs_review` フラグ**で隔離し、seed対象から外す。
最終確定は P3/owner レビューに回す（自動でISSNを当てない）。

## D. P1 実測結果（read-only・2026-06-18／本v0.2で反映）

`SET TRANSACTION READ ONLY` 下の SELECT。production mutation 0 / DDL 0。

| lane_hint | 号数 | issn済 | seed対象(未issn) | 誌数 |
|---|--:|--:|--:|--:|
| real_journal | 2,740 | 1,923 | ~817 | 58 |
| yearbook | 91 | 0 | （書籍レーンへ） | 83 |
| newsletter | 14 | 0 | （ISSN無し） | 3 |
| unknown | 2 | 0 | — | — |

→ seed対象 = real_journal の未issn **約817号 / 47誌**（既confirmed 11誌を除く）。詳細は `artifacts/periodical/P1_lane_split_20260619.md`。

## E. 役割分担（不変）

- read-only計測 / P1・P2成果物 / P4計測 = codex（このセッション）
- P3 NDL gz パース（ISSN×誌名×巻号・hash付きevidence）= Mac worker（NDL書誌はローカルのみ）
- confirmed昇格の承認 / production ratify = owner

## F. 次アクション

1. **[完了]** P1 lane split artifact（`artifacts/periodical/P1_lane_split_20260619.md`）
2. **[完了]** P2 seed draft（`artifacts/periodical/P2_issn_seed_v2_draft.csv`：confirmed 11実在＋review対象）
3. **[要 owner/worker]** P3: 上位誌の NDL evidence 抽出 WO を Mac worker へ（review→confirmed 昇格）
4. **[P3後]** P4: 拡張seedで `issue_id_v2` を並置算出し被覆率リフト＋FP監査
5. **[HOLD]** production apply / canonical promotion（P4 + rollback bundle + owner ratify 後の別WO）
