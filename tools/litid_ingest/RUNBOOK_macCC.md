# RUNBOOK (Mac) — raw_intake Phase 0 を実データで回す

レビュー待ち・legallib 待ちと**並行**で今できる read-only 作業。
既存3ルートの実カタログ（Box Drive 同期パス上）に field_profile をかけ、
合成値ではなく**実測の field-profile**を出す。canonical/DDL/突合には触れない（監査 HOLD 据置）。

> 実カタログ（LION BOLT 61MB / 弁コム 505MB / legallib フル版）は Mac ローカルにある。
> リポジトリのコンテナからは大きすぎて読めないため、本手順は **Mac の Claude Code / ターミナル**で実行する。

## 0. 取得（リポジトリ最新）

```
cd <repo>
git fetch origin claude/book-identification-progress-7yjxpc
git checkout claude/book-identification-progress-7yjxpc
python3 -m pytest tools/litid_ingest/tests/ -q   # 20 passed を確認
```

## 1. スケルトン作成（Box 同期パス上の raw_intake）

```
python3 tools/litid_ingest/make_raw_intake.py \
    --root "/Users/<you>/Library/CloudStorage/Box-Box/.../raw_intake" \
    --date 20260618
```
→ 4ルート分の `manifest.template.json` と `DROP_HERE.md` ができる（TODO テンプレ）。

## 2. 既存3ルートを実測（read-only, 今すぐ）

各カタログの実体パスを指定。`--source` だけ合わせれば key/isbn/toc は自動推定。

```
# LION BOLT (ISBN持ち, 想定 ISBN被覆あり/TOC低)
python3 tools/litid_ingest/field_profile.py \
    "<.../LIONBOLT.../catalog_dedup.jsonl>" --source lionbolt \
    --out-md artifacts/profile_lionbolt_20260618.md \
    --out-json artifacts/profile_lionbolt_20260618.json

# 弁コム (no-ISBN を実証, content_id一意性/TOC100%想定)
python3 tools/litid_ingest/field_profile.py \
    "<.../弁コム.../catalog.jsonl>" --source bengo4 \
    --out-md artifacts/profile_bengo4_20260618.md \
    --out-json artifacts/profile_bengo4_20260618.json

# 自所裁断 奥付メタ
python3 tools/litid_ingest/field_profile.py \
    "<.../colophon_meta.jsonl>" --source self_scan --isbn-field isbn_extracted \
    --out-md artifacts/profile_self_scan_20260618.md \
    --out-json artifacts/profile_self_scan_20260618.json
```

確認したい数字（監査 §4-1 NDLハブ妥当性の実証材料）:
- **弁コムが本当に無ISBN**か（`isbn_field: None` になるか）。
- LION BOLT / legallib の **ISBN被覆率・チェックサム妥当率・重複**。
- 各ルートの **キー一意率**（重複投入の温床がないか）。
- TOC 被覆率（独立証拠の供給量）。

## 3. legallib フル版が来たら（投入前ゲート, v0.2 §7-A）

```
# Box の raw_intake/legallib/20260618/ にドロップ後
python3 tools/litid_ingest/field_profile.py \
    "<.../raw_intake/legallib/20260618/legallib_full.jsonl>" --source legallib \
    --out-md profile.md --manifest-stub manifest.json
# manifest.json の TODO を埋める → ゲート
python3 tools/litid_ingest/manifest_gate.py manifest.json   # PASS で初めて投入可
```

## 4. 結果の戻し方

`artifacts/profile_*_20260618.md/.json` をブランチに commit して push すれば、
こちら（Claude）側が実測値を読んでドライラン計画/監査返答へ反映できる。
**生カタログ本体は commit しない**（容量・権利）。プロファイル要約のみ。
