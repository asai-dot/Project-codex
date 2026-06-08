# GPT_OMETSUEKE_QUEUE_PROTOCOL v0.2

- date: 2026-06-08 JST
- status: operations spec / candidate（git 実装）
- scope: `handoffs/gpt_ometsuke/` 配下の GPT お目付け役監査の **状態管理**（行き・帰り・消費・反映・closed）
- design_source: GPT 試作 `GPT_OMETSUEKE_QUEUE_PROTOCOL_v0.2.md`（SHA-256 `75d420ec96ebec8a9c9a67d5791bf6b3b1d6019b076b1f0df54dffad227b8509`）
- implementation: `tools/gpt_audit/queue.py`（依存ゼロ Python）
- 目的: **監査キューの状態管理を安定化する**こと。GPT 監査の品質向上が目的ではない。

> v0.2 は完全自動化の仕様ではない。状態定義・完了定義・Claude/GPT/浅井さんの責務分界を**固定する**ことが目的。
> 常時監視 daemon / GPT 自動送信 / Box 自動 move・delete / Web UI / DB 化 / 自動通知は **v0.3 送り**。

---

## 0. なぜ二層にするか

`QUEUE_INDEX.md` だけを正本にしない。表を誰かが書き換えた瞬間に「なぜそうなったか」が消えるからである。
代わりに二層にする。

```text
QUEUE_EVENTS.jsonl  = append-only の状態変更ログ。後から監査できる履歴。これが真実。
QUEUE_INDEX.md      = 現在状態を見るための人間・AI 向け台帳。EVENTS からの派生。手で書かない。
CONSUMED.md         = GPT RESULT を Claude が読んで採用/不採用/反映内容まで記録したもの。派生。
```

INDEX と CONSUMED は `python3 tools/gpt_audit/queue.py build` で EVENTS から決定論的に再生成する。
食い違いは `queue.py check` が検出する（生成物の手編集 / 再生成忘れを弾く）。

---

## 1. v0.2 で固定した 5 点

1. **未済を 4 分類する** — 未監査 / 未消費 / 未反映 / 浅井判断待ち（§3）。
2. **RESULT 返却だけでは closed にしない**（§4）。
3. **CONSUMED.md** — Claude が RESULT を読んだ証跡を残す。読んだだけでなく採用/不採用/反映内容まで（§5）。
4. **closed の条件を厳格に定義する**（§4）。
5. **状態報告** — 浅井さんから「監査溜まってない？」「未済ない？」と聞かれたら、件数分類で答える（§6）。

つまり次を別状態として切る。

> GPT は返したのか？（未監査 ↔ あり）/ Claude は読んだのか？（未消費 ↔ 消費済）/
> 読んだとして反映したか？（未反映 ↔ 反映済）/ 反映しないなら理由を残したか？（CONSUMED.md）/
> 本当に閉じていいか？（closed の厳格定義）

---

## 2. フォルダと命名（v0.1 / Box v0.3 から継承・不変）

- `to_gpt/`            … Claude→GPT。レビュー/監査の**依頼**（現物同梱）を置く。
- `to_gpt/processed/`  … GPT が処理し終えた REQUEST の退避先。
- `from_gpt/`          … GPT→Claude。**結果**（5ラベル+指摘）を書き戻す。

- 依頼: `<YYYYMMDD>_<topic>_<gate>_REQUEST.md`
- 結果: 同じ stem で `..._RESULT.md`、先頭行 = `<GATE>_<LABEL>`
- ラベル5種: `PASS / PASS_WITH_NOTES / MODIFY_REQUIRED / FAIL / NEED_MORE`
- `<gate>` は REQUEST ごとに異なる（`G0` / `DDLAWTIME` 等）。取り込み側は固定 `G0_` で読まない。

**鉄則（Box v0.3 §J 継承）**: `to_gpt/processed/` への退避は反映ではない。退避＝「GPT 照会 1 回分は回答済み」という
pipeline 状態にすぎず、artifact を accepted にしない。

---

## 3. 未済の 4 分類（状態語彙）

`request_id` ごとに EVENTS を畳み込んで現在状態を一意に決める。

| 状態 | 意味 | 何が揃っていないか |
|---|---|---|
| **未監査** | REQUEST はあるが GPT RESULT 未着 | `RESULT_RETURNED` が無い |
| **未消費** | RESULT はあるが Claude が読んで判断していない | `CONSUMED` が無い |
| **未反映** | 消費済だが設計反映 / 再投函 / 資料補充が未完 | `REFLECTED` が無い（要反映の場合） |
| **浅井判断待ち** | 反映済だが浅井先生の ratify 待ち | `RATIFIED` が無い（ratify 要の場合） |
| **closed** | 反映（+ratify）まで到達して閉じた / 後続に置換 | — |

NEED_MORE は `need_more_type` で細分する（Box v0.3 §E）: `material_absent` / `context_insufficient` /
`evidence_unverified` / `ambiguity_owner`。資料補充が要るものは「未反映」に入り、`reflected` まで残り続ける。

---

## 4. closed の厳格定義（v0.2 の核）

RESULT があるだけでは **絶対に** closed にしない。`request_id` が closed になるのは次のいずれか。

1. **正常クローズ** — 以下を**すべて**満たす:
   - `RESULT_RETURNED` がある、かつ
   - `CONSUMED`（採用判断）がある、かつ
   - 反映が要るなら（adopt/partial/defer で `requires_reflection=true`）`REFLECTED` がある、かつ
   - ratify が要るなら（`ratify_required=true`）`RATIFIED`（浅井先生）がある。
2. **不採用クローズ** — `CONSUMED` の `disposition=reject` かつ ratify 不要。理由は CONSUMED.md に残る。
3. **置換クローズ** — `REQUEUED`（`superseded_by` を持つ新 version に置換）。
4. **事務的クローズ** — `CLOSED` イベント（重複保存の統合 等、`reason` 必須）。

この判定は `queue.py` の `classify()` が機械的に適用する。`test_queue.py` の
`test_result_alone_never_closed` がこのルールを固定している。

---

## 5. CONSUMED — Claude の採用判断記録

GPT RESULT を Claude が処理したら、必ず `CONSUMED` イベントを 1 件残す。記録項目:

- `disposition`: `adopt`（採用）/ `partial`（一部採用）/ `defer`（保留・資料補充）/ `reject`（不採用）
- `requires_reflection`: 設計本文反映 / 再投函 / 資料補充が要るか
- `ratify_required`: 浅井 ratify が要るか
- `summary_owner`: GPT 結論の要旨（横目確認用）
- `summary_claude`: **反映内容 / 次アクション / 不採用なら理由**

CONSUMED.md はこれらを request_id ごとに一覧化した派生ビュー。
「読んだのに反映していない」「不採用にした理由が残っていない」事故を構造的に潰す。

---

## 6. 状態報告（「監査溜まってない？」への答え方）

浅井さんから「監査溜まってない？」「未済ない？」「回ってる？」と聞かれたら、**作業報告ではなく状態報告**で返す。
コマンド 1 つで件数分類が出る。

```bash
python3 tools/gpt_audit/queue.py report
```

出力例（2026-06-08 シード時点）:

```text
監査キュー状態報告 (全 25 件 / 未済 14 件 / closed 11 件)
  未監査: 0 件  [—]
  未消費: 0 件  [—]
  未反映: 6 件  [...]
  浅井判断待ち: 8 件  [...]
  closed: 11 件
```

浅井さんへの返答テンプレ（5 行・横目確認用 / Box loop rule §5 と整合）:

```text
状態: 全N件 / 未済M件
未監査: a件 / 未消費: b件 / 未反映: c件 / 浅井判断待ち: d件
今あなたの番: <浅井判断待ちの topic 列挙、無ければ「なし」>
今 Claude の番: <未反映の topic 列挙>
今 GPT の番: <未監査の topic 列挙、無ければ「なし」>
```

---

## 7. イベント運用（append-only）

EVENTS は追記専用。**行を書き換えない・削除しない**。状態を変えるときは新しいイベントを足す。

```bash
# REQUEST を to_gpt/ に置いたら
python3 tools/gpt_audit/queue.py append --event REQUEST_CREATED \
    --request-id 20260608_foo_v0.1_G0 --actor claude --topic foo --gate G0

# GPT が RESULT を返したら
python3 tools/gpt_audit/queue.py append --event RESULT_RETURNED \
    --request-id 20260608_foo_v0.1_G0 --actor gpt --label G0_PASS_WITH_NOTES \
    --result-file-id 22XXXXXXXXXX --summary-owner "..."

# Claude が読んで判断したら（採用・要反映・要ratify）
python3 tools/gpt_audit/queue.py append --event CONSUMED \
    --request-id 20260608_foo_v0.1_G0 --actor claude --disposition adopt \
    --requires-reflection true --ratify-required true \
    --summary-claude "blocking 2点を本文反映後 ratify へ"

# 反映完了 / 浅井 ratify
python3 tools/gpt_audit/queue.py append --event REFLECTED  --request-id ... --actor claude
python3 tools/gpt_audit/queue.py append --event RATIFIED   --request-id ... --actor asai

# 追記したら必ず再生成
python3 tools/gpt_audit/queue.py build
```

イベント種別: `REQUEST_CREATED / RESULT_RETURNED / CONSUMED / REFLECTED / RATIFIED / REQUEUED / CLOSED / REOPENED`。

---

## 8. 責務分界（Claude / GPT / 浅井さん）

| 主体 | やること | やらないこと |
|---|---|---|
| **Claude（番頭）** | REQUEST 作成 / RESULT 消費(CONSUMED) / 反映(REFLECTED) / 再投函(REQUEUED) / 状態報告 | accepted 化・本番投入の最終決裁 |
| **GPT（お目付け役）** | RESULT 返却（5ラベル + 指摘） | 設計本文の確定 / closed 判定 |
| **浅井さん** | T2 起動指定 / ratify（accepted 化等の決裁） | コピペ運び屋・件数の手集計 |

監査レーン内の事務（RESULT 保存・processed 退避・台帳追記）は Owner 承認不要（Box approval rule v0.1）。
Owner 承認が要るのは accepted/canonical 昇格・Generated Index backfill・本番 DB 投入・外部送信・SF 書戻し。

---

## 9. crosswalk — Box v0.3 レーンとの対応

このリポジトリの v0.2 は、Box `handoffs/gpt_ometsuke/` の既存 v0.3 レーンと**同一概念を git 側に実装したもの**。
別物の並行システムではない。名前の対応は次のとおり。

| v0.2（本リポジトリ / git） | Box v0.3 レーン | 備考 |
|---|---|---|
| `QUEUE_EVENTS.jsonl` | `_AUDIT_LEDGER.jsonl` | append-only。真実 |
| `QUEUE_INDEX.md` | `_ACTION_QUEUE.md` | 派生ビュー（件数分類） |
| `CONSUMED.md` | ledger 内 `reflected`/`owner_digest_5line`/`claude_rethink_prompt` | v0.2 で独立ファイル化 |
| 未監査/未消費/未反映/浅井判断待ち | `lane_status` / `next_action_type` / `loop_state` | `reflected:false` ⇔ 未反映 |
| closed 厳格定義（§4） | loop rule §6 + design §J「退避は反映ではない」 | 同趣旨を機械化 |
| `queue.py` | `alo-gpt-audit`（`tools/gpt_audit/`） | 設計書記載の置き場に実装 |

参照（Box file_id）: `GPT_PRO_AUDIT_LANE_DESIGN_v0.3`(2269736541410) / `GPT_PRO_AUDIT_LOOP_RULE_v0.1`(2270127270632)
/ `GPT_PRO_AUDIT_LANE_APPROVAL_RULE_v0.1`(2269668752427) / `_AUDIT_LEDGER.jsonl`(2271040382325) /
`_ACTION_QUEUE.md`(2271025917499) / `PROTOCOL.md`(2266009787864)。

> **正本の最終決定は浅井さん保留事項。** Box を正本とする ALO 原則（Box=正本 / Drive=ミラー / SF=統制塔）に従い、
> 現状この git 実装は **v0.3 レーンと突き合わせ可能な実装・シードのリファレンス**として置く。
> v0.2 git を新正本とするか、Box ledger に統合するかは浅井さんが決める。

---

## 10. 守秘

置けるのは **設計・仕様・DDL・監査パケットのみ**。実案件データ・実認証情報・依頼者個人情報は置かない（匿名化）。
セキュリティ・マーカー（例 `★は＿パスワード`）は実シークレットではないが、実シークレット本体は絶対に置かない。
