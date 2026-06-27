# LEASE_SUBSYSTEM — design audit decision log

- date: 2026-06-25（v0.5 ratify: 2026-06-27）
- owner: asai
- status: **RATIFIED — v0.5 design 確定（GPT Pro `LEASE_PASS_WITH_NOTES` / owner-ratified 2026-06-27）。未実装**

## 結論（2026-06-27）

v0.5 は GPT Pro 再監査で **`LEASE_PASS_WITH_NOTES`**（result 2312201353719）。v0.4 残 B11/B17 は
CLOSED、§4 gate 列は実装一意と是認。オーナー裁定で **v0.5 design を ratify 確定**。PASS の射程は
「dispatch 可判定の設計」までで、付帯 notes は実装時必達（design doc §10）。実 mutation・運用解禁・
外部公開は別 gate まで HOLD。次工程は HANDOFF schema patch ratify packet → offline validator 実装 +
negative fixtures → Box stable ID 限定 synthetic prototype（GPT GO 範囲・実 mutate なし）。

## 経緯メモ（オーナー判断）

5 ラウンド目（v0.4 result 2306561290821）時点で「踊っているのでは」という問いが上がり、畳み方を
検討。一旦は「v0.5 で owner 確定し design gate を close」する案も挙がったが、オーナー裁定で
**design loop 継続（clean PASS を取りに行く）**を選択。結果、v0.5 で PASS_WITH_NOTES に到達し、
本記録を **ratification（v0.5 確定）** として確定した。

## 監査経緯（GPT Pro design audit）

| ver | REQUEST (Box to_gpt) | RESULT (Box from_gpt) | verdict | 主な指摘 |
|---|---|---|---|---|
| v0.1 | 2303989218514 | 2304096222240 | MODIFY_REQUIRED | ledger/target_key/holder/TTL/scope/二重active（6件） |
| v0.2 | 2306466253725 | 2306477639392 | LEASE_MODIFY_REQUIRED | B1-B8 |
| v0.3 | 2306503398024 | 2306525973159 | LEASE_MODIFY_REQUIRED | B9-B16 |
| v0.4 | 2306546819863 | 2306561290821 | LEASE_MODIFY_REQUIRED | 新規 8→2 に収束。B11/B17 + B18(次gate契約) |
| v0.5 | 2306847779852 / 2312082873257(repost) | **2312201353719** | **LEASE_PASS_WITH_NOTES** | B11/B17 CLOSED・§4 gate 実装一意是認・notes は実装時必達。※2309123924652=NEED_MORE は representation pending の取りこぼし（実体判断でない） |

## スコープの正直な明示（不変）

- design が確定・実装されても解禁されるのは「mutating dispatch **card を出してよい判定**」までで、
  **実ファイル移動・metadata 書込みは一切行われない**（feature flag 既定 off 継続）。
- 実 mutation は §8 の **独立した将来 gate**。

## 収束の所感

- 新規 blocking は 6→8→8→2→0 と推移し、v0.5 で PASS_WITH_NOTES に到達。
- LLM 監査者は「曖昧ゼロ・実装一意」を基準とするため clean PASS の fixed point を持ちにくいが、
  5 ラウンドで残 notes が「実装時具体化事項」のみに落ち、design gate としては確定可能と判断した。
