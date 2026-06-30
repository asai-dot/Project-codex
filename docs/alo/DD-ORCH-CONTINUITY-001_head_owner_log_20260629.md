# DD-ORCH-CONTINUITY-001 — Head↔Owner 決定ログ（航海日誌）と head 交代継続性

- 起案: head (Claude Code) / 2026-06-29
- 種別: DESIGN（設計のみ。実装・本番反映・accepted化は対象外）
- スコープ: プロジェクト横断（雑誌/判例/法令/語彙 等 全スレ共通の運用基盤）
- 親規約: `docs/alo/AGENT_ORG_AND_ROUTING.md` / `docs/periodical/HEAD-ORDER-PROTOCOL.md`
- prior art（既決・矛盾不可）: `ALO-HEAD-HAND-HANDOFF-20260619`
  = `HEAD_HAND_HANDOFF_DESIGN v0.5`（**RATIFIED design 2026-06-23**）＋ `handoff_operational_impl v0.1`（PASS_WITH_NOTES）

---

## 0. 一行要約

Head↔owner(浅井) の対話に宿る「**意図・経緯・恒久制約**」を、コミットや ORCH 発注書とは別に
**1本の append-only ログに蒸留**して外部化し、(a) head が data limit 等で落ちたとき**代理 head が文脈ごと継げる**、
(b) **ワーカーが発注の字面の裏にある "なぜ" を読める**、状態を作る。

---

## 0.5 既存系列との関係（prior art・線引き — 重複でなく補完）

`ALO-HEAD-HAND-HANDOFF-20260619`（v0.5 が 2026-06-23 RATIFIED）は、本 DD と**同じ根の公理**から出発する:

> **H1（既存設計）: シームは直列化境界。アーティファクトに書かれない文脈は渡らない。**

ただし既存はこの H1 を **head→hand の「1タスクの作業パケット」** にのみ適用する設計である:
thin index＋fat packet・governance/execution role 分離・3軸 fail-closed effect（mutation/egress/resource）・
packet-hash・per-attempt reconciliation。**owner は gate metadata（`owner_pending`/ratify）としてしか登場せず**、
owner との対話に宿る意図や、head セッション自体の交代継続（limit ヒット）は射程外。

本 DD は同じ H1 を、既存が touch しない**別レイヤ**へ拡張する:

| 軸 | 既存 `HEAD-HAND-HANDOFF`（RATIFIED） | 本 DD `ORCH-CONTINUITY` |
|---|---|---|
| 対象 | **1タスクの dispatch パケット**（head→hand）| **永続する意図・恒久決定**（head↔owner、全タスク横断）|
| 形式 | 機械可読・hash・gated・schema 正本 | 人間/AI 可読の散文ログ（hash 無し・gate 対象外）|
| 粒度 | per-task（投下のたび）| per-session 蒸留（恒久＋直近30）|
| 解く失敗 | 過少記述/過結合/肥大による「シーム出血」| head交代の意図断絶(F1)/ワーカーの意図不知(F2)|

**合流点（重要・H1 と整合）**: 既存設計は「intent を packet に inline すると**肥大**して H1 の失敗モードに陥る」と明示する。
だから per-task の「なぜ」は packet に詰めず、**HEAD_OWNER_LOG に永続化して packet からは参照だけする**のが正しい。
本 DD は既存の dispatch schema・role/effect 軸・gating には**一切触れない**（それらは accepted・本 DD のスコープ外）。

---

## 1. 解こうとしている問題（Why）

現状、プロジェクトの記憶は3か所にあるが、いずれも「意図」を保持しない:

1. **ORCH-*.md 発注書** — 「何を・受入基準」は書くが「なぜ・どういう経緯で方針が変わったか」は書かない。
2. **git コミット履歴** — 結果の監査証跡。意図は断片的で、横断検索しないと辿れない。
3. **走っている head(Mac CC)の会話コンテキスト** — 「なぜ」はここに最も濃く宿るが、
   **data limit ヒットや別マシン交代で消滅する**。約30セッション分の Head↔owner やりとりが揮発する。

結果として生じる2つの事故モード:

- **F1（継続性の断絶）**: Mac CC head が limit で停止 → 代理 head が来ても、進行中タスク・保留判断・
  これまでの方針転換が分からず、状況復元に時間がかかる／誤った再着手をする。
- **F2（ワーカーのローカル最適暴走）**: ワーカーは ORCH の字面しか見ないため、owner が会話で示した
  優先順位・禁止・好みを知らずに「局所的には妥当だが戦略的には誤り」の判断をする。

本 DD はこの2つを、**重い handoff 機構を作らず**、1本のログで同時に解く。

---

## 2. 確定済み前提（変更不可・監査の枠）

- 既存の `AGENT_ORG_AND_ROUTING.md`（組織・ルーティング）と `HEAD-ORDER-PROTOCOL.md`（発注のやり方）は
  「**やり方**」担当。本 DD は「**今どこにいるか・なぜそうなったか**」担当で、両者を置換しない。
- **`HEAD_HAND_HANDOFF_DESIGN v0.5`（RATIFIED 2026-06-23）と矛盾しない**。本 DD は dispatch packet schema・
  role/effect 3軸・gating を一切変更せず、それらが packet 外に出した「永続 intent」の置き場を定義する補完層（§0.5）。
- **常駐デーモンは増やさない**（2026-06-29 owner 決定: 常駐はコスト過大）。新たなポーリングや watcher を要求しない。
- 共有ブランチへの force push 禁止（CLAUDE.md）。
- canonical 昇格・DB投入・外部公開は owner GO 必須。本ログは**参照系の運用文書**でありゲート対象データではない。

---

## 3. 提案設計（What）

### 3.1 成果物: `docs/alo/HEAD_OWNER_LOG.md`（append-only・スレ非依存・単一の真実）

2層構成:

```
A. STANDING（恒久の決定・好み・禁止）   ← 少数・厳選・先頭固定
   - 例: force push禁止 / external_share=false不変 / canonical昇格は owner GO
   - 例: ローカルちゃんは必ずチャンク分割
   - 例: 常駐デーモンは回さない（コスト過大, 2026-06-29）
   ※ ここは「今も生きている縛り」だけ。失効したら明示的に取り消し線＋日付で落とす。

B. SESSION DIGESTS（新しい順・直近~30件）   ← 1セッション5行程度
   ## 2026-06-29 — storm再発防止 / head交代準備
   - 決定: storm対策は wake_worker の cap ゲートのみ採用、reapデーモンは塩漬け
   - 理由: 常駐はコスト過大
   - 影響: tools/wake_worker.sh / 全スレ共通
   - 起票ORCH: (なし)
   - 未決/owner判断待ち: (なし)
```

- **A は蒸留、B はローリング**。30件を超えた古い digest は `HEAD_OWNER_LOG_archive_<period>.md` へ退避し、本体は薄く保つ。
- **owner は書かない**。head が会話の副産物として追記する（後述 3.3）。

### 3.2 更新トリガ（運用クセはこれだけ）

head は次の**3つの瞬間にだけ** 5行追記して push する:

1. owner との議論が一区切りして**方針が決まった**直後
2. ハンドへ**発注を投げた / 検収して認定・差戻した**直後（B に1行、必要なら STANDING 更新）
3. **owner 判断待ち（pending decision）が発生した**直後（B の「未決」欄に明記）

→ limit ヒットで最悪失うのは「直近1アクション」のみ。それも `git log` ＋ `claude agents --json` で復元可能。

### 3.3 ワーカーへの導線

- `CLAUDE.md` に一文追加: 「**発注実行前に `docs/alo/HEAD_OWNER_LOG.md` の STANDING ＋直近数件を読み、
  発注の意図を把握してから着手する**」。
- さらに `wake_worker.sh` が生成するワーカー起動プロンプトの冒頭に同指示を1行差し込む（既存プロンプト改修のみ。新デーモン不要）。

### 3.4 代理 head の BOOTSTRAP（交代時の読む順）

代理 head（別 Claude）は交代時に以下だけ実施すれば数分で追いつく:

1. `HEAD_OWNER_LOG.md` 全文を読む（STANDING で恒久制約、B で直近の流れ）
2. `claude agents --json` で実態照合（B の in-flight が本当に生きているか）
3. `git log --oneline -15 <共有ブランチ>` で直近差分
4. B の「owner 判断待ち」を最優先で対応

---

## 4. クロスブランチ伝播（設計上の要注意点・要監査）

本ログは全スレ共通だが、作業は各 feature ブランチ（magazine / hanrei / horei / vocab …）で進む。
「全ワーカーが最新の同じ1本を見る」をどう保証するかが論点。候補:

- **案P1（推奨）**: canonical を `origin/main:docs/alo/HEAD_OWNER_LOG.md` 1点に固定。
  ワーカーは着手時に `git show origin/main:docs/alo/HEAD_OWNER_LOG.md` で読む（append-only・小サイズなので衝突最小）。
  head の追記も main へ直接 push（または .claude-orch 経由で集約）。
- **案P2**: `.claude-orch/`（全スレ共通の発注基盤）配下に置き、既存の同期経路に相乗り。
- **案P3**: 各ブランチに複製し watcher/wake 時に main から rebase 同期 → **二重正本リスクが高く非推奨**。

→ P1/P2 のどちらが運用衝突・可視性の点で優れるか、GPT 監査の論点とする。

---

## 5. 代替案と却下理由

- **A1: 生 transcript を全部置く** — ノイズで誰も読まない。蒸留(STANDING＋digest)に劣る。却下。
- **A2: HEAD-NOTE_*.md を増やし続ける（現状）** — スレ依存・散在・横断不能。単一の真実にならない。却下。
- **A3: 重い handoff フレームワーク（状態DB＋ダッシュボード常駐）** — owner 決定「常駐はコスト過大」に反する。却下。
- **A4: ORCH-CURRENT.txt を拡張して兼用** — CURRENT は「次に振る発注ポインタ」の責務。
  意図・経緯・恒久制約まで載せると責務過多。分離する。（ただし統合する余地はあり、5の論点）

---

## 6. 影響範囲・コスト

- 新規ファイル1本（`HEAD_OWNER_LOG.md`）＋ `CLAUDE.md` 1行＋ `wake_worker.sh` プロンプト1行。
- 新デーモン・新ポーリング・新依存 = **なし**。
- 運用コスト = head が3トリガで5行追記する習慣のみ。owner の追加作業 = ゼロ。

---

## 7. 求める判定（decision_requested）

GPT Pro お目付け役に、以下を**独立監査**で判定してほしい（迎合不要・load-bearing な欠陥を厳しく）:

1. **DESIGN_PASS 可否**: この1本ログ方式が F1/F2 を実際に解くか。穴はないか。
2. **クロスブランチ伝播（§4）**: P1/P2/P3 のどれを採るべきか。見落とした第4案はあるか。
3. **責務分離（§5 A4）**: HEAD_OWNER_LOG と ORCH-CURRENT.txt を分離すべきか統合すべきか。
4. **更新規律の現実性（§3.2）**: 「3トリガで head が追記」は実運用で守られるか。守られないなら何で担保するか。
5. **過去30セッションの backfill** を別タスクで起こす価値はあるか。やるなら最小スコープは何か。
6. **既存 `HEAD-HAND-HANDOFF` との線引き（§0.5）が clean か**: 重複・責務漏れ・矛盾はないか。
   「intent は packet に inline せず HEAD_OWNER_LOG で参照」という合流は H1 と整合しているか。

## 8. 特に厳しく監査してほしい点（前提を疑え）

- 「head が規律よく追記する」前提が崩れたら全体が崩れる。**人間（AI）の規律に依存しない fail-safe** はあるか。
- STANDING が肥大化・陳腐化して誰も読まなくなる失敗モードへの歯止めは十分か。
- ワーカーが「読む」導線（3.3）は本当に読まれるか。読まなくても害がない設計になっているか。
