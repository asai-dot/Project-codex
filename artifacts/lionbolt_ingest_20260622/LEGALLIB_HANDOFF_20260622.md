# LEGALLIB_HANDOFF_20260622 — legal-library 本投入の引き継ぎ（このクラウド環境からは着手不可）

```yaml
doc_id: LEGALLIB-HANDOFF-20260622
status: blocked_handoff (BLOCKED: source unreachable from cloud env)
created_at: 2026-06-22 JST
author: Claude (claude.ai head) — 浅井さん指示「lionbolt/legal-library の本投入を進めて」
gate: NO_WRITE
related: DD_LIONBOLT_INGEST_v0.1.md / LIT_SOURCE_GAP_20260618.md
```

## 1. なぜここから進められないか（権限ではなく到達性の問題）

| 確認項目 | 結果 |
|---|---|
| Supabase 投入 | **未投入**（`bib_records.source` に legal-library 無し、`raw` 走査でも痕跡なし） |
| Box 配置 | **未配置**（lionbolt と違い Box にカタログが上がっていない） |
| source 実体の所在 | **Mac ローカルのみ**: `~/alo-ai/work/legallib_dl/`（台帳v1.1 §2） |
| このクラウド環境からの到達 | **不可**（Box にも無いため読めない。Mac FS には接続できない） |

→ lionbolt は Box にカタログがあったので設計+ローダを起こせたが、**legal-library は source が
クラウドから届かない**。最初の一手は **Mac 側で legal-library を Box にアップロードすること**。
これは owner 承認の問題ではなく、データが物理的にこの環境に存在しないという制約。

## 2. Mac 側で先にやること（順番）

1. **棚卸し**: `~/alo-ai/work/legallib_dl/` の中身を確認。
   - 投入元になる JSONL（lionbolt の `catalog_dedup.jsonl` 相当）はどれか
   - 1 レコードのスキーマ（フィールド名・目次構造）を 1 冊サンプルで控える
   - 件数（台帳では 4,051冊 / TOCノード 662,717）と実ファイルの一致を確認
2. **REPORT.md 相当を書く**: lionbolt の REPORT.md（取得元・スキーマ・件数・制約）に倣って
   legal-library 版のデータ契約を 1 枚作る。これがローダ設計の一次ソースになる。
3. **Box へアップロード**: `02_文献` 配下に `LEGALLIB_法律ライブラリ_<date>` フォルダを作り、
   投入元 JSONL + REPORT を上げる（lionbolt の folder 388659455439 と同じ構造）。
4. Box folder/file id を控えて本リポジトリに連絡（または次セッションで渡す）。

## 3. その後（クラウド側で再開できること）

Box に上がれば、lionbolt と**同じ枠組み**で進められる:
- `biblio.library_sources` に `legal-library` を 1 行登録（`tier`/`needs_auth`/URLテンプレは実態に合わせる）
- `biblio.bib_records`（`source='legal-library'`）+ `biblio.bib_toc` へ投入
- ローダは `tools/lionbolt_ingest/load_lionbolt.py` を雛形に `load_legallib.py` を派生
  （スキーマ差分＝フィールド名と目次構造のマッピングだけ差し替え）
- dedup は lionbolt 同様 ISBN/fingerprint で**レポートのみ**、mint は HOLD

## 4. 投入後の全体像（参考）

3 ソースが揃うと bib_records は概算:

| source | 冊数 | bib_toc |
|---|---:|---:|
| asai-bookshelf | 6,524 | 0 |
| bencom-library | 3,802 | 552,544 |
| lionbolt（DD で投入後） | 22,844 | 264,555 |
| legal-library（本ハンドオフ後） | 4,051 | 662,717 |
| **合計** | **37,221** | **1,479,716** |

台帳v1.1 の設計総計（約164万ノード）に近づく。残差は弁コム 688冊未ロード分など
（`LIT_SOURCE_GAP_20260618.md` B2.2）。

## 5. ブロッカー要約（owner へ）

- **lionbolt**: 設計+ローダ+マイグレーション完成（この PR）。owner ratify → 実行のみ。
- **legal-library**: **Mac 側 Box アップロードが先決**。上がり次第クラウドで lionbolt と同枠で実装可能。
