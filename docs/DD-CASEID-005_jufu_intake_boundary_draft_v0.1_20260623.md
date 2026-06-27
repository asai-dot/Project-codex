# DD-CASEID-005 — jufu 取込境界（受任案件 手元判決の identity 利用と出口遮断）**draft v0.1**

- 起票: 2026-06-23 JST ／ 番頭: Claude Code (remote)
- lifecycle: **draft / candidate**（GPT Pro 独立監査 未了 → DDCASEID ゲート）
- domain: CASEID（判例ID確定 / 受任手元判決の取込境界）。**DD-CASEID-001 §5 follow-up「CASEID-005（jufu取込境界）」の本体**
- parent: `DD-CASEID-001`(accepted v1.0, N-1/jufu) / `DD-CASE-001`(accepted v1.0, AC-3 出口/3軸)
- related: `DDCASESOURCE`(出口一次所有) / `DD-CASEBIND-001`(G2) / `DD-CASECITE-001`(V7/V8) / `DD-DYNDB-CASES-001`(受任案件master=別オブジェクト)
- 実装: `scripts/jufu_intake.py` / `scripts/test_jufu_intake.py`

> **目的**: 受任案件で事務所が保有する**手元判決（jufu・非公開）**を判例同一性レイヤへ取り込む境界を確定する。原則は **「identity evidence には使えるが出口（global）には出さない」**（DD-CASE-001 AC-3 / DD-CASEID-001 AN-3 / RP-02・04）。これで CASEID ファミリーの設計を完結。**設計のみ・read-only**。

---

## 0. スコープと位置づけ
jufu は forum registry 上 `jufu`（court 型）だが、**出口は source registry で `lawyer_client_confidential / can_global_index=false`**（CASEID-003 AC-3）。本DDは「jufu observation をどこまで使ってよいか」の**用途境界**を実装粒度で確定する。判例の**識別**（A1）に資する一方、**機密の漏出**（A3）を構造的に防ぐ。

## 1. 決定

### 1.1 jufu observation の取込分類（`classify_jufu_observation`）
- `role = identity_evidence_only`：jufu は **A1 同一性 evidence 専用**。
- `confidentiality_class = lawyer_client_confidential` / `redistribution = restricted` / `can_global_index = false`。
- `matter_link_required = true`：jufu observation は **`alo_matter_id`（受任案件）へ link 必須**。ただし **`case_key`（判例ノード）≠ `alo_matter_id`**（N-1、別オブジェクト・相互代入禁止）。
- `content_grade`：手元判決の本文は最大でも matter 内限定（識別属性のみを A1 へ）。

### 1.2 用途境界（`allow_jufu_use`・5点ガード）
| 用途 | global | matter（認可者） | 根拠 |
|---|---|---|---|
| `identity_evidence`（A1） | **許可** | 許可 | 出口ではない。case_key 確認・自然キー補強に使える |
| `embedding` | 拒否 | **拒否** | RP-04（jufu global embedding 禁止、matter 認可でも不可） |
| `global_content_index` | 拒否 | 拒否 | lawyer_client は global 不可 |
| `mcp_serve` / `display` | 拒否 | **認可者のみ許可** | 当該受任案件の関係者への matter 内閲覧 |
| `export` / `claim_support` | 拒否 | 拒否 | matter 外へ出す用途は matter 内でも不可 |

→ **global は出口5点すべて拒否。matter 内は認可者に閲覧系（display/mcp_serve）のみ**。CASECITE V8（matter 認可）と同一の認可モデル。

### 1.3 公表 vs jufu限定
- 同一判決が**公表源にも在る**場合：jufu は ③CORROB の **identity 補強**に使い、**serve は公表ノード**（jufu本文は出さない）。
- **jufu 限定（未公開手元判決）**の場合：ノードは matter 機密。**global へは一切出さない**。識別（case_key 採番）は可、出口は matter 内認可閲覧のみ。

## 2. reconcile（accepted 上位DDと双方向一致）
- **N-1**: `case_key`(判例) と `alo_matter_id`(受任案件) は別オブジェクト。jufu は両者を link するが代入・FK・混在しない。
- **N-3 / AC-3**: 出口可否は DDCASESOURCE 一次所有。本DDはその適用（identity と出口の分離）。
- **②CASEBIND G2**: jufu で自然キー不能（匿名化・未確定）なら provisional・自動bind禁止。
- **④CASECITE V7/V8**: jufu ノードを引用する bundle は global で V7（非open 遮断）・matter で V8（認可）に必ず掛かる。
- **RP-02/04**: matter_scoped 5点ガード・jufu global embedding 禁止を本境界で実装。

## 3. why / alternatives_rejected
- **why identity と出口を分離**: 手元判決は「この事件が存在し、forum/日付/番号はこれ」という**識別に極めて有用**だが、本文・要旨を global に出せば守秘違反。識別（A1）だけ使い、出口（A3）は閉じる。
- **rejected**: jufu を通常 source として global index（守秘違反＝却下）。jufu を `case_key` に直接 matter_id 代入（N-1 違反＝却下）。jufu embedding を matter 内で global vector に相乗り（RP-04＝却下）。jufu 本文を要旨 source に昇格（公表ノード優先＝却下）。

## 4. verification（現状）
- deterministic_self_verification = **fixture-level done**: `test_jufu_intake.py` green（exit 0）。identity 許可・global 出口5点全拒否・embedding は matter 認可でも拒否・matter 内は認可閲覧のみ・未認可/別matter 拒否・分類。
- runtime/corpus = **Mac CC**（実 jufu 取込・access policy 統合）。
- independent_meaning_audit = **未了**（DDCASEID ゲートへ）。owner_approval = 未了。

## 5. follow-up
- jufu 取込の matter_link 実装（`case_observation` × `alo_matter_id`、N-1 不変）。
- access policy 側 fail-closed（CASEID-003 AC-3・K6）と本境界の二重化。
- 公表ノードとの identity 突合（③CORROB）で「公表に在るか」を判定する手順。
- jufu content_grade の運用（本文 matter 内・識別属性のみ A1）。
