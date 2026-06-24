# GPT監査結果と反映ログ ― CASELINK（2026-06-06）

- 監査レーン: Box `handoffs/gpt_ometsuke/`（GPT Pro お目付け役）
- REQUEST: `to_gpt/20260606_caselink_CASELINK_REQUEST.md`（匿名化現物同梱）
- RESULT: `from_gpt/20260606_caselink_CASELINK_RESULT.md`
- **判定: `CASELINK_PASS_WITH_NOTES`**（久保さんへの共有可。確定ルール化の前に下記反映が条件）
- 本体ルール/データモデルとの **hard な不整合なし**（N:M・9パターン・candidate≠truth・背骨ID・Boxメタデータは整合）

## 指摘と反映状況

| # | GPT指摘 | 反映 |
|---|---|---|
| 高1 | **D1 旧姓/別姓は「強い候補特徴量」に留める**。自動確定でなくreview queueへ。`alias_candidate`/`alias_confirmed`分離、根拠をevidenceで保持 | ✅ 01§5・03§5-E・06§3-3に「候補特徴量・自動確定しない」を明記 |
| 高2 | **D2 利益相反メンションの消去法は人数/運用変更で壊れる**。`assignee_prior`として扱い**単独確定禁止** | ✅ 03§5-E・06§3-3を「担当候補を強く示唆（単独確定禁止）」に弱化 |
| 高3 | **誤紐付けの巻戻し設計が弱い**。append-onlyの`link_decision_log`(confirmed/rejected/superseded)。確定後も取消可・旧判断を消さない | ✅ 03チェックリストに#14追加、04・05に巻戻し経路を追記 |
| 中4 | **Box `sf_record_id`はメタデータ/サイドカー優先**、フォルダ名一括改名は後段 | ✅ 03#13・06§3-4を「メタデータ優先・リネームは後段」に修正 |
| 中5 | **非案件トリアージに行き先語彙**（`non_matter_type`の粗語彙） | ✅ 04に`non_matter_type`語彙を追加 |
| 中6 | **中黒・全半角正規化の副作用**（別法人の誤併合）。正規化キーは候補生成用、確定キーにしない。原表記併存 | ✅ 06§3-2/§3-3に「正規化キーは候補用・確定キーにしない」を明記 |
| 弱 | 表現弱化（「実データで確認」→「本件サンプルで観測」/「消去法で担当」→「担当候補を強く示唆」/「最優先級」→「初期実装の高優先」/「必須」を法的必須と実装推奨に分離） | ✅ 各所反映 |

## 久保さんが実装前に決めるべき設計判断 TOP5（GPT提示・そのまま引き継ぎ）

1. link decision を **append-only**にするか上書きか（推奨: append-only）
2. `sf_record_id` を Box metadata に付与する最小単位（推奨: 案件フォルダから開始）
3. 自動確定/人レビュー/未分類の閾値と初期運用（推奨: 高precisionのみ自動）
4. alias/旧姓/同姓異人の **evidence schema**
5. 誤紐付けの検出・取り消し・再学習除外の運用

## メモ
- 監査は匿名化版で実施（実依頼者名・離婚案件の旧姓等は記号化して投函）。
- RESULT全文は Box `from_gpt/20260606_caselink_CASELINK_RESULT.md`。
