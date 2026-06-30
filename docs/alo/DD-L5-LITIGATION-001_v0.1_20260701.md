# DD-L5-LITIGATION-001 v0.1 — 通称→事件(litigation)→判決 の二層 1:N 構造

- decision_id: DD-L5-LITIGATION-001
- 起案: head (Claude Code) / 2026-07-01
- 種別: DESIGN（read-only。litigation entity の DB化・edge accepted・canonical は owner GO・本DD対象外）
- 親/兄弟: `DD-L5-DISAMBIGUATION`（PASS_WITH_NOTES・通称↔判例の照合）/ `DD-PERIODICAL-003`（edge_role・誤OCR gate）
- 契機: L5 review queue の機械精査で **同通称→複数判例ID の CONFLICT 253行/77通称** を検出（read-only 実データ）。

---

## 0. 一行要約

「通称→判例ID」は **1:1 でなく 1:N**。有名事件は通称が**訴訟(litigation)**を指し、その訴訟が**審級チェーン
（地裁→高裁→最高裁）や併合で複数判決**を持つ。さらに**通称は衝突する**（日産自動車事件＝別個3事件）。
→ `通称 → 事件(litigation) → 判決(judgment)` の二層に分け、審級昇順の単調性で 1:N チェーンと通称衝突を機械判別する。

## 1. 問題（flat マップの誤り）

- L5 v0.3 のフラット `通称→判例ID` は、有名事件で**同通称→複数判例ID**になり CONFLICT として人手に滑り落ちる。
- 原因は2つ別物:
  1. **正当 1:N（訴訟チェーン）**: 一つの訴訟が一審/控訴審/上告審で複数判決を持つ。通称は訴訟を指す。
  2. **通称衝突（N:1 名前）**: 別個の事件が同じ通称を共有（日産自動車事件・離婚訴訟・マンナ運輸事件）。
- flat モデルは両者を区別できず、L5 主鍵（評釈→どの判決か）を誤らせる。

## 2. 実データ根拠（read-only・本セッション機械分析）

CONFLICT 77通称を審級ランク×date 単調性で分類:

| 分類 | 件数 | 例 |
|---|---|---|
| **litigation_chain（審級昇順＝正当1:N）** | **44** | 福島原発事故賠償訴訟(前橋地2017→仙台高2020) / 名古屋自動車学校(地2012→地2020→最高2023) / 津田電気計器(大阪高2011→最高2012) |
| multi_instance（審級複数・日付不整合）| 19 | 日産自動車事件(最高1985・最高1987・横浜地2014＝別事件) |
| same_instance別日（別事件/通称衝突）| 14 | 離婚訴訟(最高1983・最高2004) / マンナ運輸(神戸地2004・京都地2012) |

→ **審級昇順×date単調 = 訴訟チェーン**（機械確定可）、**同審級別日/日付不整合 = 通称衝突**（subject/当事者で分離・held）。

## 3. 二層モデル

```
nickname(通称)  --N:N(衝突あり)-->  litigation(事件/訴訟)  --1:N-->  judgment(判例ID)
                                       │
評釈article --edge--> judgment(引用日時で一意) または litigation(訴訟全体を論じる評釈)
```

- **litigation(事件)**: 一つの紛争。属性 = canonical_nickname / 当事者署名(将来) / 主題 / instance_chain[judgment...]。
- **nickname→litigation**: 1通称が1訴訟（普通）／**衝突時は1通称→複数litigation**（subject で分離・held）。
- **litigation→judgment**: 1:N。審級チェーン（一審 date < 控訴審 date < 上告審 date）＋同日併合。
- **edge(評釈→)**: 評釈が**特定判決**を論じる（引用 date/court で一意化）か、**訴訟全体**を論じる（litigation 級 edge）かを分ける（PERIODICAL-003 edge_role と整合）。

## 4. read-only 導出規則（機械確定 vs held）

各 CONFLICT 通称の判例ID群を審級ランク(地1/高2/最3)×date_key で:
1. **審級が2つ以上 ＆ 審級昇順で date 単調** → `litigation_chain`（**機械確定 litigation_candidate**・T1）。
2. **審級複数だが date 不整合** → `multi_instance_ambiguous`（**通称衝突疑い**・held・要 subject 信号）。
3. **同審級・別日** → `same_instance_collision`（**別事件**・held・要分離）。
4. judgment メタ欠落 → unresolved。

非CONFLICT（1通称→1判例）は litigation メンバー1の自明 litigation。

## 5. edge 解決（評釈article→）への接続

- 評釈タイトル/本文の**引用 (court,date)** が litigation の特定 judgment と一致 → **judgment 級 edge**（最精密）。
- 引用が訴訟全体（「○○訴訟をめぐって」等、特定審級なし）→ **litigation 級 edge**。
- いずれも PERIODICAL-003 の edge_role（評釈対象 vs 引用）と OCR-conf gate を通す。

## 6. tiering（L5 v0.3 / PERIODICAL-003 と整合）

- **T1**: litigation_chain（審級昇順単調）＋ distinctive 通称 → litigation 機械確定候補。
- **T2**: 1通称1判例の自明 litigation（既存 map T1/T2）。
- **held**: multi_instance_ambiguous / same_instance_collision（通称衝突）→ subject/当事者 信号が要・人手。
- **REJECT**: generic 通称×複数（既存 negative fixtures）。

## 7. 求める判定（GPT 監査用・任意）

1. 二層 `通称→litigation→judgment` は L5 主鍵の正しいモデルか。flat の誤りを解くか。
2. 審級昇順×date単調で litigation_chain と通称衝突を分ける read-only 規則は妥当か（誤分類リスク）。
3. edge を judgment級/litigation級に分ける設計は PERIODICAL-003 edge_role と矛盾しないか。
4. litigation entity を canonical 化する前提として、当事者署名 不在（identity_keys のみ）で十分か、追加権威が要るか。

## 8. HOLD

litigation entity の DB化 / edge accepted / canonical 昇格 / serving は owner GO。
本DDは **read-only 設計（二層モデル・導出規則・tiering）まで**。当事者署名等の追加権威取込は別 owner GO。
