# DD-COORD-001 ADDENDUM — Claude 2レーンの分担切り分け (lane-split) v0.1 REQUEST

- 日付: 2026-06-16
- domain: GOV
- status: **REQUEST**（owner ratify + GPT Pro 監査待ち。governance = material decision なので self-accept しない）
- 親（accepted・本ADDENDUMは延長であり上書きしない）:
  - **DD-CLAUDEHEAD-001-core v1.0/v1.1**（head/hand/番頭 役割プロトコル, ALO 憲法）
  - **DD-COORD-001**（cross-agent coordination protocol）
- 起票理由: legallibjoin ブランチ `claude/legallib-integration-design-Jgrtf` 上で **Claude 2レーンが
  並行して head 的に振る舞い（DD起票・owner決定記録・モジュール実装を各自）**、A-2「head 単一原則」が
  実質崩れて semantic 重複が発生した。具体実害は §1。本ADDENDUMは新統治の発明ではなく、
  **既存 accepted 憲法の再適用＋seam 運用規則の追加**。

---

## 1. 観測された実害（git 実証, 2026-06-15〜16）

| # | 事象 | commit |
|---|---|---|
| D1 | edition 強化を **2レーンが別物として生産**（DD-EDIDENT-001 spec vs edition_identity_v2 impl） | a9d4bca(Mac) / b4423f2(Mac) ※同一machineだが別セッション |
| D2 | **owner決定(b) を2回記録**（二重 single-writer 違反） | a67b114(Web) / 435bc63(Mac) |
| D3 | edition_v2 の **モジュール=Mac / 配線=Web** が別レーンで進行（seam） | b4423f2(Mac module) / 19c3e46・d1d0ca0(Web wiring) |

- **file 衝突は 0**（直近40commit、hot file 無し）。失敗は **textual ではなく semantic**＝
  「同じ意味の成果物を2レーンが各自作る」。よって解は file lock でなく **意味territory＋単一writer**。
- 良い兆候: Web は Mac の `B_STATUS` を読んで残件（v2配線）を解消＝**STATUS 経由の片方向coord は既に機能**。
  欠けているのは「着手前の claim」と「material act の単一化」。

## 2. レーン同定（誰が何者か）

| レーン | git identity | 憲法上の役割 | 実績territory |
|---|---|---|---|
| **Mac-local CC** | `Yuta <yuta@YutanoMac-Studio.local>` | **head / 番頭（DD-CLAUDEHEAD v1.0 = Mac CC）** | Phase0/B, DD(TOCADOPT/EDIDENT), edition_identity*, _toc_text, resolver_*, assemble_books, *_STATUS |
| **Web/cloud CC** | `Claude Code <asai@asai-lo.com>` | **hand / capacity（planner含む, head/auditor 不可 = A-1/A-2）** | concordance_pipeline, page_basis, authority_resolver, decision_log, conflict_detector, review_report, data_health, thresholds, config/, tests/, DDSELFHEAL |
| GPT Pro | — | **目付け役（不動・A-1）** | material decision の独立監査 |

> ⚠ head/hand の最終割当は **owner の専権**（§5 で確認）。上表は accepted v1.0（head=Mac CC）に基づく
> たたき台。Web を hand に固定しても、planner（考える人）として設計提案は継続してよい（v1.1 P1-NOTE-1）。

## 3. territory 分担（自然分業の formal 化）

各レーンが既に触っている領域に沿って境界を引く（disruption 最小）:

- **A. 意味・同定レーン（head=Mac CC が owner）**: edition_identity*（版/manifestation 同定の意味）、
  `_toc_text`（normalize 規則）、phase0_inventory、resolver_*、assemble_books、識別子/URI/identity-key、
  全 DD の起票・supersede・採用、`*_STATUS` と **owner決定の記録**。
- **B. パイプライン・基盤レーン（hand=Web CC が実装担当）**: concordance_pipeline / concordance /
  page_basis / authority_resolver / decision_log / conflict_detector / review_report、
  data_health / thresholds / config、tests/、DDSELFHEAL。head が dispatch した実装を実行。
- **C. seam（明示ルールが要る境界）**:
  - **edition_identity の意味=A / その配線(flag・既定値)=B**。A が v2 の contract を定義、
    B は **既定off で配線**（19c3e46 の良パターンを規範化）。**既定 flip は head 署名を要する**（material）。
  - concordance_pipeline は **B 所有**だが、入力 assembler(assemble_books) は **A 所有** → 入力契約は A、
    実行は B。

## 4. seam 運用規則（D1–D3 の再発防止・これが本体）

1. **単一 writer（material act は head のみ）** ← D2 修正。
   owner決定の記録 / DD の accepted・supersede / Generated Index backfill / 本番投入 / 外部送信 /
   identity-URI 変更は **head（Mac CC）が唯一の writer**。hand は提案までで記録しない。
2. **claim-before-build** ← D1 修正。
   新規 DD・新規モジュールに着手する前に、共有 `LANES.md`（または branch の CLAIMS section）へ
   `intent: <artifact> / lane: <A|B> / 起票者` を1行 post。相手レーンは同テーマ着手前に必ず確認。
3. **cross-link & status を起票時に付ける** ← reactive を proactive へ。
   相手 territory に重なる成果物は `[[相手DD]]` link＋`SUBSUMED/SUPERSEDED/companion` を **起票時に**明記。
4. **branch は1本維持**（現行 clean-rebase が機能・file衝突0）。territory＋claim で semantic 衝突を防ぐ。
   per-lane branch には**しない**（統合 overhead 増・現状不要）。
5. **目付けは GPT Pro 不動**（A-1）。2台目 Anthropic を監査役・head 代行にしない。
   head 落ち時、hand は襲名せず fallback（浅井 chat → claude.ai → Box queue, v1.0/F5）。

## 5. owner 判断（1 入力）

- **OQ-1（要確認）**: head = **Mac-local CC** で確定でよいか（accepted v1.0 準拠）。
  Web/cloud CC = hand（planner 兼 executor、head/auditor 不可）。
  別案 = 役割を入替（Web=head）／タスク期間ごとに owner が指名。**たたき台 = Mac=head**。
- **OQ-2**: §3 の territory 境界（A=意味/同定, B=pipeline/基盤）でよいか。seam C の「既定flipはhead署名」を採るか。
- **OQ-3**: claim 機構は `LANES.md`（branch 内ファイル）でよいか、Box queue（DD-COORD-001 既存）に寄せるか。

## 6. 適用範囲 / 非適用

- 本ADDENDUM は **調整プロトコルの追補のみ**。コード移動・branch 分割・既存 DD の改廃はしない。
- governance = material のため **self-accept 不可**: owner ratify ＋（role/auditor に触るので）GPT Pro 監査を要する。
- ratify 後、§4 の規則を DD-COORD-001 本文へ畳む（または本ADDENDUMを accepted companion 化）。

---

> 狙い: 「2台目 Claude を増やすと速いが、増えるのは capacity であって判断の独立性でも head 権でもない」
> （A-1/A-2）を運用に落とすこと。territory＋単一writer＋claim の3点で、今回の semantic 重複（D1-D3）は
> いずれも未然に防げた。
