# RUNBOOK — forum_registry_seed 実生成（Mac CC, accept後 step b）

- 対象: DD-CASE-001 accept(2026-06-20) の next_action (b)。DD-CASEID-003 forum registry seed。
- 実行環境: **Mac CC のみ**（builder がローカル `hanrei.ttl` + D1 `判例一覧.csv` を読むため。リモート実行不可）。
- 性質: read-only 生成（CSV出力のみ）。DB write/DDL/canonical mint なし（AC-6 HOLD 維持）。

## 前提ファイル（ローカル）
- `~/Downloads/hanrei.ttl`（NII 判例 TTL。`caselawp:court` 81種の源）
- `.../判例＿DLfromD1law/判例一覧.csv`（D1 裁判所名 union 用。builder 内パス参照）
- builder: `build_forum_registry_seed.py`（Box 2264377914086）

## 手順
```bash
cd ~/ALOBookDX/事務所内本棚DX化計画/scripts   # builder 配置先
python3 build_forum_registry_seed.py ~/Downloads/hanrei.ttl
# 出力:
#   app/data/case_identity/forum_registry_seed.csv          ← 本体
#   app/data/case_identity/forum_registry_unmapped_d1.csv   ← 支部地名ローマ字TODO
```

## 生成後の検収（should_fix#4: 再現ログ＋SHA 添付）
```bash
sha256sum app/data/case_identity/forum_registry_seed.csv \
          app/data/case_identity/forum_registry_unmapped_d1.csv \
  | tee app/data/case_identity/forum_registry_seed.SHA256
```
- builder stdout（行数 / distinct forum_code / forum_type内訳 / unmapped件数 / REVIEW件数）を
  `forum_registry_seed_runlog_YYYYMMDD.txt` に保存。
- 上記 csv 2点 + SHA256 + runlog を Box `docs/alo` へ上げ、DD-CASEID-001/003 から参照。

## 整合チェック（accept済の不変則）
- forum_code の `forum_type` が DD-CASE-001 §2 case_type の既定 forum_type と矛盾しないこと。
- 準司法23件（QUASI台帳）が `alo_source_registry_seed`(recon, Box 2295292633374) の23行と source_system 一致すること。
- `jufu` は forum_code 上 court 扱いだが、出口は `lawyer_client_confidential / can_global_index=false`（AC-3）を維持。
- `__REVIEW__` / unmapped（支部ローマ字未確定）は **canonical mint しない**。CASEID-002（符号正規化）と併せて人手確定（AC-6 HOLD）。
