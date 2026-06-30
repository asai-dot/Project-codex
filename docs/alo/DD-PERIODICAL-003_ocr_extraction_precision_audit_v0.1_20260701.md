# DD-PERIODICAL-003 v0.1 — OCR/抽出 精度監査規格（誤OCR を accepted edge にしない）

- decision_id: DD-PERIODICAL-003
- 起案: head (Claude Code) / 2026-07-01
- 種別: DESIGN（read-only 設計。OCR 実行・DB write・edge accepted 化は owner GO・本DD対象外）
- 親: `DD-PERIODICAL-002`（article fulltext layer / OCR=HIGH-HOLD・P3 被覆より精度・§6 監査ビュー）
- 兄弟先例: 本セッションの精度監査（CITATION 和暦整合 / AUTHOR is_ambiguous / SERIES junk guard / L5 v0.3 generic guard・tiering・item証跡）
- gate: DDPERIODICAL（owner ratify → production は別ゲート）

---

## 0. 一行要約

scan/自炊の OCR は誤読が**致命傷**（事件名1字化け→判例ID 誤接続＝`edge_falselink`）。号で実証済の衝突検査
（false_merge/split/key_collision）を **OCR→本文→L5辺** に一般化し、**OCR-conf 閾値・由来権威の実在検査・
named reject code・低conf=held** を規格化する。**誤OCR は accepted edge に絶対しない**ための head 監査標準。

---

## 1. 解く問題（誤OCR が致命傷である理由）

- L5 辺 = 「この評釈は判例ID X を論じる」。**抽出元が OCR テキストだと、1字の誤読が別判例/不存在IDへの誤接続**を生む。
- これは本セッションで露呈した過併合（同名異判決の誤接続）と同型の **load-bearing 欠陥**。被覆を焦ると確実に混入する。
- DD-PERIODICAL-002 の原則 **P3「被覆より精度・曖昧は held」** と **§6 edge_falselink** を、実行可能な検査規格に落とす。

## 2. 不変の核（5原則）

1. **OCR-conf を辺の一級属性にする**。conf 無しの抽出は accepted 候補にすら上げない。
2. **由来権威で実在検査**。辺の target（判例ID/法令ID）は authority（判例 identity_keys / 法令DB）に**実在必須**。
3. **誤OCR を許容マージで吸収しない**。fuzzy 一致は **flag（候補）止まり**、accepted は厳密一致＋裏取りのみ（AUTHOR/L5 と同方針）。
4. **低conf/曖昧は held**（破棄も accepted もしない・append-only で残す）。被覆より精度。
5. **named reject code で機械差戻し**（号ISSN衝突検査・L5 v0.3 検収ゲートの一般化）。

## 3. OCR-conf 規格（抽出スパン単位）

- 各抽出スパンに `ocr_conf`(0..1)・`source_span_hash`・`bbox/page`・`engine_version` を保持（DD-PERIODICAL-002 「OCR conf保持」具体化）。
- 閾値（初期・branch dry-run で較正）:
  - `ocr_conf < 0.70` → **低conf**（accepted 候補から除外・held へ）
  - `0.70 ≤ conf < 0.90` → **要裏取り**（下記 §4 corroboration が無ければ held）
  - `conf ≥ 0.90` → 通常候補（それでも §4 ゲート通過必須）

## 4. L5 辺 精度ゲート（named reject code）— 号→辺への一般化

辺 candidate を accepted に上げる前に head/監査が機械判定。該当で差戻し:

| 条件（機械判定） | reject code |
|---|---|
| 抽出元 `ocr_conf < 0.70` | `REJECT_LOW_OCR_CONF` |
| target 判例ID/法令ID が authority に**実在しない** | `REJECT_FALSELINK_TARGET_ABSENT` |
| 抽出した引用 `(court,date)` が target 判例の court/date と**不一致** | `REJECT_CITATION_MISMATCH` |
| 引用の和暦↔西暦が**不整合**（CITATION 監査と同検査）| `REJECT_DATE_INCONSISTENT` |
| court が既知語彙に無い（OCR 化け）| `REJECT_COURT_UNKNOWN` |
| 事件名が generic（判例DB頻度≥10）で他の裏取り signal 無し | `REJECT_GENERIC_NAME_UNCORROBORATED` |
| 同一 (court,date) に複数 target 候補があり一意化 signal 無し | `REJECT_AMBIGUOUS_MULTI_TARGET` |
| 抽出元 span が複数辺に矛盾接続（誤分割/誤統合）| `REJECT_SPAN_CONFLICT` |

**corroboration（裏取り）signal**: docket(事件番号)一致 / 正式事件名の distinctive 一致 / 既存 L5 確定マップ(T1/T2)整合 / 複数スパンの独立一致。
1つも無い fuzzy/generic/低conf は **held**。

## 5. 回帰監査ビュー（DD-001 号検査の記事/辺への一般化・常設）

authority 更新・取込のたびに回す（DD-PERIODICAL-002 §6 を閾値付きで具体化）:

| ビュー | 検出 | 既存類比 |
|---|---|---|
| `edge_falselink` | target ID 不存在 / 低conf / citation不一致 | 号 key_collision |
| `edge_false_merge` | 1スパンが複数判例へ（誤統合）| 号 false_merge |
| `edge_false_split` | 同一判例参照が別IDに散る（誤分割）| 号 false_split |
| `article_collision` | 同 article_id に異なる本文/標題 | 号 false_merge(記事版) |
| `article_orphan` | issue_id 未解決 / 不存在号への接合 | 号 orphan |
| `ocr_lowconf_held` | 低conf で held 中の抽出（被覆ギャップの可視化）| 新規(P3 可視化) |

各ビューは**件数0が合格ではない**——held はギャップとして**明示**し、silent に accepted へ流さない（号スイープの silent truncation 禁止と同思想）。

## 6. tiering（L5 v0.3 と整合・accepted は最上位のみ）

- **T1**: 厳密一致＋distinctive名＋conf≥0.90＋corroboration有 → accepted 候補（owner ratify でedge化）
- **T2**: conf≥0.90 だが corroboration 単一 → reviewed 候補（owner review）
- **T3**: generic名 or conf 0.70-0.90 → held（要 owner/人手）
- **REJECT**: §4 いずれか該当 → 不採用（append-only で理由保持）

## 7. 分担（DD-PERIODICAL-002 準拠）

- OCR 取込・本文抽出・conf 付与 = **Mac producer ＋ owner GO**（HIGH-HOLD）。
- 本規格（閾値・reject code・回帰ビュー）の設計と監査 = **head**（read-only）。
- accepted edge 化・canonical 昇格・DB投入・外部公開 = **owner GO（T2ゲート）**。

## 8. 求める判定（GPT 監査用・任意）

1. OCR-conf 閾値（0.70/0.90）と held 方針は P3（被覆より精度）に整合し、誤OCR を accepted に通さないか。
2. §4 reject code は edge_falselink の経路を網羅するか（抜けた誤接続パターンは）。
3. fuzzy を flag 止まりにし accepted を厳密一致＋corroboration に限定する設計は安全側に十分か。
4. 回帰ビューの「held を silent に流さない」可視化は owner の被覆判断材料として十分か。

## 9. HOLD

OCR 実行 / 本文 DB write / accepted edge 化 / canonical 昇格 / 外部公開 は全て owner GO。
本DDは **read-only 設計（閾値・ゲート・ビューの規格）まで**。production 化は §4 ゲートが branch dry-run で全 PASS になってから。
