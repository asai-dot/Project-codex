# alo_workflow_event_schema — v0.1 → v0.2 CHANGELOG

実査(Salesforce / Box / Gmail)はまだ未完のため、実査由来の大きなスキーマ変更は
**保留**。本リリースは「機械検証の固定」を本丸とし、実査不要で正当化できる
**保守的デルタのみ**を入れる。

## 変更点

1. **`schema_version` の const を更新**
   - `alo-workflow-event-0.1` → `alo-workflow-event-0.2`
   - 理由: バージョン識別子の更新。examples も合わせて 0.2 に。

2. **`event_type` を「コア enum + `x-` 接頭辞の自由型」の緩衝帯に**
   - v0.1: `{"type": "string", "enum": [...72種...]}`
   - v0.2: `{"type": "string", "oneOf": [{"enum": [...72種...]}, {"pattern": "^x-[a-z0-9_]+$"}]}`
   - コア enum(v0.1 の 72 種)は**そのまま維持**。加えて `x-` 接頭辞
     (`^x-[a-z0-9_]+$`)の自由型を許容。
   - 理由: 未知イベントの登場ごとに schema を改訂する事態を避けるため、
     拡張用の緩衝帯を設ける。コア型を狭めず後方互換を保つ。
     `oneOf` により「コア型」か「x- 型」かのどちらか一方に必ず一致させる。

## 変更しなかったもの(意図的)

- `$defs`(RecordRef / ActorRef / SourceRef / StateTransition / WorkItem /
  DocumentRef / DecisionRecord / FinanceRecord / DeadlineRef / HumanReview /
  Provenance)の構造・enum・required は **v0.1 のまま**。
- トップレベル required・`additionalProperties:false` も v0.1 のまま。
- 実査で得られる知見(SourceRef の system 値域の確定、FinanceRecord の
  必須化、Box/SF オブジェクト型の固定化等)は v0.3 以降で扱う。

## 検証(機械化)

- stdlib のみの検証器: `tools/workflow_event/`(`jsonschema` 非依存)。
- `tools/workflow_event/tests/` で「examples_v0.2.jsonl 全件 green」+
  ネガティブテストを固定。CI(`.github/workflows/ci.yml`)に pytest ステップを
  `tools/worker_queue` の隣に追加済み。

## 残課題 / 未確認(queue 起票候補)

- 実査未完: SourceRef.system / object_type の値域、FinanceRecord の必須項目、
  Box 正本パスの命名規約は **未確認**。v0.3 で実査知見を反映する。
