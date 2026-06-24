# P1: DD-DICT-008 accept 片付けパッケージ（candidate → accepted v1.0）

> doc_kind: accept readiness（design-only・owner 判断材料） / status: DRAFT / author: Claude / date: 2026-06-21 / owner: 浅井
> 親: design/vocab_object/01_VOCAB_BOTTLENECK_RESOLUTION_PLAN（P1）
> 対象: `DD-DICT-008 Canonical Bedrock 戦略 v0.2`（candidate）
> gate: 本パッケージは accept を**実行しない**。owner review ＋ URL 事実確認の段取りだけを固める。

## 0. 一行

DICT-008 を accepted v1.0 にするための**残ブロッカーは owner レビュー(A1/A2/A3)だけ**。
②Wave URL確認は 2026-06-25 に解消（4件とも新規bedrockを足さず accept非ブロッカー / 11_P1_WAVE_URL_VERIFICATION）。
owner が A1/A2/A3 を判断すれば accept 可。

## 1. 残ブロッカー（DICT-008 §6.1 より）

### A. owner レビュー（owner のみが判断）→ **これだけが残ブロッカー**
- [ ] **A1** DICT-008 v0.2 本体の内容 OK/NO/戻す（Q1–Q4 確定反映版が対象）
- [ ] **A2** `34_vocabulary_layer` §4.1（接続順=bedrock-first）/ §9（gate 2本追加）の改訂計画 review
- [ ] **A3** DDL 改訂（gate 2本＋§2.3.1 の gate 条件改訂）の影響範囲 review
- [x] A4 PLAN-01 v1.1 §3.4.5 整合（取込済）
- [x] Q1–Q4 確定済（2026-06-01）

### B. Wave 計画 URL 実在性確認 → **✅ 解消（2026-06-25 / 11_P1_WAVE_URL_VERIFICATION）**
read-only web で4件確認済。**いずれも新規 bedrock を追加しない**ため accept をブロックしない：

| Wave | 対象 | 結果 | 含意 |
|---|---|---|---|
| W1b | 参議院法制局「法令用語の例」 | ✅ web コラム連載(HTML) | 構造化辞書でない。enrichment 候補(非bedrock) |
| W1c | 内閣法制局「法令用例集」 | △ 単独web版なし | **既存 rank101(有斐閣)と同一編者で重複** → Wave除外 |
| W3a | 法務省 用語集 | ✅ web 軽量用語集 | 低権威=rank≥103 領域(非bedrock) |
| W3b | 金融庁/経産省/消費者庁 | ✅ 散在(web) | rank≥103 専門 attach(DICT-008方針どおり) |

→ **bedrock は現有3辞書(e-Gov rank100 + 有斐閣 rank101 + 学陽 rank102)で完結**。Wave 取得は accept 後の enrichment に降格。

> W2系列（JLT）は v0.2.1 amendment で確認済（rank106 辞書 v19.0・rank100d Law XML）。W1a（e-Gov）/W2c（最高裁OPAC）/W5（CiNii）は既存資産。

## 2. §2.3.1 で要る DDL gate 条件の改訂（A3 の核心・accept後作業だが論点を先出し）

`gate_canonical_promotion` は現状 `authority_rank > 102` を violation にしているが、§10 で canonical 昇格可が
**100 / 100a–100d / 101 / 102 / 200（自身の bibliographic hub のみ）**へ拡張された。よって gate 条件を：

```
-- canonical hub の anchor が「昇格可 rank 集合」以外なら violation
WHERE h.hub_status = 'canonical'
  AND NOT ( authority_rank IN ('100','100a','100b','100c','100d','101','102')
            OR (authority_rank = '200' AND <bibliographic hub である>) )
```

へ改訂する（実 DDL は P2／accept 後）。本 P1 では「この改訂が必要」を owner に明示するに留める。

## 3. accept したら何が起きるか（owner 向け一言）

- DICT-008 が accepted v1.0 → §6.2 の作業（doc_registry 登録・34層改訂・gate VIEW 追加・PLAN-01 反映）が解禁。
- これは **設計の確定**であって、辞書を DB に積むこと（P2）とは別。P2 は別途 owner GO ＋監査。
- accept は **DD-CRED-001（信憑性合成・別DD）に依存しない**（Q4 で scope 外確定済）。

## 4. owner への質問（P1 を閉じるために）

| # | 質問 | 既定 |
|---|---|---|
| Q-P1-1 | DICT-008 v0.2 を accept してよいか（A1） | owner 判断 |
| Q-P1-2 | Wave URL 確認（B）を hand agent に出すか / 後回しか | **hand agent（read-only web）** 推奨。accept の必須前提でなければ accept を先行も可 |
| Q-P1-3 | §2.3.1 gate 条件改訂を P2 の DDL に含める前提でよいか | **yes**（§10 と整合） |

## 5. ゲート

- 本パッケージは design-only。accept・DDL・DB・外部取得を実行しない。
- Wave URL 確認は read-only web（owner GO 後）。それ以外は owner レビュー待ち。
