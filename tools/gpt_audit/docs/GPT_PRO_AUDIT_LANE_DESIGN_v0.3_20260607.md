<!--
SoT 注記: この文書の正本(canonical)は Box の gpt_ometsuke/ にあります。
  Box file: GPT_PRO_AUDIT_LANE_DESIGN_v0.3_20260607.md (file_id 2269736541410)
本ファイルは実装 (tools/gpt_audit/ の alo-gpt-audit) と spec を一緒に運ぶための mirror です。
内容に差異が出た場合は Box 版を優先してください (Box=canonical, repo=mirror)。
-->

# GPT Pro 目付け役 監査レーン設計 v0.3

- date: 2026-06-07 JST
- author: GPT-5.5 Pro lane / ALO（番頭代行: Claude Code）
- status: design proposal / operations spec（candidate）
- supersedes: GPT_PRO_AUDIT_LANE_DESIGN_v0.2_20260606.md (2269085336900 → 旧版は `_old/` 退避推奨)
- companion(語彙正本): DD-STATUS-REGISTRY-001 candidate v0.2 (2269071863810) + redline v0.2 (2269074944869)
- implementation: `alo-gpt-audit` CLI（Project-codex リポジトリ `tools/gpt_audit/`）
- scope: `gpt_ometsuke/` 配下の GPT Pro 監査の行き・帰り・**反映**処理
- design principle（不変・v0.2継承）: **フォルダ位置を状態にする。`to_gpt/` 直下は未回答だけ。**

---

## changelog v0.3

v0.2 の **フォルダモデル・中核ルール・三点照合は不変**。v0.3 は次を足す/直す。

1. **§A 語彙アライン**: 監査レーンの状態語彙を DD-STATUS-REGISTRY v0.2 に整合させる。
   レーンの状態は **artifact lifecycle（軸A 7語）ではなく runtime/pipeline 状態**であると明示。
2. **§D 反映キュー（action queue）を正式採用**: 退避で終わらせず、RESULT を消化する next_action を持つ。
   → 「監査結果が返っただけで設計に反映されない」事故を構造的に潰す（v0.2 の最大の穴）。
3. **§E NEED_MORE 細分**: `need_more_type` を導入（material_absent 等）。
4. **§F PASS_WITH_NOTES 厳密化**: notes を blocking / non-blocking に分割。
5. **§G REQUEST preflight 強化**: `review_scope` / `regression_anchors` / `decision_requested` /
   `target_mode` / `source_hash` を T2 必須化（`alo-gpt-audit lint`）。
6. **§H 実装リファレンス + 検収**: `alo-gpt-audit` の status/close/close-all/action-queue/lint と TEST-1〜6。

---

## A. 語彙アライン（v0.3 の核）— レーン状態 ≠ artifact lifecycle

DD-STATUS-REGISTRY v0.2 §2.A は **artifact lifecycle** を 7語に限定する:
`draft / candidate / conditional_accept / accepted / canonical / superseded / withdrawn`。

監査レーンが扱う状態は、この lifecycle とは**別の軸**である。混同を避けるため名前空間を分ける
（codexprogress DDPROGRESS_PASS_WITH_NOTES の GPT 指摘 #2「runtime_status と lifecycle_status を別列に」と同趣旨）。

| レーンの概念 | 名前空間 | 値 | DD-STATUS との関係 |
|---|---|---|---|
| REQUEST の処理状態 | `request_status` | `queued / blocked / superseded / cancelled` | **lifecycle ではない**。GPT が読むべきかの runtime フラグ |
| REQUEST の位置 | `lane_status` | `active / blocked_active / answered_not_processed / duplicate_in_processed / processed_without_result` | **lifecycle ではない**。フォルダ位置＝pipeline 状態 |
| RESULT の判定 | `result_label` | `<GATE>_{PASS,PASS_WITH_NOTES,MODIFY_REQUIRED,FAIL,NEED_MORE}` | 監査意見。**それ自体は artifact lifecycle を動かさない**（§C） |
| RESULT 後の作業 | `next_action_type` | `ratify / patch / required_materials / reject / none` | ここで初めて lifecycle 遷移（candidate→accepted 等）に接続 |

**鉄則**: `to_gpt/processed/` への退避は artifact を `accepted` にしない。退避は
「GPT 照会 1 回分は回答済み」という **pipeline 状態**にすぎない。artifact lifecycle の昇格は
DD-STATUS-REGISTRY §3 の遷移ゲート（candidate→accepted は **GPT Pro T2 + 浅井先生 ratify**）に従う。

---

## B. request_status の語彙（runtime, 非lifecycle）

front-matter の `status:` は request_status であり、lifecycle 語を入れない。

| value | 意味 | GPT処理 |
|---|---|---|
| `queued` | 監査可能 | レビューして RESULT 作成 |
| `blocked` | 対象不在・情報不足 | 原則 `<GATE>_NEED_MORE` だけ返す（§E） |
| `superseded` | 後続 REQUEST に置換 | レビューせずスキップ可 |
| `cancelled` | Owner/番頭が取り下げ | レビューしない |

---

## C. result_label → next_action_type → lifecycle 遷移

RESULT は**監査意見**であって DD 正本ではない。3段を分離する（v0.2 §8 を構造化）。

```text
1) GPT RESULT (監査意見, result_label)
      ↓ 番頭が反映
2) Patch / Accepted Body (設計本文)
      ↓
3) Owner Ratify (浅井先生) → artifact lifecycle: candidate → accepted
```

| result_label | next_action_type | ratify_required | requeue_expected | lifecycle への作用 |
|---|---|---|---|---|
| PASS | ratify | true | false | ratify 後 candidate→accepted |
| PASS_WITH_NOTES | ratify | true | false | blocking notes 反映後に ratify（§F） |
| MODIFY_REQUIRED | patch | false | true | 新 version で再投函（§9）。昇格しない |
| FAIL | reject | false | false | 別案起票。昇格しない |
| NEED_MORE | required_materials | false | true | 資料補充して再投函（§E）。昇格しない |

---

## D. 反映キュー（action queue）— 監査の出口

`from_gpt/` に RESULT を置くだけでは足りない。RESULT を読み next_action を生成する層を持つ。
Box フォルダは増やさず、台帳 `_AUDIT_LEDGER.jsonl` の next_action 項目と
`alo-gpt-audit action-queue`（台帳派生ビュー）で実現する。

退避済み（`processed_done`）の RESULT も消化対象として出し続ける。退避＝反映済みではないからである。

台帳の反映キュー項目（最小）:
```yaml
request_id:
result_label:
next_action_type: ratify | patch | required_materials | reject | none
ratify_required: true|false
requeue_expected: true|false
need_more_type: <§E>
missing_materials: []
blocking_before_ratify: []   # §F
reflected: false             # 反映完了で true 化（人手 / 後続ツール）
```

`reflected:false` が残る限り、監査は閉じていない。

---

## E. NEED_MORE の細分（need_more_type）

NEED_MORE は最低 4 種に分ける。番頭の次アクションが一意に決まる。

| need_more_type | 意味 | 次アクション |
|---|---|---|
| `material_absent` | 対象ファイルが Box 不在 | Box 復旧 → 再投函 |
| `context_insufficient` | ファイルはあるが文脈不足 | REQUEST 補充 → 再投函 |
| `evidence_unverified` | 主張の根拠不足 | 実測・出典追加 → 再投函 |
| `ambiguity_owner` | Owner 判断が必要 | 浅井先生判断 |

RESULT 本文に `need_more_type:` と `missing_materials:` を書く。
（例: quasijudicial v0.4 = `material_absent`。対象正本5点が docs/alo 不在。）

---

## F. PASS_WITH_NOTES の厳密化

PASS_WITH_NOTES は「ほぼPASS」と誤読されやすいが、notes に accepted 化前必須の修正が混じりうる。
RESULT 本文で notes を 3 層に分ける。

```yaml
notes:
  blocking_before_ratify:     # ratify 前に必ず反映
    - ...
  non_blocking_after_ratify:  # ratify 後でよい
    - ...
  optional:
    - ...
```

`blocking_before_ratify` が空になるまで accepted 化しない。
（例: claudehead = 第二Anthropic を hand/capacity と書く・head 落ち時 fallback 明記 が blocking。）

---

## G. REQUEST preflight 強化（監査スコープ境界 / target_mode）

T2（accepted化・規範新設・本番投入前）の REQUEST は front-matter に次を必須とする（`alo-gpt-audit lint`）。

```yaml
review_scope:
  include: [ 今回見てほしい差分 ]
  exclude: [ 既に確定・蒸し返さない事項 ]   # exclude が特に重要
regression_anchors:
  - accepted/canonical の Box ID（矛盾してはいけない決定）
decision_requested:
  - PASS可否 / accepted化可否 / backfill可否
target_mode: inline_embedded | box_hash_locked | box_pointer_only
source_hash: sha1:...        # unresolved を弾く
```

`target_mode` 推奨: T0=`box_pointer_only` / T1=`box_hash_locked` / T2=`inline_embedded` か `box_hash_locked`。
T2 REQUEST 投函時に Box ID・sha1・サイズ・modified_at を検査してから出す
（quasijudicial の対象不在事故は T2 で痛い）。

---

## H. 実装リファレンス（alo-gpt-audit）と検収

実装は Project-codex `tools/gpt_audit/`（依存ゼロ Python CLI）。root は Box Drive 同期パス
または Box API。**単一書き手**が退避を実行する。

```text
alo-gpt-audit status         # 三点照合でレーン状態（読み取り）
alo-gpt-audit close <id>     # RESULT照合・ラベル検査・request_id照合 → processed退避 → 台帳追記
alo-gpt-audit close-all      # answered_not_processed を一括退避（既定 dry-run, --apply で実行）
alo-gpt-audit action-queue   # 反映キュー（§D）
alo-gpt-audit lint           # REQUEST preflight（§G）
```

検収（受け入れ基準）:

| test | 内容 |
|---|---|
| TEST-1 status | answered_not_processed を正しく数える |
| TEST-2 dry-run | 退避予定表示・NEED_MORE/MODIFY も対象・何も動かさない |
| TEST-3 execute | REQUEST→processed、to_gpt直下0、from_gpt RESULT残置 |
| **TEST-4 idempotency** | **再実行で二重移動・二重台帳追記しない** |
| TEST-5 missing-result | RESULT 無し REQUEST は移動しない |
| TEST-6 bad-label | 先頭行が不正な RESULT は移動しない |

---

## I. v0.2 から不変の条項

- フォルダ責務（to_gpt / from_gpt / processed）。
- 完了条件: RESULT作成 + ラベル検査 + REQUEST退避。
- 二重回答防止の三点照合（§6 判定表）。
- 再投函は元 REQUEST を復活させず新 version を作る（`supersedes_request_id`）。
- 権限・守秘: 設計・仕様・DDL・監査パケットに限定。実依頼者情報は Owner 承認・匿名化・最小化。
- 状態の SoT はフォルダ位置とファイル実体。台帳は派生控え。per-artifact lifecycle の SoT は
  ALO_CANONICAL_INDEX（2266253855296）。

---

## J. 結論

v0.2 の中核「`to_gpt/` 直下は未回答だけ」に、v0.3 は**出口**を足した。

> RESULT を返したら REQUEST を退避する。**だが退避は反映ではない。**
> 反映キューの `reflected:true` と、lifecycle の `accepted`（Owner ratify 経由）まで到達して、監査は初めて閉じる。

そして監査レーンの状態語彙は、DD-STATUS-REGISTRY v0.2 の lifecycle とは別軸の runtime 状態である、と固定した。
