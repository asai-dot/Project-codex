# 501 dry-run 戻り後の処理計画 v0.1（受入基準・分岐・次成果物）

- 作成: 2026-06-19 / Claude（リモート）
- 目的: 501 attr-layer dry-run（WO 2286268562080）の成果物が戻った瞬間に、**事前合意の基準で機械的に判定→分岐**できるようにする。
- 入力の在処（戻り次第いずれかを全取得）: `_claude_dispatch/from_worker/attr_layer_501_dryrun_20260615/`、または `claude/book-identification-*` 系ブランチのコミット、または Box `build/attr_layer_501_dryrun/`。
- 前提: 全分岐で **DDL/backfill/canonical promotion は owner ratify＋お目付け役PASS まで HOLD**（既決）。

## 0. 形式チェック（最初の30秒）
1. worker は完了したか / エラー報告か（`summary.md` か error ログか）。
2. **12必須出力（runbook §5.5）が揃っているか**。欠けていれば「partial」扱い。
3. **DB書込ゼロの証跡**があるか（read-only/dry-run遵守）。無ければ即停止・確認。

## 1. ハード受入ゲート（**全通過が GO の必要条件**。1つでも×→No-Go）
| ゲート | 合格 | ×の意味 |
|---|---|---|
| 接地 | `ungrounded_value_count == 0` | 採用値が観測に紐づかない＝anti-hallucination破れ → projection修正 |
| 誤マージ | gold評価で **false-merge ≈ 0** | 別workを同一視＝identity精度不足 → fingerprint/独立証拠規律修正 |
| 二重計上 | provenance_family 畳みが効き、`provenance_collapse_count`>0 で独立票が適切に減 | 弁コム×legallib を独立2票に数えた → family判定修正 |
| 決定性 | 2回流して projection hash 一致 | 非決定＝設計違反 → 実装修正 |
| rights | `rights_blocked_rate` が機能（購読由来が serving 不許可文脈へ出ない） | 漏れ → rights伝播修正 |
| work遅延 | `rollup_status` が全件 item_only | 早すぎる work合議 → guard修正 |
| HOLD遵守 | DB/DDL/backfill ゼロ | 違反 → 即エスカレーション |

## 2. 12出力の判定基準（runbook §5.5 ↔ 期待値）
| # 出力 | pass の目安 | ×/要注意の対応 |
|---|---|---|
| 1 独立証拠数(family別) | 主要属性で family≥1、二重計上なし | family誤判定→規律修正 |
| 2 item/edition/work候補状態 | 三層で矛盾なく分類 | work混入→item_onlyへ |
| 3 pub_date precision/kind分離 | 値・粒度・種別が分離記録 | 未分離→抽出修正 |
| 4 edition/impression marker＋根拠 | 版表示を抽出・記録 | 取れない本は needs_review |
| 5 TOC delta | node数/見出し一致率/階層差/page basis/coverage 出力 | 低coverage=判別力不足→要注意 |
| 6 grounded率/ungrounded | ungrounded=0（ハードゲート） | §1参照 |
| 7 triage後disputed率/field別 | **triage前の生不一致より大幅減**・絶対数が人手処理可能 | 過多→正規化/triage規則強化（CONDITIONAL） |
| 8 false-split/merge gold評価 | merge≈0（ハード）、split は版差で説明可 | split過剰→pub_date soft化/刷統合 |
| 9 二重計上防止結果 | collapse 実績あり | §1参照 |
| 10 unresolved/owner-review queue＋理由 | 件数と理由コードが明確 | 巨大なら閾値調整 |
| 11 proxy 1,470/847 比較 | **母集団差を明記して別表**（同一視しない） | 混同→記述修正（監査必須） |
| 12 追跡可能性 raw→candidate→adjudication→adopted | 全工程たどれる | 欠落→ログ補強 |

## 3. 分岐（判定→次アクション）
- **GO**（§1 全通過 ＋ §2 で致命なし）→ **DDL/backfill 計画ドラフトに着手**（§4）。ただし実行はせず owner ratify＋お目付け役へ。
- **CONDITIONAL**（§1 通過・§2 で disputed過多/coverage低 等の品質課題）→ 該当を**設計/規則で強化して再dry-run**（DDLに進まない）。例: disputed過多→正規化規則・definition_difference_allowed 拡充。
- **NO-GO**（§1 のどれか×）→ **失敗箇所別に差し戻し**:
  - ungrounded>0 → projection接地修正
  - false-merge>0 → fingerprint/独立evidence-family規律（FP note）修正
  - 二重計上 → provenance_family判定修正
  - 非決定 → 実装修正
  → 修正後に**再dry-run**（再びこの計画で判定）。
- **ERROR/partial**（worker失敗・出力欠落）→ 原因切り分け（入力パス `build/newsources_books_identity/20260611/` の有無 / NDL parser / JWT / 依存）→ **WO修正して再投函**。

## 4. GO時に私が即出す成果物
1. **results 分析レポート**（12項目の評価＋verdict＋proxyとの母集団差明記）→ repo＋必要なら お目付け役へ「dry-run結果」として投函（FP/ATTR next #4 の本番版）。
2. **DDL/backfill 計画ドラフト v0.1**（お目付け役 next #5）:
   - DDL案: `biblio_item_attr_observations`（append-only）/`biblio_item_attr_canonical`（projection cache）/`attr_registry`/`attr_policy`。SoT境界（§0.7）厳守。
   - backfill順: 観測投入 → projection算出 → canonical → biblio_item scalar は view/cache（独立書込み禁止）。
   - gate: append-only / determinism / grounded / provenance-no-double-count / rights-serving / work-rollup-requires-promotion / consumer-compatibility。
   - 段階: canary（小バッチ）→ batch、再実行diff0（冪等）。
   - **DDL実行は owner ratify＋お目付け役PASS後**。
3. 進捗台帳更新（IDENTITY_PROGRESS 相当）：採用値カバレッジ・disputed・unresolved・厚化数を記録。

## 5. 不変（全分岐で維持）
- identity-key ≠ attributes（属性一致だけで item/edition を mint しない）。
- 単独権威採用は adopted_status で明示・可逆。OCR単独/書名単独を canonical 昇格しない。
- 厚さはKPIにしない（採用値の正しさ・接地100%・triage後disputedで測る）。
- DB/DDL/backfill/canonical promotion は HOLD（owner＋お目付け役 後）。

## 6. 戻ったら私が踏む手順（チェックリスト）
1. 成果物を全取得（from_worker / branch / Box build）。
2. §0 形式 → §1 ハードゲート → §2 12項目 を順に判定。
3. §3 で分岐を確定し、verdict を1行で宣言。
4. GO なら §4 をその場で起こす／NO-GO なら差し戻しリストを出す。
5. repo へ記録・push、必要なら お目付け役へ投函。
