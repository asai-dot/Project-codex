# ボトルネック解消計画: 辞書ゴールドを語彙ハブへ積む（dict→hub landing）v0.1

> doc_kind: 計画書（design-only・実行承認ではない） / status: DRAFT / author: Claude / date: 2026-06-21 / owner: 浅井
> 親: design/vocab_object/00_VOCAB_OBJECT_BOTTLENECK_BACKGROUND_20260621.md
> 一次: DD-VOCAB-000 / DD-DICT-008 v0.2(candidate) / 34_vocabulary_layer(FREEZE CANDIDATE) / DD-EL-001
> gate: 本計画の P0 は read-only。DDL/DB load/canonical/外部取得は後続フェーズの owner ゲート。

## 0. punchline（一行）

詰まりは「綺麗な辞書ゴールドを語彙ハブDBに積めていない」一点。**積む前の Hub 構築 dry-run（read-only）は今すぐ回せ**、
DB 着地・bedrock DD accept はその後の owner ゲート。silver と同じ「dry-run 先行・write は後」の型。

## 1. ゴールドと成功条件

| ゴール | 現在値 | 目標 |
|---|---|---|
| 語彙ハブDBへの着地 | **0（未デプロイ）** | 有斐閣13,344＋学陽2,662 が alo_terms/labels/relations に load |
| bedrock Hub | 0 | bedrock seed→exact→close で provisional hub 群が立つ |
| 重なり率閾値 | 0.6（暫定・Q2） | Wave0 実測で再校正した値 |
| 同綴異義の分離 | 64件 既知 | Term=sense で別 Term・surface-only merge 0（物理ゲート） |
| DD-DICT-008 | candidate | accepted（owner review＋Wave URL確認 後） |
| legal WSD(DD-EL-001) | 候補設計 | Wave0 eval corpus 選定・accepted EL の初期セット |

## 2. フェーズ計画（クリティカルパス）

```
P0 [即・read-only・ゲート無]  Hub構築 dry-run（DB書かない）
      bedrock seed→exact_match→close_match を staging JSONL で生成・重なり率/衝突を measure
        ▼
P1 [owner ゲート]  DD-DICT-008 accept への片付け
      owner review ＋ Wave計画 URL実在性確認(W1b/W1c/W3a/W3b) → candidate→accepted
        ▼
P2 [owner GO＋監査]  語彙ハブ schema デプロイ＋ゴールド load
      34_vocabulary_layer FREEZE 確定→DDL apply(物理ゲートをCI化)→bedrock 2辞書を canary→batch load
        ▼
P3 [後続]  Hub canonical 昇格(人手レビュー) ＋ legal WSD(DD-EL-001) Wave0 eval
```

## 3. 各フェーズ

### P0 — Hub 構築 dry-run（即着手・read-only・ゲート無）
- 入力 = 既存ゴールド staging（`yuhikaku_legal_dict_terms_stg_v3.jsonl` 13,344 / `hourei_all_entries_v0.2` 2,662 / `dict_overlay_v0.2_clean` 突合）。
- DICT-008 §2.4 の Stage1-3 を **DBに書かず JSONL で**回す:
  bedrock seed（rank100-102 の Term から hub 候補 1:1）→ exact_match（normalized_pref＋reading 一致）→ close_match（fuzzy）。
- 産物: `hub_candidate.jsonl` / `hub_membership_candidate.jsonl` / `report.md`
  （重なり率分布・同綴異義衝突・bedrock coverage・anchor 中立規則の適用結果）。
- **owner GO 不要**（既存 JSONL の突合・集計のみ・本番 write なし）。閾値0.6 はここで実測再校正の材料を出す。

### P1 — DD-DICT-008 accept への片付け（owner ゲート）
- 残ブロッカー2つを潰す: ①owner による DICT-008 v0.2 の review、②Wave計画の URL 実在性確認（W1b 参議院/W1c 内閣法制局/W3a 法務省/W3b 金融庁等）。
- ②は read-only の web 事実確認（owner GO で hand agent か手動）。→ candidate→accepted v1.0。

### P2 — schema デプロイ＋ゴールド load（owner GO＋監査ゲート）
- `34_vocabulary_layer`（FREEZE CANDIDATE）を確定 → **DDL apply**。物理ゲート（`gate_canonical_promotion` / `gate_specialty_exact_match`）を CI 化。
- bedrock 2辞書（有斐閣＋学陽）を **canary→batch** で alo_terms/labels/relations に load。
- HOLD 解除はこのフェーズで初めて。canary→検証→batch、各段に owner GO。

### P3 — canonical 昇格＋WSD（後続）
- bedrock hub を人手レビューで canonical 昇格（高頻度クエリ語から段階的）。
- `DD-EL-001` legal WSD の Wave0 eval corpus 選定（DD-VOCAB-000 O5）、accepted EL の初期セット作成。

## 4. owner 決定ポイント（推奨つき）

| # | 決定 | 選択肢 | 推奨 |
|---|---|---|---|
| D1 | P0 Hub dry-run を今すぐ回すか | yes / no | **yes**（read-only・ゲート無・パス先頭） |
| D2 | 重なり率閾値 | 0.6暫定のまま dry-run → 実測再校正 / 先に決め打ち | **0.6で dry-run→Wave0実測で再校正**（Q2確定どおり） |
| D3 | schema deploy の対象順 | bedrock 2辞書先行 / KOS含め一括 | **bedrock 2辞書を canary 先行**（KOS=D1TAXOは別スレ・別ゲート） |
| D4 | WSD eval corpus | P3で選定 / 今決める | **P3で選定**（hub が立ってから） |

## 5. 依存関係

```
即着手可(ゲート無)      : P0 Hub dry-run
owner 判断/作業で進む    : P1 DICT-008 accept(review＋URL確認)
owner GO＋監査に依存     : P2 schema deploy＋load
hub 成立後             : P3 canonical 昇格／WSD eval
```
クリティカルパス = **P0 → P1 → P2 → hub live → P3**。

## 6. リスク

| リスク | 対処 |
|---|---|
| 同綴異義が surface 一致で誤統合 | Term=sense＋`gate_specialty_exact_match`／exact は normalized_pref＋reading＋重なり率≥閾値のみ |
| 業界定義が canonical に昇格 | bedrock-first＋rank103 attach-only＋`gate_canonical_promotion`（rank≤102のみ canonical） |
| OCR末尾切れ5.1% 残ノイズ | `needs_reocr`(DD-DICT-006) で別処理。load 時は flag 保持 |
| schema FREEZE 未確定で DDL 手戻り | P2 前に 34_vocabulary_layer の FREEZE を owner 確定 |

## 7. ゲート（射程）

- 本計画は design-only。採用＝方向と順序の採用であり実行承認ではない。
- 継続 HOLD: 語彙ハブ schema DDL / alo_terms・alo_hubs への load / canonical hub 昇格 / WSD 本番 / 外部取得。
- P0 のみゲート無（read-only 突合・dry-run candidate 出力）。
