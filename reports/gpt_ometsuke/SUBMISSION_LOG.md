# gpt_ometsuke 投函ログ — DD-TOCLEGALREF

| 版 | request_id | gate | source_hash | Box REQUEST | Box 現物(docs/alo) | RESULT | 状態 |
|---|---|---|---|---|---|---|---|
| v0.1 | 20260606_toclegalref_v0.1_DDTOCLEGALREF | DDTOCLEGALREF | sha256:15f3025b… | file_id 2269713772194 → `processed/` 退避 | file_id 2269729051059 | **DDTOCLEGALREF_MODIFY_REQUIRED** (2026-06-07) | 監査済→v0.2へ |
| v0.2 | 20260607_toclegalref_v0.2_DDTOCLEGALREF | DDTOCLEGALREF | sha256:d891b882… | file_id 2270226491058 → `processed` | file_id 2270223952678 | **DDTOCLEGALREF_PASS_WITH_NOTES** (file_id 2270358722334, 2026-06-07) | **accept(design)・owner ratify 可** |

## v0.2 評定の取り込み（2026-06-07）
- 判定: `PASS_WITH_NOTES` / accepted_now=yes(design) / owner_ratify=yes_with_notes / **ratify前必須修正なし**。
- required_patches 1–9 全 CLOSED。production-promotion note 5点のうち #1(display_relation)/#4(dedup=extraction_policy_id)/#5(gate2本) をコード反映、#2/#3 を DD §5.5 に明記。
- producer 自己検査 **12 gate 全 PASS**（実データ 600 ノード, interprets 49=initial43/quarantine6, case 25）。
- **owner ratify 確定（2026-06-07, 浅井）**: DD-TOCLEGALREF-001 v0.2 = **ratified (design)**。TOC由来リンクは candidate `toc_signal`・claim_support 不適格、判例は canonical case URI 解決まで edge化しない、を design として確定。
- production promotion は別タスク（medium閾値/source_priority確定値/DD-LAWTIME resolver gate/canonical work・case URI 解決レーン）。DB書込みは promotion 実装後。

- v0.2 は v0.1 の required_patches 1–9 + proposed gates を反映（`reports/DD-TOCLEGALREF_draft_v0.2.md`）。
- producer 10 gate 全 PASS（実データ 600 ノード, interprets 49 = initial 43 / quarantine 6, case candidate 25）。
- RESULT は Box `from_gpt/20260607_toclegalref_v0.2_DDTOCLEGALREF_RESULT.md`（先頭行 `DDTOCLEGALREF_<LABEL>`）で受領予定。
- DB 書込みは依然ゼロ（accept + 法令/リンク層実装後）。
