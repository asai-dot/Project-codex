# ボトルネック解消計画: claim_support 在庫をゼロから立ち上げる（silver-first）v0.1

> doc_kind: 計画書（design-only・実行承認ではない） / status: DRAFT（owner レビュー待ち）
> author: Claude / date: 2026-06-18 / owner: 浅井
> 親: 00_SILVER_RESOLUTION_BACKGROUND_20260618 / DD-LRINDEX-001 v0.3 / DD-DATAARCH-001 v0.2 / DD-D1TAXO-003 v0.3
> WO: WO-SILVER-CITEID-001 / WO-SILVER-TOCSECTION-001 / WO-D1HANREI-REFETCH-001（いずれも本リポジトリ同梱・草案）
> gate: 本計画の P0 は read-only。write・外部取得・canonical mint・DDL はすべて後続フェーズの owner ゲート。

---

## 0. 計画の punchline（一行）

**claim_support 在庫（実測ゼロ）を立ち上げるクリティカルパスは、既取得データだけで回る silver-1（掲載位置→判例ID）
＋ silver-2（TOC→論点section）であり、両方 read-only・owner GO 不要で即着手できる。**
外部取得（#16 / D1再取得）と機構DD（DD-D1TAXO-004）は **当面のボトルネックのクリティカルパス上に無い**＝
カバレッジ拡張トラックとして後追いする。

## 1. ゴールと成功条件

| ゴール | 現在値（measured） | 目標（本計画の達成判定） |
|---|---|---|
| claim_support 在庫 | **0** | **> 0**（strong/reviewed の judgment-level エッジが立つ） |
| 解説→判例の judgment-level 化 | tier A 22k のみ | silver-1 で **+約6k**（tier B 23,914 の解決） |
| silver-1 歩留まり | 概算 24%（5,849/23,914） | 誌名正規化＋号fallback で向上を測定（目標値は dry-run 後に確定） |
| 意味ある共起 | 同一書籍 weight-1 が 89,358（無意味） | 論点section 単位の共起へ置換（weight 分布が出る） |
| 論点 harvest | 賃貸借/解除 659件（人手ゼロ実証） | N claim_type へ一般化（pipeline 化） |

honest_empty 規律: 無評釈・痕跡なしは `trace_absent`、未構築は `db_unbuilt` として区別し、空を成果と偽らない。

## 2. フェーズ計画（クリティカルパス）

```
P0 [即・read-only・ゲート無]  silver-1 dry-run ∥ silver-2 dry-run
        │  （既取得データのみ。candidate を staging 出力。歩留まり/weight を measure）
        ▼
P1 [owner レビューゲート]    dry-run report レビュー → 閾値確定 → strong/reviewed の staging write
        │
        ▼
P2 [監査ゲート: DD-LRINDEX v0.4 GPT確認]  論点 harvest pipeline を silver-2 section 上で一般化
        │
        ▼
P3 [監査ゲート: DD-DATAARCH v0.2 GPT監査]  claim_support>0 を serve（graph-only as_of read-model）へ
─────────────────────────────────────────────
カバレッジ拡張トラック（クリティカルパス外・並行）
  X1 [owner GO・外部]  #16 D1文献編事項索引 取得WO → DD-D1TAXO-004（機構DD）
  X2 [owner GO・外部]  D1全件再取得WO（参照判例フィールド）→ 判例→判例 直接引用
```

### P0: silver dry-run（即着手・read-only・ゲート無）
- WO-SILVER-CITEID-001 と WO-SILVER-TOCSECTION-001 を **dry-run（candidate staging 出力のみ）**で並行実行。
- 入力は既取得のみ（lic edges 55,978 / hanrei_published_in 76,643 / toc_row_reports 7,039 / hyoshaku 61,153）。外部取得なし。
- 産物: `silver_cite_resolution_report.md` / `silver_toc_section_report.md`（歩留まり・weight 分布・未解決理由・trace_absent 割合）。
- **このフェーズは owner GO 不要**（既存 jsonl/索引の集計・突合のみ・本番 write なし）。

### P1: owner レビュー → staging write（owner ゲート）
- dry-run report を見て (a) 誌名正規化辞書の採否、(b) confidence 閾値、(c) strong-only か strong+reviewed か を決める。
- 確定後、strong/reviewed candidate を **staging（build側②silver）へ write**。canonical graph へは書かない。
- 推奨デフォルト: **strong-only（issue_page_exact 由来）から write**。fallback/court_date 由来は review queue 保持。

### P2: 論点 harvest 一般化（監査ゲート）
- 前提: **DD-LRINDEX-001 v0.4（G_HARVEST_NOT_MANUFACTURE）の GPT 確認パス確定**。
- silver-2 の論点section を母数に、賃貸借/解除 659件パターンを N claim_type へ一般化（論点グループ＝文献見出しクラスタ、
  重要度＝評釈密度＋引用中心性）。**人手 seed は使わない**。
- 確認パス未確定の間は、本フェーズの出力を accepted 論点として扱わない（P0/P1 は影響を受けず先行可）。

### P3: serve 接続（監査ゲート）
- 前提: **DD-DATAARCH-001 v0.2 の GPT 独立意味監査 → owner ratify**。
- claim_support>0 を graph-only / as_of read-model（DD-DATAARCH ⑤）で引用接地つきに serve。vector は HOLD 継続。

### X1 / X2: カバレッジ拡張（クリティカルパス外・owner GO 外部取得）
- X1 #16取得: DD-D1TAXO-003 の次手。取得後に DD-D1TAXO-004（match 付与規則・閾値・葉アラインメント・conflict 解決・confidence 較正）。
- X2 D1再取得: 「反例が引く反例」を入れる唯一経路。D1 セッション干渉回避策の合意が前提。
- **どちらも当面のボトルネック（claim_support 立ち上げ）には不要**。P0–P2 と独立に、owner の都合で発注。

## 3. 依存関係マップ

```
即着手可（ゲート無）         : P0 silver-1 dry-run, P0 silver-2 dry-run
owner 1判断で進む           : P1 staging write（閾値決定）
GPT監査結果に依存           : P2（DD-LRINDEX v0.4 確認）, P3（DD-DATAARCH v0.2 監査）
owner GO + 外部 + 干渉回避   : X1 #16取得, X2 D1再取得
```

クリティカルパス = **P0 → P1 → P2 → claim_support live**。X1/X2 は並行トラックで合流は後。

## 4. owner 決定ポイント（推奨つき）

| # | 決定事項 | 選択肢 | 推奨 |
|---|---|---|---|
| D1 | silver-1 着手単位 | (a) 1 claim_type canary（賃料不払解除 882 seed）→ batch / (b) 掲載位置正規化を横断先行 | **(a) canary→batch**（DD-LRINDEX §6 の確立パターン・小さく検証） |
| D2 | silver write 閾値 | (a) strong-only / (b) strong+reviewed | **(a) strong-only から**（reviewed は queue 保持で後追い） |
| D3 | 外部取得の順序 | (a) P1 まで両方保留 / (b) #16 先行 / (c) D1再取得 先行 | **(a) 保留**。強行するなら **(b) #16**（概念層機構トラックを解錠・D1セッション干渉なし） |
| D4 | P0 dry-run を今すぐ回すか | yes / no | **yes**（read-only・ゲート無・クリティカルパス先頭） |

## 5. リスクと対処

| リスク | 影響 | 対処 |
|---|---|---|
| harvest 設計が監査で覆る（v0.4 未確定） | P2 やり直し | **P0/P1 を read-only に保ち、論点を accepted として書かない**。監査確定まで harvest 出力は probe 扱い |
| carverage バイアス（無評釈判例が出ない） | 学説的空白が claim_support に現れない | `trace_absent` で honest_empty 明示区別。owner 発想（評価され尽くしたものを捕まえる）と整合 |
| 誌名正規化の歩留まりが伸びない | silver-1 の +6k が縮小 | dry-run で未解決理由を内訳化 → 正規化辞書を反復改善（号fallback の効き目を測る） |
| D1再取得のセッション干渉 | 既存 D1 作業と衝突 | X2 は owner GO ＋ 干渉回避合意 ＋ canary 検証計画を発火条件に固定（クリティカルパス外なので急がない） |

## 6. 即時の次アクション（P0）

owner が D4=yes なら、本リポジトリ上で **silver-1 / silver-2 の dry-run スクリプトを read-only で実装**し、
report 2本を artifacts へ出す。外部取得・本番 write は伴わない。D1（着手単位）と D2（閾値）は dry-run report を見てから確定で問題ない。

## 7. ゲート（本計画の射程）

- 本計画は design-only。採用は「方向と順序の採用」であって実行承認ではない。
- 継続 HOLD: DDL / DB write（staging 含む P1 以降）/ 外部取得（#16・D1）/ canonical mint / production mapping / MCP publication / vector 解禁。
- P0 のみゲート無（read-only 集計・dry-run candidate staging 出力）。
