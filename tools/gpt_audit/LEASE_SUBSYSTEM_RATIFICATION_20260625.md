# LEASE_SUBSYSTEM — design audit decision log

- date: 2026-06-25
- owner: asai
- status: **design loop 継続中**（v0.5 を GPT Pro 再監査へ投函・clean PASS を取りに行く）

## 経緯メモ（オーナー判断）

5 ラウンド目（v0.4 result 2306561290821）時点で「踊っているのでは」という問いが上がり、畳み方を
検討。一旦は「v0.5 で owner 確定し design gate を close」する案も挙がったが、**オーナー裁定で
design loop 継続（clean PASS を取りに行く）**を選択。よって本記録は ratification ではなく
**decision log** とし、v0.5 は GPT へ投函する。

## 監査経緯（GPT Pro design audit）

| ver | REQUEST (Box to_gpt) | RESULT (Box from_gpt) | verdict | 主な指摘 |
|---|---|---|---|---|
| v0.1 | 2303989218514 | 2304096222240 | MODIFY_REQUIRED | ledger/target_key/holder/TTL/scope/二重active（6件） |
| v0.2 | 2306466253725 | 2306477639392 | LEASE_MODIFY_REQUIRED | B1-B8 |
| v0.3 | 2306503398024 | 2306525973159 | LEASE_MODIFY_REQUIRED | B9-B16 |
| v0.4 | 2306546819863 | 2306561290821 | LEASE_MODIFY_REQUIRED | 新規 8→2 に収束。B11/B17 + B18(次gate契約) |
| v0.5 | （投函予定） | — | （審査中） | B11/B17 閉塞・B10/B12/B13/B14/B16 詰め・B18 次gate契約 |

## スコープの正直な明示（不変）

- design が確定・実装されても解禁されるのは「mutating dispatch **card を出してよい判定**」までで、
  **実ファイル移動・metadata 書込みは一切行われない**（feature flag 既定 off 継続）。
- 実 mutation は §8 の **独立した将来 gate**。

## 収束の所感

- 新規 blocking は 6→8→8→2 と推移し、v0.4 で収束局面に入った。
- LLM 監査者は「曖昧ゼロ・実装一意」を基準とするため clean PASS の fixed point を持ちにくい。
  これを承知の上で、オーナー判断により PASS を取りに行く（取れない/限界効用が落ちたら再判断）。
