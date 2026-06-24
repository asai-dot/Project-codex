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

---

<!-- ===== 追記 START: W-20260624-160 (v0.1→v0.2 全成果反映・上書きせず追記) ===== -->

# CHANGELOG v0.1 → v0.2 — リリース全体（追記: W-20260624-160）

> 上記までは W-20260624-120 が記録した **イベント封筒スキーマの差分**（保守的デルタ）。
> 本節は v0.2 リリース **全成果物の v0.1→v0.2 差分**を、上書きせず追記したもの。
> v0.1 原本（`../v0.1/` の4ファイル）は読むだけ・無改変。スキーマ節の記述は維持する。

## A. v0.2 で新規作成した成果物（v0.1 に無かったもの）

| 成果物 | 内容 | 作業票 |
|---|---|---|
| `ALO_WORKFLOW_CURRENT_STATE_v0.2.md` | v0.1 構造インベントリ（23フロー/245問/22データ源/35文書/72イベント/53状態/SF対応44/決定14 の実抽出棚卸し＋仮説/確定/未決分離） | W-101 |
| `PHASE1_question_triage_v0.2.csv` / `_summary_v0.2.md` | 245問を5区分にトリアージ。P0 58問を status 別に分類（回答済0/暫定42/浅井11/中森3/外部SE2） | W-102 |
| `PHASE2_box_document_lifecycle_v0.2.md` | Box read-only メタデータ実査。12対象のライフサイクル状態区別マトリクス＋Raw/Canonical/Derived萌芽 | W-111 |
| `ALO_WORKFLOW_EVIDENCE_LEDGER_v0.2.jsonl` | Gmail 3トレース（受任到達/失注/解決→第三者支払者精算）を event 封筒で匿名抽出 | W-112 |
| `ALO_OWNER_GRILL_PACK_v0.1.md` | 浅井先生 裁定パック。初回 P0 20問（G-01〜G-20・裁定型）＋ §2 後続キュー全保持 | W-140 |
| `alo_workflow_event_schema_v0.2.json` / `_examples_v0.2.jsonl` | イベント封筒スキーマ v0.2（上記スキーマ差分節を参照） | W-120 |
| `ALO_WORKFLOW_GAP_AND_POC_PLAN_v0.2.md` | ギャップ分析＋PoC1/PoC2（対象・KPI・close gate 10項目）＋依存/ブロッカー＋次アクション | **W-160（本票）** |
| `CHANGELOG_v0.2.md` | 本ファイル（スキーマ差分＋本全体差分） | W-120 / **W-160 追記** |

## B. v0.1 → v0.2 の主な前進（差分の要点）

1. **棚卸し（Phase0）**: v0.1 原本の実数を全件再抽出し検算。原本内の不整合を2点検出 — (i) 状態機械「5本実定義 vs 7本言及」（Delivery/Deadline）、(ii) KPI「要確認フロー20 vs 22+1」。推測で潰さず未決として明示。
2. **トリアージ（Phase1）**: 245問の「どの手段で埋まるか」を機械的に割当（実データ133/既存資料3/実物30/聴取28/設計判断51）。回答は作らず、捏造（`回答済`の付与）を回避。
3. **Box実査（Phase2）**: read-only で 12対象のライフサイクルを観測。状態が「フォルダ配置・命名動作語・docx/pdfペア・version」の4手段で**自然発生的に**表現されること、Derived層（`_alo_*`）の萌芽を確認。書込/移動/改名/削除なし。
4. **Gmail実証（Phase2）**: 3トレースで client/payer 分離・append-only封筒・state_transition basis(observed/declared) を実装実証。同時に due_at/completion_evidence 全件null = 自然発生データだけでは期限/完了証跡が埋まらないことを実証。
5. **裁定パック（§4）**: 実査で埋まらない論点だけを 20問の裁定型に蒸留。調査で埋まる質問・SF実査待ち項目は §2 へ隔離。
6. **GAP & PoC（§6・本票）**: 目標12分解単位・5/7状態機械・provenance・HITL に対する現状ギャップをデータ源別に整理。PoC1/PoC2 の KPI と close gate 10項目を「確認データ源」付きで定義。W-110 BLOCKED の PoC への影響を明示。

## C. ブロッカー・前提の確定（v0.2 で判明）

- **W-20260624-110（SF/LEALA実査）= WORKER_BLOCKED**: 本環境に Salesforce/LEALA/Dialpad/Notta/MoneyForward の接続コネクタが無い。よって制御塔状態・通話・会計の3本柱が未観測。PoC1 KPI の半数、PoC2 close gate の6項目が現状判定不能。`blocked/` に隔離し、解消後 `inbox/` 再投函で再開。
- 実査できたのは **Box・Gmail の2源のみ**。SF実査の解消が PoC1/PoC2 双方の必要条件であることを確定。

## D. 意図的に変更しなかったもの / v0.3 送り

- v0.1 原本4ファイルは無改変（読むだけ）。
- イベント封筒スキーマの $defs 構造・required は v0.1 維持（上記スキーマ節）。
- 実査台帳 9シートへの反映（W-130）は depends_on=W-110/111/112 のため **SF実査解消後**に実施（本 v0.2 時点では held）。
- CATALOG_v0.2.yaml（W-150）の states/transitions/close gate/KPI 確定は裁定＋SF実査の後。
- SourceRef 値域・FinanceRecord 必須化・Box正本命名規約・状態機械5/7本確定は v0.3。

## E. 残課題 / queue（推測で埋めず確認要）

1. 浅井グリル20問の裁定（特に PoC を左右する G-01/04/05/06/08/09/10/12/14/15/20）。
2. SF/LEALA 実査の解消（W-110）＋ Dialpad/Notta/MF 接続。
3. W-130 台帳反映 → 再 catalog（W-150）→ PoC 計測実装。
4. 未確認の Box 論点: 相談票単票形態(U1/G-14)、終了報告書ひな形(U2/G-15)、到達/受理/入金の正本(U3/G-11)、`~BROMIUM`(U4/G-18)、version運用の一貫性(U5)。

<!-- ===== 追記 END: W-20260624-160 ===== -->
