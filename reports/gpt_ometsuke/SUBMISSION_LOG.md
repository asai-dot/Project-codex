# gpt_ometsuke 投函ログ — DD-TOCLEGALREF

| 版 | request_id | gate | source_hash | Box REQUEST | Box 現物(docs/alo) | RESULT | 状態 |
|---|---|---|---|---|---|---|---|
| v0.1 | 20260606_toclegalref_v0.1_DDTOCLEGALREF | DDTOCLEGALREF | sha256:15f3025b… | file_id 2269713772194 → `processed/` 退避 | file_id 2269729051059 | **DDTOCLEGALREF_MODIFY_REQUIRED** (2026-06-07) | 監査済→v0.2へ |
| v0.2 | 20260607_toclegalref_v0.2_DDTOCLEGALREF | DDTOCLEGALREF | sha256:d891b882… | file_id 2270226491058 (`to_gpt/`, queued) | file_id 2270223952678 | 受領待ち | **投函済・RESULT待ち** |

- v0.2 は v0.1 の required_patches 1–9 + proposed gates を反映（`reports/DD-TOCLEGALREF_draft_v0.2.md`）。
- producer 10 gate 全 PASS（実データ 600 ノード, interprets 49 = initial 43 / quarantine 6, case candidate 25）。
- RESULT は Box `from_gpt/20260607_toclegalref_v0.2_DDTOCLEGALREF_RESULT.md`（先頭行 `DDTOCLEGALREF_<LABEL>`）で受領予定。
- DB 書込みは依然ゼロ（accept + 法令/リンク層実装後）。
