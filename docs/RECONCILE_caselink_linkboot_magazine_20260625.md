# RECONCILE — CASELINK / LINKBOOT / magazine 3ブランチ重複地図と正本決定（owner判断用）

- 作成: 2026-06-25 / 番頭: Claude Code (remote, head)
- 動機: owner「先に3ブランチの重複を地図化し正本を決めてから1回だけ回す」。worker 起動前のゲート。
- 結論(先出し): **重複(殺すべき duplicate)は無い。3つは別レイヤで、未接続なだけ。** ただし**私の CASELINK と magazine の計画 L5 は同一機能**で、片方を実装本体・他方を呼出にすべき。

## 0. 名前衝突の整理(重要)
- `data-linking-progress` の **"CASELINK"(2026-06-06, CASELINK_PASS_WITH_NOTES)** = **案件/依頼者リンク**（旧姓・別姓・利益相反・担当推定・Box sf_record_id）。**判例とは無関係。私の CASELINK と別物**（名前衝突）。混同回避のため将来 `MATTERLINK` 等へ改称推奨。

## 1. 3ブランチ レイヤ地図
| ブランチ | DD | source → target | レイヤ | 状態 |
|---|---|---|---|---|
| `magazine-object-analysis` | DD-PERIODICAL-002 | 記事 → 号(issue_id/ISSN/ISBN) ＋ 記事種別分類(302k) | **書誌同定・上流**(article↔issue, 判例評釈subset抽出) | 稼働中(article-join L4 / classify pilot) |
| **`precedent-object-progress`(私)** | **DD-CASELINK-001 accepted v1.0** | **評釈/記事本文 → 判例(case)** | **L5 判例リンク・型付け engine**(evaluates/compares+stance, masthead=auto/本文=review) | accepted・実装+span検出+dry-run harness 完備 |
| `journal-article-legal-linking` | DD-LINKBOOT-001 candidate | 書名/目次(TOC) → 法令(statute) | **法令リンク + 精度昇格 engine**(multi-pass, FP guard, 主題prior) | candidate(PASS_WITH_NOTES), TOC statute medium のみ・case将来 |

→ **ターゲットが各々 issue / 判例 / 法令 で異なる。殺す重複は無い。**

## 2. 唯一の実機能重複: 私CASELINK == magazine 計画L5
- magazine の `ORCH-LOCAL-ARTICLE-TYPE` 後続に明記: 「判例評釈subset → **第2段=評釈対象判例の抽出(court/date/事件) = ORCH-LOCAL-HANREI-TARGET → L5(評釈→判例リンク)**」。
- これは **私の DD-CASELINK-001 と同一**(masthead 対象判例抽出 + 本文採掘 + 型付け)。**magazine L5 はまだ未実装**(発注書なし)。
- ＝ 二重実装の risk。**今ここで一本化すべき**。

## 3. 正本決定（提案・owner ratify 待ち）
**各レイヤで正本を分離し、接続する（どれも廃止しない）:**
1. **magazine = 上流の正本**: article↔issue 同定・記事種別分類(302k)・**判例評釈 subset**(`article_type_local_v0.1.csv`)。
2. **CASELINK(私) = L5 判例リンク engine の正本**: `case_link_extract/map/eval` + `case_citation_span` + 語彙(35_link_layer crosswalk) + 精度gold。**magazine 計画の HANREI-TARGET/L5 は新規実装せず、この engine を呼ぶ**。
3. **LINKBOOT = 法令リンク + 精度昇格 engine の正本**: book/TOC→statute。**CASELINK の本文由来 review 候補は、将来 LINKBOOT の multi-pass 昇格 engine を再利用**（並行 promoter を作らない）。

## 4. 「1回だけ回す」改訂プラン（重複を作らない単一実行）
- CASELINK の corpus dry-run の入力を、**別 D1-LIC 整形ではなく magazine の 判例評釈 subset** にする:
  `article_type_local_v0.1.csv`(type=判例評釈) → article_id/title/body_text を引き、masthead 対象判例は HANREI-TARGET 抽出（court/date/事件）で埋める → `case_link_corpus_dryrun.py`。
- これで **magazine(上流) → CASELINK(L5 engine)** が一本で繋がり、二重実装も二重コーパス整形も発生しない。

## ✅ RATIFY（浅井先生 2026-06-25）
§3 の3レイヤ別正本 ＋ 「**magazine L5(HANREI-TARGET) は新規実装せず CASELINK engine に委譲**」を ratify。
→ §4 の単一 dry-run（magazine 判例評釈 subset を入力に CASELINK engine を1回回す）へ。
旧 "CASELINK"(案件リンク, data-linking) の改称は別途。

## 5. owner に決めてほしいこと
- (a) §3 のレイヤ別正本＋接続を ratify するか。
- (b) magazine L5(HANREI-TARGET) を**新規実装せず CASELINK engine に委譲**することの合意（雑誌ヘッドとの調整）。
- (c) `data-linking` の旧 "CASELINK"(案件リンク) を改称し名前衝突を解消するか。
- → ratify 後、§4 の単一 dry-run を **1回だけ** worker に回す（magazine の 判例評釈 subset を入力に）。
