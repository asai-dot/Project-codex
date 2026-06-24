# ヘッド検収 — canary 1313 scratch/rollback packet（2026-06-17）

> 対象: Mac CC worker（Codex 5.5 controller 配下）提出
> `build/d1taxo_canary_1313_20260617/canary_1313_scratch_execution_packet.md`（29,602 bytes, 584行）
> lease: `PYDET-20260617-D1TAXO-CANARY1313-SCRATCHPACK-001`
> ヘッド: 番頭（Claude Head）／監査根拠: DD-D1TAXO-001 v0.6-R3 Pre-Apply（MF-1）

## 判定: ACCEPT_WITH_ONE_CHECK（scratch packet 設計は可・G23検証リンクの明示を条件に Mode B exec へ）

設計は妥当。次の1点を満たせば Mode B 実行 lease に進んでよい。full batch / production DDL / canonical / claim-support は HOLD 継続。

## 良い点（そのまま採用）

- **Mode B2（scratch schema 隔離）**: production schema を物理隔離し search_path 切替で原 RUNBOOK SQL を最小改変再利用。妥当。
- 全 Phase 単一 `BEGIN..ROLLBACK` ＋ Phase 境界を `SAVEPOINT` 化（partial rollback 防止）。
- prod 依存テーブルは scratch 内 minimal stub。fn_run_all_gates Phase9 は inline 推移閉包で代替。
- 永続操作 31 を列挙、`QA_fail=0 / protected_writes=0 / candidate_shell_INSERT=0`。HOLD ガード遵守。

## 要確認（1点・ブロッカー）— G23 skip の正当性リンク

packet は「**G23 は production の case_annotations 依存のため scratch では skip（Mode A QA で PASS 確認済を引用）**」とする。
**MF-1（G23 array guard）は本 canary の存在理由**なので、skip を narrative で済ませてはいけない（DD-D1TAXO-RDB-006: artifact受理・narrative不可）。

判断:
- G23 が **case_annotations 専用**で D1TAXO の load データ（alo_terms/edges 等）を**触らない**なら、D1TAXO scratch canary で G23 を回さないのは**論理的に妥当**。MF-1 検証は別途 Mode A で行うのが正しい切り分け。
- **ただし条件**: 「Mode A QA で PASS」を**具体 artifact で引用**すること。すなわち MF-1 patched G23 を **adversarial 非配列入力**
  （`MF1_G23_negative_smoke.sql` の missing/null/string/object/number/boolean 6形状）で回し、**エラー0・violation誤検出0**を示した
  evidence ファイル（path＋hash or 件数表）を canary evidence に添付/参照する。
- これが無いと「MF-1 を直したが canary も Mode A も実証 artifact が無い」状態になり、pre-apply ゲートを通せない。

→ **G23 skip 自体はOK。ただし MF-1 検証 artifact（Mode A 負例smoke結果）の明示リンクを必須にする。**

## open_questions（8件）への head 裁定

| # | 論点 | 裁定 |
|---|---|---|
| 1 | target DB 隔離度 | **独立 dev/staging or 独立 scratch DB**。production 隣接でも**物理隔離必須**、production 本体は不可 |
| 2 | search_path 衝突 | scratch schema＋明示 search_path。public/prod へのフォールバック禁止 |
| 3 | gate VIEW skip(G23) | 上記「要確認」のとおり：skip可・ただし MF-1 検証 artifact をリンク必須 |
| 4 | \copy JSONL 取込法 | scratch のみ可。v0.6/v3 JSONL を `FORMAT json`（1行1オブジェクト）で |
| 5 | 推移閉包 depth | 戸籍法は max_depth=6（413ノード）なので十分浅い。depth cap を設け無限ループ防止 |
| 6 | TS 命名 | controller 裁量で可（evidence は `scratch_run_<TS>/` に集約） |
| 7 | \o の build/ 配下書込 | **許可**（artifact 出力・scratch 限定） |
| 8 | production-schema 側 gate 評価 lease | **別 lease・owner gated・HOLD**。本 canary に含めない |

## 次アクション

1. controller(Codex): packet を上記 G23 検証リンク条件付きで accept。
2. **Mode B execution lease 発行**（target=独立 scratch DB / role 明示 / evidence 出力先 TS）。
3. canary 実行 → evidence（構造カウンタ: pref362/alt362/hidden362・term_tier2・external_kos・claim_support_eligible=false・
   pending L3 edge数・broader cycle=0、＋ **MF-1 G23 検証 artifact リンク**）返却。
4. head が evidence を MF-1 仕様＋監査ノートに照合 → PR #22/SoT 記録 → GPTお目付けの batch 判断へ。
   2本目 canary（richな root）は canary1 evidence 確認後に head 指示。
5. 並行候補（worker提案）: DD-D1TAXO-002 v0.2 audit packet / v0.6 R2 GPT audit result の Box sweep は、canary を塞がない範囲で可。

HOLD 継続: full batch / production DDL apply / canonical promotion / claim-support / embedding / MCP。
