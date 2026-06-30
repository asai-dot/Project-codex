# DD-ORCH-CONTINUITY-001 v0.3 — Head↔Owner 決定ログ（航海日誌）と head 交代継続性

- decision_id: **DD-ORCH-CONTINUITY-001**
- status: **RATIFIED (design)** — owner ratify 2026-06-30 / GPT `DESIGN_PASS_WITH_NOTES`（RESULT 2318022243805）。
  ratify_record: `docs/alo/RATIFY_DD-ORCH-CONTINUITY-001_v0.3_20260630.md`
- binding notes（実装遵守・正は ratify_record §Binding notes）:
  ①`REJECT_REQUIRED_STANDING_OMITTED` は `required_log_commit` 時点の active global_required で評価
  ②worker が新しい `read_log_commit` を読んでも `read_digest_id` は `required_digest_id` と一致させる
  ③旧 field alias 禁止 ④`REJECT_INLINE_HISTORY` は初期実装で保守的 heuristic 可 ⑤本ログは設計判断正本でない
- 起案: head (Claude Code) / 2026-06-30
- 種別: DESIGN（設計のみ。実装は owner GO 範囲の最小差分のみ・production/外部/DB/canonical は HOLD）
- version: **v0.2 → v0.3**。v0.2 は `DESIGN_MODIFY_REQUIRED`（RESULT file_id 2317980241576）を反映:
  ①§3.6 `REJECT_STALE_LOG_COMMIT` の祖先関係が逆向きだった致命バグを修正（accept = 発注時 commit が worker 読了 commit の**祖先**）
  ②field 名の揺れを正本語彙に統一 ③standing に `enforcement` scope(global_required/task_scoped/informational) 付与。
  v0.1→v0.2 の差分は §9。
- スコープ: プロジェクト横断（雑誌/判例/法令/語彙 等 全スレ共通の運用基盤）
- 親規約: `docs/alo/AGENT_ORG_AND_ROUTING.md` / `docs/periodical/HEAD-ORDER-PROTOCOL.md`
- prior art（既決・矛盾不可）: `ALO-HEAD-HAND-HANDOFF-20260619`
  = `HEAD_HAND_HANDOFF_DESIGN v0.5`（**RATIFIED design 2026-06-23**）＋ `handoff_operational_impl v0.1`（PASS_WITH_NOTES）

---

## 0. 一行要約

Head↔owner(浅井) の対話に宿る「**意図・経緯・恒久制約**」を、`HEAD_OWNER_LOG.md` に蒸留して外部化し、
(a) head が data limit 等で落ちたとき**代理 head が文脈ごと継げる**、(b) **ワーカーが発注の裏の "なぜ" を読める**状態を作る。
v0.2 では **「信用ではなく照合」**＝ ID(digest_id/standing_id) と commit による機械照合で、
「更新されない航海日誌が新たな単一障害点になる」失敗を fail-safe で塞ぐ。

---

## 0.5 既存系列との関係（prior art・線引き — 重複でなく補完）

`ALO-HEAD-HAND-HANDOFF-20260619`（v0.5 が 2026-06-23 RATIFIED）は、本 DD と**同じ根の公理**から出発する:

> **H1（既存設計）: シームは直列化境界。アーティファクトに書かれない文脈は渡らない。**

既存はこの H1 を **head→hand の「1タスクの作業パケット」** にのみ適用する（thin index＋fat packet・
governance/execution role 分離・3軸 fail-closed effect・packet-hash・per-attempt reconciliation）。
**owner は gate metadata（`owner_pending`/ratify）としてしか登場せず**、owner 対話の意図や head 交代継続は射程外。

本 DD は同じ H1 を、既存が touch しない**別レイヤ**へ拡張する:

| 軸 | 既存 `HEAD-HAND-HANDOFF`（RATIFIED） | 本 DD `ORCH-CONTINUITY` |
|---|---|---|
| 対象 | **1タスクの dispatch パケット**（head→hand）| **永続する意図・恒久決定**（head↔owner、全タスク横断）|
| 形式 | 機械可読・hash・gated・schema 正本 | 人間/AI 可読の散文ログ（hash 無し・gate 対象外）|
| 粒度 | per-task（投下のたび）| per-session 蒸留（恒久＋直近30）|
| 解く失敗 | 過少記述/過結合/肥大による「シーム出血」| head交代の意図断絶(F1)/ワーカーの意図不知(F2)|

**接続は "参照キー" に限る（MF-3 / SF-4・H1 整合）**: 既存設計は「intent を packet に inline すると**肥大**して
H1 の失敗モードに陥る」と明示する。よって per-task packet は HEAD_OWNER_LOG を**次のキーでのみ参照**し、
owner/head の会話履歴を**長文 inline しない**:

```
per-task dispatch packet may reference HEAD_OWNER_LOG only by:
  - log_commit        (どの版を見たか)
  - digest_id         (HOL-YYYYMMDD-NNN)
  - standing_id       (HOS-NNN)
  - optional reason_ref
per-task packet MUST NOT inline long owner/head conversation history.
```

本 DD は既存の dispatch schema・role/effect 軸・gating には**一切触れない**（accepted・本 DD のスコープ外）。

---

## 1. 解こうとしている問題（Why）

プロジェクトの記憶は3か所にあるが、いずれも「意図」を保持しない:

1. **ORCH-*.md 発注書** — 「何を・受入基準」は書くが「なぜ・経緯」は書かない。
2. **git コミット履歴** — 結果の監査証跡。意図は断片的で横断検索しないと辿れない。
3. **走っている head(Mac CC)の会話コンテキスト** — 「なぜ」が最も濃く宿るが、
   **data limit ヒットや別マシン交代で消滅**（約30セッション分が揮発）。

事故モード:

- **F1（継続性の断絶）**: head 停止 → 代理 head が進行中タスク・保留判断・方針転換を継げない。
- **F2（ワーカーのローカル最適暴走）**: ワーカーが ORCH の字面しか見ず、owner が会話で示した
  優先順位・禁止を知らず「局所最適だが戦略的に誤り」の判断をする。

---

## 2. 確定済み前提（変更不可・監査の枠）

- 既存 `AGENT_ORG_AND_ROUTING.md`／`HEAD-ORDER-PROTOCOL.md`（やり方担当）を置換しない。本 DD は「今どこ・なぜ」担当。
- **`HEAD_HAND_HANDOFF_DESIGN v0.5`（RATIFIED）と矛盾しない**。dispatch schema・role/effect 3軸・gating を一切変更せず、
  packet 外に出した永続 intent の置き場を定義する補完層。
- **設計判断の正本は別**: 本ログは「運用継続性のための蒸留ログ」であり、設計判断正本 `90_design_decisions.md`（あれば）とは別物（SF-1）。
- 常駐デーモンは増やさない（owner 決定 2026-06-29: コスト過大）。新ポーリング不可。
- 共有ブランチへ force push 禁止。canonical 昇格・DB投入・外部公開は owner GO。本ログは参照系運用文書。

---

## 3. 提案設計（What）

### 3.1 成果物: `docs/alo/HEAD_OWNER_LOG.md`（append-only・スレ非依存・単一の真実）

```
A. STANDING（恒久の決定・好み・禁止）   ← active 最大20項目・各3行以内（MF-4）
   - standing_id: HOS-001
     rule: force push 禁止
     applies_to: all branches      # 適用対象（旧 scope。enforcement と区別）
     enforcement: global_required  # global_required | task_scoped | informational
     status: active                # active | retired
     last_confirmed: 2026-06-29
     owner_ratified: yes           # owner ratify 要の項目のみ yes/no（SF-2）
   ※ enforcement の意味:
       global_required = 全タスクが required に含め read+check 必須（欠落は ORCH を REJECT）
       task_scoped     = ORCH が指名したタスクのみ required
       informational   = 参考。未読でも REJECT しない
   ※ active が20を超えたら統合・retire・archive を先に行う。retired は archive_index に残し active 読了 set から外す（SF-3）。

B. SESSION DIGESTS（新しい順・直近~30件）   ← 1件5行程度（MF-2）
   - digest_id: HOL-20260629-001
     trigger: policy_decision      # policy_decision | handoff_review | owner_pending
     summary: storm対策は wake_worker の cap ゲートのみ採用、reapデーモンは塩漬け
     reason: 常駐はコスト過大
     related_orch: (なし)
     related_commit: <sha>
     owner_pending: no

C. archive_index（本体に残す薄い索引・SF-3）
   - HEAD_OWNER_LOG_archive_202606.md: HOL-20260601-001 .. HOL-20260629-030
```

- **A は蒸留、B はローリング、C は索引のみ**。30件超の digest は archive へ退避し、本体は薄く保つ。
- **owner は書かない**。head が会話の副産物として追記（3.2）。owner ratify 要の STANDING のみ `owner_ratified` を持つ。

### 3.2 更新トリガ（運用クセ）

head は次の3つの瞬間にだけ digest を1件（5行）追記し push:

1. owner 議論が一区切りして**方針が決まった**直後（trigger=policy_decision）
2. ハンドへ**発注 / 検収**した直後（trigger=handoff_review。必要なら STANDING 更新）
3. **owner 判断待ちが発生**した直後（trigger=owner_pending・`owner_pending: yes`）

### 3.3 ワーカーへの導線（読了を ID で照合・MF-2）

- `CLAUDE.md` に追加: 「**着手前に `HEAD_OWNER_LOG.md` の STANDING＋直近数件を読み**、
  発注が要求する `required_standing_ids` を確認する」。
- `wake_worker.sh` 生成プロンプト冒頭に同指示を1行差込（既存改修のみ・新デーモン不要）。
- **読了は自然言語でなく ID で証跡化**（後述 3.5）。

### 3.4 代理 head の BOOTSTRAP（交代時の読む順）

1. `HEAD_OWNER_LOG.md` 全文（STANDING で恒久制約、B で直近の流れ）
2. `claude agents --json` で実態照合
3. `git log --oneline -15 <共有ブランチ>` で直近差分
4. B の `owner_pending: yes` を最優先で対応

### 3.5 ID・参照キー方式（MF-2 / MF-3）— 「信用ではなく照合」

**正本語彙（field 名はこの6つに固定。`context_log_digest_id`/`head_owner_log_commit`/`standing_ids_*` 等の旧称は使わない）:**

ORCH 発注書（head→worker）に必須化:

```yaml
required_log_commit: <sha>              # 発注時点の HEAD_OWNER_LOG 版（worker はこれ以上に新しい版を読むこと）
required_digest_id: HOL-YYYYMMDD-NNN
required_standing_ids: [HOS-001, HOS-002]   # active な global_required は全件含むこと（欠落は ORCH 側 REJECT）
```

worker RESULT に必須化:

```yaml
read_log_commit: <sha>                  # worker が実際に読んだ版
read_digest_id: HOL-YYYYMMDD-NNN
read_standing_ids: [HOS-001, HOS-002]
```

→ 「読みました」を信じず、**ID と commit の一致で照合**する。

### 3.6 検収ゲート（常駐なしの fail-safe・named reject code）

head（または GPT 監査）は **ORCH 検収時**に次を**機械判定**し、該当すれば named code で**差戻し（REJECT）**:

| 条件（機械判定） | reject code |
|---|---|
| `read_digest_id != required_digest_id` | `REJECT_STALE_DIGEST` |
| `read_digest_id` が null / 未記載 | `REJECT_MISSING_DIGEST` |
| accept 条件 `git merge-base --is-ancestor <required_log_commit> <read_log_commit>` が **false**（＝worker が発注時版より古い／分岐した版を読んだ）| `REJECT_STALE_LOG_COMMIT` |
| `required_standing_ids ⊄ read_standing_ids` | `REJECT_STANDING_UNREAD` |
| ORCH の `required_standing_ids` が active な `global_required` を網羅していない（head の入れ忘れ）| `REJECT_REQUIRED_STANDING_OMITTED` |
| `active_standing_count > 20` | `REJECT_STANDING_OVERFLOW` |
| ORCH/packet に owner/head 会話履歴の長文 inline 検出 | `REJECT_INLINE_HISTORY` |

**祖先関係の向き（v0.2 の致命バグ修正点）**: ACCEPT は
**「発注時 `required_log_commit` が worker の `read_log_commit` の祖先（＝worker は同等以上に新しい版を読んだ）」**。
すなわち `git merge-base --is-ancestor <required_log_commit> <read_log_commit>` が true。
これが false（worker が古い／分岐版を読んだ）なら `REJECT_STALE_LOG_COMMIT`。
※ v0.2 は逆向き（古読みを通し新読みを弾く）だったため修正した。

**「読みました」は証拠でない。`digest_id` と `commit` が証拠。** これで常駐デーモン無しに、
更新漏れ・読了漏れ・古いログ参照を検収の一点で捕捉する。

### 3.7 更新漏れ時の復旧手順（MF-5）

```
digest 欠落を疑ったら:
1. git log --since=<last_digest_date>
2. ORCH-CURRENT と worker RESULT の log 参照を scan
3. owner_pending 言及を scan
4. BACKFILL digest を confidence=restored で作成
5. 元の欠落を gap_detected と印
```

---

## 4. クロスブランチ伝播（MF-1: P4 pointer-with-hash を採用）

全スレ共通だが作業は各 feature ブランチで進む。採用方式:

> **実装訂正（2026-06-30）**: canonical は実態に合わせ **head インフラ正本ブランチ
> `origin/claude/magazine-object-analysis-seg9cr`** とする（main には CLAUDE.md 等の head infra が無く 3日 stale のため）。
> 将来 infra が main へ集約された時点で canonical を main へ移す。設計ロジック（祖先照合・field・enforcement）は不変。

```
canonical_log : origin/<head-infra-branch>:docs/alo/HEAD_OWNER_LOG.md   # 現状 = claude/magazine-object-analysis-seg9cr。本体1点固定（P1）
worker_read   : git show origin/<head-infra-branch>:docs/alo/HEAD_OWNER_LOG.md
ORCH-CURRENT  : log_ref / required_log_commit / required_digest_id を持つ（P2導線＋P4 hash）
worker RESULT : read_log_commit / read_digest_id を持つ（鮮度検証）
branch_copy   : 禁止（P3不採用＝二重正本・古いSTANDING・解釈差を生む）
```

- **P1（本体 1ブランチ1点）＋ P4（ORCH 側は pointer＋expected commit/digest だけ）** の混合。
- P4 により「worker が古いログを見た」ことを**検収時に発見**できる。新デーモン不要。

---

## 5. 代替案と却下理由

- **A1: 生 transcript 全置き** — ノイズで読まれない。蒸留に劣る。却下。
- **A2: HEAD-NOTE_*.md を増やし続ける（現状）** — スレ依存・散在・横断不能。却下。
- **A3: 重い handoff フレームワーク（状態DB＋常駐）** — owner 決定「常駐はコスト過大」に反する。却下。
- **A4: ORCH-CURRENT.txt と統合** — CURRENT が「読み物」化し worker 運用が崩れる。**分離が正**（GPT Q4 も支持）。
  ただし CURRENT → LOG への `log_ref / required_log_commit / required_digest_id` 参照は持つ（§4）。

---

## 6. 影響範囲・コスト

- 新規ファイル1本（`HEAD_OWNER_LOG.md`）＋ `CLAUDE.md` 1行＋ `wake_worker.sh` プロンプト1行
  ＋ ORCH/worker RESULT スキーマに参照フィールド数行（§3.5）。
- 新デーモン・新ポーリング・新依存 = **なし**。
- 運用コスト = head が3トリガで5行追記＋検収で digest 照合（既存検収に1チェック追加）。owner 追加作業 = ゼロ（ratify 要 STANDING の yes/no のみ）。

---

## 7. backfill（最小スコープ・Q6）

```
BACKFILL-ORCH-CONTINUITY-MIN-001
対象: 直近7日 または 主要10決定のみ
出力: HEAD_OWNER_LOG.md 初期 STANDING ＋ SESSION DIGESTS 最大10件
禁止: transcript 全量保存 / 全セッション復元 / 常駐機構 / DB投入
目的: 歴史資料化ではなく今後の誤作動防止。"今も効く恒久制約・未決・HOLD・owner決定" だけ拾う。
```

---

## 8. 求める判定（decision_requested・再監査）

v0.1 の `DESIGN_MODIFY_REQUIRED`（MF-1〜5 / SF-1〜4）を反映済み。差分が MF に閉じているか確認し、
**DESIGN_PASS / PASS_WITH_NOTES 可否**を判定してほしい。特に:

1. MF-1〜5 が設計レベルで一意に閉じたか。
2. ID 照合方式（§3.5/§3.6）が既存 HANDOFF の thin/fat packet と矛盾せず接続するか。
3. 残る over-engineering（ID 付番が運用を重くしないか）がないか。

## 9. v0.1→v0.2 反映表

| 指摘 | 反映箇所 |
|---|---|
| MF-1 P4 pointer-with-hash | §4（採用）|
| MF-2 digest_id/standing_id＋ORCH/RESULT 参照必須 | §3.1 / §3.5 |
| MF-3 既存HANDOFF接続を参照キーに | §0.5（reference-key 規則）|
| MF-4 STANDING 肥大化制限（≤20/≤3行/active-retired）| §3.1-A |
| MF-5 更新漏れ復旧手順 | §3.7 |
| 検収ゲート | §3.6 |
| SF-1 90_design_decisions と区別 | §2 |
| SF-2 owner_ratified | §3.1-A |
| SF-3 archive_index 本体残置 | §3.1-C |
| SF-4 packet への長文 inline 禁止 | §0.5 |
| Q6 backfill 最小 | §7 |
| 検収ゲートを named reject code 化（owner stress test 反映）| §3.6 / §10 |
| **v0.3-①** `REJECT_STALE_LOG_COMMIT` 祖先方向の致命バグ修正（accept=発注commitがworker読了commitの祖先）| §3.6 / §10-B |
| **v0.3-②** field 名を正本語彙6つに統一（required_log_commit/required_digest_id/required_standing_ids/read_log_commit/read_digest_id/read_standing_ids）| §3.5 |
| **v0.3-③** standing に `enforcement`(global_required/task_scoped/informational)＋入れ忘れ検出 `REJECT_REQUIRED_STANDING_OMITTED` | §3.1 / §3.6 |

---

## 10. 受入ストレステスト（owner 指定 A〜E・PASS の必要条件）

| # | シナリオ | 期待動作（§3.6 ゲート）|
|---|---|---|
| A | head交代テスト: 新 head が過去会話を読まず `ORCH-CURRENT`／`HEAD_OWNER_LOG`／active STANDING／直近digest／`required_digest_id`／`log_commit` だけで復帰 | 復帰可能（§3.4 BOOTSTRAP）。不可なら航海日誌として失格 |
| B | 古いログ参照: worker が発注時版より古い／分岐版を読了（`git merge-base --is-ancestor <required_log_commit> <read_log_commit>` が false）| `REJECT_STALE_LOG_COMMIT` |
| B' | digest 不一致: `read_digest_id != required_digest_id` | `REJECT_STALE_DIGEST` |
| C | 読了偽装: `read_digest_id` が null（「読みました」だけ）| `REJECT_MISSING_DIGEST` |
| D | STANDING肥大化: `active_standing_count > 20` | `REJECT_STANDING_OVERFLOW` |
| E | HANDOFF重複: 既存 HANDOFF を長文 inline 再掲 | `REJECT_INLINE_HISTORY` |

## 11. 実装移行ゲート（owner G1〜G10・GPT再監査PASS後に判定）

| ゲート | 合格条件 |
|---|---|
| G1 ID完全性 | ORCH／worker RESULT／digest／standing が ID で相互参照できる |
| G2 hash鮮度 | `log_commit`＋`required_digest_id` が存在し worker 読了値と照合できる |
| G3 stale検出 | 古い digest 参照を `REJECT_STALE_DIGEST` で機械 REJECT |
| G4 missing検出 | digest未読・standing未読を `REJECT_MISSING_DIGEST`／`REJECT_STANDING_UNREAD` で REJECT |
| G5 肥大化防止 | active standing 最大20・各3行・retired化手順あり |
| G6 復旧手順 | digest欠落時に git log 等から再構成し `gap_detected` を残す（§3.7）|
| G7 既存HANDOFF接続 | 長文 inline 禁止・参照キーのみ（§0.5）|
| G8 正本分離 | `90_design_decisions.md` と航海日誌の責務が別（§2）|
| G9 backfill制限 | 初回 owner backfill が直近7日 or 主要10決定に限定（§7）|
| G10 実装HOLD | GPT再監査PASS前に accepted化・main commit・運用開始しない |
