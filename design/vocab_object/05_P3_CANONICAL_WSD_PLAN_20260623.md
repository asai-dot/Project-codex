# P3: canonical 昇格 ＋ legal WSD（entity linking）計画 v0.1

> doc_kind: 計画書（design-only・実行承認ではない） / status: DRAFT / author: Claude / date: 2026-06-23 / owner: 浅井
> 親: design/vocab_object/01_VOCAB_BOTTLENECK_RESOLUTION_PLAN（P3）/ DD-VOCAB-000 / DD-DICT-008 / DD-EL-001
> 前提: P2 完了（bedrock 2辞書が alo_terms/alo_hubs に load・provisional hub 群が立っている）
> gate: 本計画は design-only。canonical 昇格・WSD 本番・embedding は HOLD（owner GO＋監査）。

## 0. 一行

provisional hub を **高頻度語から人手レビューで canonical 昇格**し、その canonical 語彙を土台に
**文中の語を正しい語義へ貼る legal WSD（DD-EL-001）**を write時に回す。語彙オブジェクトが「使える」状態になる最終段。

## 1. P3-A: provisional hub → canonical 昇格

### 方針（DICT-008 §2.4 Stage4 / §3.4）
- 全 hub は P2 時点で `provisional`。**canonical 昇格は人手レビュー後のみ**（自動昇格しない）。
- **高頻度クエリ語から段階的に**昇格（全件一括しない）。残りは provisional 運用、AI出力時に provisional マーク。
- 物理ゲート `gate_canonical_promotion`（rank≤102 の anchor のみ canonical 可）を CI で強制。

### 手順（read-only 準備 → owner レビュー → 昇格 write）
1. **昇格候補キュー（read-only）**: hub を (a) member 数、(b) クエリ/出現頻度、(c) bedrock 複数源一致 で序列化し
   `hub_promotion_queue.jsonl` を出力。member の定義並立・anchor 中立規則の適用結果を添える。
2. **owner レビュー**: 上位 N 件（例 200）を目視 → 昇格可否。
   - 定義が 101/102 で食い違う hub は**両定義を並立保持**（捨てない・優劣つけない／Q1）。
3. **昇格 write**: `hub_status=canonical` へ更新（append-only の review event 台帳）。`gate_canonical_promotion` 通過確認。
- review event は append-only。静かに既存判断を書き換えない（DD-VOCAB-000 §12.3）。

## 2. P3-B: legal WSD / entity linking（DD-EL-001）

### 原則（DD-VOCAB-000 §8 / DD-EL-001）
- **write時 disambiguation**（read時に毎回やらない）。mention → 正しい sense-Term へ解決。
- 解決シグナル: 文書の法令・領域コンテキスト / 近接法令参照 / 共起語 / TOC path / 定義文照合 / source type / prior。
- **confidence ＋ flag-first**: 閾値未満は確定せず review queue（誤リンクを沈黙保存しない）。
- accepted EL は WSD eval data / gold / linker 精度比較に再利用。

### 手順
1. **Wave0 eval corpus 選定（DD-VOCAB-000 O5・owner 判断）**:
   - 候補: 既取得の判例要旨 / 文献chunk / e-Gov条文 のうち、同綴異義が多い語（占有・善意・社員・担保・抗告）を含む小コーパス。
   - **read-only**: mention 抽出 → candidate sense（hub の member Term）→ シグナル付与 → confidence。
2. **dry-run linker**: `entity_link_candidates.jsonl`（mention / target_term_id / resolved_hub_id / confidence / review_status / evidence）。
   - `confidence>=threshold` → 確定候補、未満 → review queue。**本番 alo_entity_links には書かない**（dry-run）。
3. **eval**: 人手 gold と突合し precision/recall。閾値・シグナル重みを較正。
4. accepted EL を seed に linker_version を回す（owner GO 後）。

## 3. 依存と順序

```
P2 完了(hub in DB) ─┬─ P3-A 昇格候補キュー(read-only) → owner レビュー → canonical 昇格(write,段階)
                    └─ P3-B WSD: Wave0 corpus 選定 → dry-run linker(read-only) → eval → 較正
```
- P3-B の dry-run（mention→候補sense）は **provisional hub でも回せる**（read-only）。canonical 昇格を待たずに eval 着手可。
- ただし accepted EL の本番化・alo_entity_links write は owner GO＋監査。

## 4. owner 決定ポイント（推奨つき）

| # | 決定 | 推奨 |
|---|---|---|
| Q-P3-1 | canonical 昇格の初回バッチ範囲 | **高頻度 200 語**から（段階） |
| Q-P3-2 | WSD Wave0 corpus | **同綴異義が濃い小コーパス**（占有/善意/社員/担保/抗告 を含む判例要旨＋条文） |
| Q-P3-3 | confidence 閾値 | dry-run で分布を見てから決定（既定 0.7 仮） |

## 5. ゲート

- design-only。canonical 昇格 write / WSD 本番 / alo_entity_links write / embedding は HOLD（owner GO＋監査）。
- P3-A 昇格候補キュー・P3-B dry-run linker は read-only（候補出力のみ）で先行可。

## 6. これで語彙オブジェクト計画は P0→P3 まで揃う

P0(Hub dry-run・実データ完走) → P1(DICT-008 accept) → P2(schema deploy＋gold load) → P3(canonical昇格＋WSD)。
実行を解錠するのは「2辞書 dry-run の実測値」と「各 owner ゲート」。設計・ツールは ready。
