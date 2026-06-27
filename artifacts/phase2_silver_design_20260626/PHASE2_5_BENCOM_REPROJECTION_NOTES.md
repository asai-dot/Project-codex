# Phase 2.5 — 弁コム既存 toc_nodes の再射影 論点メモ

```yaml
doc_id: PHASE2_5-BENCOM-REPROJECTION-NOTES-20260626
status: notes（Phase 2 PASS 後に DD として正式化する前段）
created_at: 2026-06-26 JST
author: Claude（Phase 2 監査待ち時間に作成）
gate: 本ファイルは思考メモ。DB変更を一切伴わない。
related:
  - artifacts/phase2_silver_design_20260626/PLAN_PHASE2_BRONZE_TO_SILVER.md
  - artifacts/phase2_silver_design_20260626/AUDIT_REQUEST_phase2_silver_to_gpt.md
  - tools/toc_search_index/migration_toc_path_text_trgm.sql
```

## 1. なぜ別フェーズか

Phase 2 は **lionbolt（236,674） + 将来の legallib** を新規に toc_nodes へ射影する。
**弁コム既存 552,544 行は S3 で `bencom-library` を除外フラグで触らない**。理由:

1. **命名差**：既存弁コム `toc_node_id` の発番規則が、新 mint 規則 `'tn:'||source||':'||bib_id||':'||ordinal` と一致するか未確認。一致しなければ「同じノードが2系統のID」で履歴汚染。
2. **embedding 温存**：弁コム既存行の embedding 列は現状すべて NULL だが、Phase 3 で生成が始まった後に Phase 2.5 を撃つと、UPDATE 判定で全行 re-embed の引き金になり得る。
3. **検証コスト**：弁コム 552k は新規射影と違って「既に正しいものを上書き」のため、差分（path_text 構築の取り違え等）が起きていないかの全件比較が要る。

新規（lionbolt/legallib）は **加算のみ**なので比較不要、リスク勾配が違う。

## 2. Phase 2.5 の必要性は実装結果次第

Phase 2 S4 検証で以下のどちらが出るかで分岐:

- (A) 新規射影の path_text サンプルが既存弁コム形式（`第8章 先取特権 > 第3節 ...`）と
  **完全一致** → 弁コム既存は再射影不要。**Phase 2.5 を skip**して良い。
- (B) 微差（区切り違い、エスケープ、`>` 半角/全角混在、トレ末空白）が出る → Phase 2.5 で
  **弁コム既存も新形式に揃える**価値あり（検索の一貫性確保）。

> 暫定判定: 既存弁コム path_text の avg 48.9字・サンプル `第8章 先取特権 > 第3節 先取特権の順位 > §§329-332(西原道雄)` を見る限り、新規射影と差はほぼ無い見込み（区切り ` > ` 半角＋スペース）。
> 実差が確認できなければ Phase 2.5 は **skip** で good enough。

## 3. もし実行する場合の論点

### 3.1 ID マッピング

- 既存 `toc_node_id` を保持しつつ、新形式 ID も alias として並走 → 過渡期の互換性
- もしくは UPDATE で `toc_node_id` を新形式に置換（外向き露出が無ければOK）
- 外部参照（既存アプリ・キャッシュ・ノートブック等）の棚卸しが先

### 3.2 embedding との同期

- 「path_text の文字列が同一であれば embedding は再生成しない」を厳格運用
- UPDATE 経路で `OLD.path_text = NEW.path_text` チェック、変更時のみ `embedding=NULL` リセット
- Phase 3 の backfill 順序: Phase 2 → Phase 2.5 → Phase 3。逆順は禁止（無駄 re-embed）

### 3.3 検証手順（dry-run 必須）

1. 関数 `fn_project_toc_silver(p_source='bencom-library', p_dry_run=true)` を実行
2. 結果と既存 552k 行を SQL 比較:
   - 件数差 = 0
   - parent_toc_node_id の対応関係（旧→新マッピングが一意）
   - path_text の文字列差分（全行 hash 比較で N=0 を目標）
3. 差分があれば**先に原因を Phase 2 設計にフィードバック**。Phase 2.5 単体で吸わない

### 3.4 ロールバック

- 弁コム既存は `toc_node_id` の更新を伴うため source 単位 DELETE では戻せない可能性
- 事前に `toc_nodes_bak_<date>` テーブルへ COPY しておく（embedding 含む）
- ロールバック手順: TRUNCATE 弁コム分 → INSERT FROM bak

## 4. ガバナンス

- Phase 2.5 は **別 PR / 別 DDDESIGN 監査**。Phase 2 PR と混ぜない
- 適用順: Phase 2 PASS → Phase 2 apply (S3/S5) → Phase 3 embedding → 必要時のみ Phase 2.5

## 5. 暫定結論

> 現時点での見立て: **Phase 2.5 は実施しない可能性が高い**。Phase 2 S4 で path_text の
> 形式差がほぼゼロと確認できる前提。差が出たら出たでこのメモを DD として正式化する。
