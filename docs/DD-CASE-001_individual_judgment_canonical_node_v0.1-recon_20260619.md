# DD-CASE-001 — 個別判断の正準ノード母型（判決・審判・裁決・答申・ADRの統一同一性）**v0.1-recon draft**

- **recon_status: `reconstructed_from_residual_materials`**（原本同一性なし。must_fix#1）
- 起票（原本）: 2026-06-04〜05 JST（前セッション・ローカル限定で散逸） ／ **再構成日: 2026-06-19 JST**
- lifecycle: **draft / candidate**（GPT Pro 独立意味監査 **`DDCASESOURCE_PASS_WITH_NOTES`** 2026-06-19, Box 2295309962089／must_fix 6点を本版で反映済 → **owner ratify 待ち**）
- 原本 v0.4 の扱い: **`blocked_unrecoverable_reconstructed`**（superseded ではない。原本5点は回収不能、本 recon が後継。must_fix#2）
- domain: CASE（判例レイヤ エンティティ母型 / 準司法取水口）
- parent: `31_case_layer.md`(SPEC-02 v1.4, cases/case_annotations 分離) / 統合仕様書 v3.0 CaseBundle v1.5
- related: `DD-CASEID-001`(ID確定・**accepted v1.0**／本DDは case_type/node schema を供給) / `DDCASESOURCE`(準司法・機密一次所有) / `DD-DYNDB-CASES-001`(受任案件master＝別オブジェクト)
- reconcile 前提: `DD-CASE-001_DDCASEID_reconcile_20260618.md`（不変則 N-1〜N-4）

> ⚠ **本書は再構成版（v0.1-recon）**。原本 `DD-CASE-001_individual_judgment_canonical_node_draft_v0.1.md`（および sibling 4点：closure本体・`alo_source_registry_seed_v0.1`・`registry_negative_test.py`・`31_case_layer_quasi_judicial_patch_v0.2`）は前セッションのローカル作業のまま Box 未アップロードで散逸（2026-06-06 / 06-19 二重確認、`reconcile §4` 探索ログ参照）。本書は Box 残存材料（準司法REQUEST の RP-01〜06・§D5' 要旨、`31_case_layer.md`、`DD-CASE reality_check`、DD-CASEID-001 accepted正本／reconcile不変則）から**意味を復元**したもの。原本の逐語ではない。**監査・ratify はこの recon 版を対象**とする。

---

## 0. スコープ — なぜ「母型」が要るか

判例レイヤ(31_case_layer §1.1)は「**事件の同一性**(cases)」と「**ソース別解釈**(case_annotations)」を分離済みだが、PoC は判決(judicial)を主対象に設計された。事務所の差別化価値は **準司法判断**（行政審判・審査会裁決・答申・ADR・仲裁・調停）と在野・受任手元にある（DD-CASEID-001 §2 why）。これらは「判決」と同じ `cases` 行に素朴に同居させると、(a)同一性の根拠が機関ごとに異なる、(b)機密の出口可否が判断種別ごとに違う、(c)解釈の帰属が混ざる、の3点で破綻する。

本DDは **個別判断(individual judgment)を1つの正準ノード**として扱う母型を定義し、判決をその特殊形と位置づける。DD-CASEID-001 が「ID確定の上流機能」なら、**本DDは「ノードそのもののエンティティ母型」**（不変則 N-4）。case_type 正準enum と node schema は **本DDが定義**し、CASEID 側は参照・整合のみ（N-2）。

## 1. §D5' — 個別判断ノードの **3軸分離**（本DDの核）

1つの個別判断ノードが混同してはならない3軸を分離する。素朴な `cases` 行はこの3軸を1行に潰すため不可。

| 軸 | 名称 | 何を保持するか | 所有DD | 該当テーブル |
|---|---|---|---|---|
| **A1** | **同一性軸 (identity)** | 判断そのもの＝「どの機関が・いつ・何号事件で・誰の間に下したか」。源非依存。case_key(ULID不変) を anchor、forum_code+decision_date+case_number_norm を自然キー | **本DD**（node schema）＋ CASEID-001（採番・名寄せ） | `cases`(拡張) / `case_observation` |
| **A2** | **解釈軸 (interpretation)** | 要旨・タクソノミーパス・分類・評釈リンク。ソース帰属を保持したまま | 31_case_layer（既存）＋ DD-CASEANNOT-TEXT | `case_annotations` / `term_occurrence` |
| **A3** | **出口軸 (confidentiality / export)** | 誰に見せ・どこへ出せるか。判断種別と源で決まる | **DDCASESOURCE が一次所有**（本DDは参照のみ・N-3） | `confidentiality_class`（A1ノードの属性として参照） |

**分離不変則**：
- ノードの**存在・同一性(A1)は、解釈(A2)が空でも(annotation_maturity=preliminary)、出口(A3)が `lawyer_client_confidential` でも、成立する**。識別と公開可否は独立。
- `case_type`(後述)は **A1の属性**。出口可否は **A3の属性**。両者を同一カラムに混ぜない（例: 「受任だから非公開」をcase_typeで表さない）。
- A3 の判断（open/scoped/confidential）は本DDで**定義しない**。DDCASESOURCE の `confidentiality_class` を**参照する外部キー的関係**に留める（N-3）。

## 2. case_type 正準enum（本DDが唯一の定義元 — N-2）

31_case_layer v1.6 の `judicial/adr/conciliation/adjudication` を準司法へ一般化し、**本DDを正準定義元**とする。CASEID・他DDは新規追加せず参照のみ。

| case_type | 含む判断 | 同一性の自然キー源 | 既定 forum_type |
|---|---|---|---|
| `judicial` | 通常裁判の判決・決定・命令（既定） | 裁判所＋判決日＋事件番号 | court |
| `adjudication` | 家事審判・少年審判・行政審判 | 機関＋審判日＋事件番号 | tribunal |
| `administrative_review` | 行政不服審査の裁決・審査会の議決 | 審査庁/審査会＋裁決日＋事件番号 | administrative |
| `advisory` | 答申・諮問・意見（公取委・労委・各種審議会） | 機関＋答申日＋諮問番号 | advisory |
| `adr` | 仲裁判断・ADR和解（仲裁機関・弁護士会ADR） | ADR機関＋判断日＋事件番号 | adr |
| `conciliation` | 民事/家事調停成立・調停に代わる決定 | 裁判所/機関＋成立日＋事件番号 | court/tribunal |

> 注：`judicial` を既定とし、自然キーが取れない種別（answer番号のみ・匿名裁決等）は CASEID-001 の **provisional 採番**へ逃がす（A1とCASEIDの接合）。`case_type` は **annotation ではなく cases(A1) のカラム**（CaseBundle guard `case_type` が参照、31_case_layer §6.3）。

## 3. node schema — `cases` 拡張（A1）

DD-CASEID-001 §3 の `cases` 拡張と**同一フィールド集合**を共有し（重複定義を作らない）、本DDは **意味付け（どの列がどの軸か）と case_type enum** を所有する。

| カラム | 軸 | 由来 | 備考 |
|---|---|---|---|
| `case_key` ULID | A1 | CASEID-001 | 採番後不変 anchor。法的・文献的意味を持たせない純surrogate（AN-1） |
| `canonical_uri` | A1 | CASEID-001 | `identity_status=confirmed` 時のみ確定。不能時 provisional `alo:case:jp:_prov:{case_key}` |
| `forum_code` | A1 | CASEID-001(`alo_forum_registry`) | 旧 court_code の一般化。本DDの case_type と forum_type で整合 |
| `case_type` | **A1** | **本DD（§2）** | 正準enum。NOT NULL・既定 judicial |
| `decision_date` / `case_number_norm` | A1 | 31_case_layer | 自然キー。norm はかな/漢字保持（CASEID-001 §1.3） |
| `identity_status` | A1 | CASEID-001 | confirmed / provisional |
| `merged_into_case_key` | A1 | CASEID-001 | merge禁止原則の下、tombstone/superseded_by のみ（AN-2） |
| `confidentiality_class` | **A3参照** | **DDCASESOURCE** | open / matter_scoped_only / matter_confirmed / lawyer_client_confidential。本DDは値域を**借用**し定義しない（N-3） |
| (解釈一切) | A2 | `case_annotations` | headnote/taxonomy は本ノードに**置かない**（31_case_layer §1.1 厳守） |

## 4. RP-01〜06 の取り込み（準司法 closure からの確定事項）

散逸した closure 本体で閉じられていた6指摘を、出口軸(A3)の制約として母型に明記する（準司法REQUEST §1 より復元）：

- **RP-01 / RP-06**: `confidentiality_class` 値域＝`open` / `matter_scoped_only` / `matter_confirmed`（旧 confirmed_private）/ `lawyer_client_confidential`。
- **RP-02**: `matter_scoped_only` ノードは **出口5点 guard**（global content index / embedding / MCP serve / export / claim_support）で当該matter外へ漏らさない。
- **RP-03**: backfill フィルタは **`confidentiality_class == open` のみ**を public/global content index へ（`!= no_export` では緩すぎる。D1商用・在野も open 以外は除外）。
- **RP-04**: jufu（受任手元）由来 embedding の **global 投入禁止**（identity evidence 用途に限定、AN-3 と一致）。
- **RP-05**: negative test 9 assertion（散逸した `registry_negative_test.py` が担保）→ **再構成要**（§7）。

## 4.5 record-level 出口 override（must_fix#6 / 監査 F2・should_fix）

出口可否(A3)は **source_system 単位だけでは粗い**。同一 source 内でも record により異なる（例：公表要約 vs 本文 vs 添付PDF vs 匿名化前データ／公表裁決でも個人情報含有 record）。よって node/record に **出口 override** を持たせ、source/class 既定より **record override を優先**させる（実装は `registry_negative_test.py` の `record_override` で符号化、`B6` で検証済）。

- 設計列（G2 で DDL 化、本版は設計確定のみ）: `cases.export_override jsonb`（`{sink: bool}`、null=既定に従う）。
- 既定との関係: `effective_allow(sink) = override[sink] if sink in override else default_policy(confidentiality, redistribution, source, same_matter, sink)`。
- record-level note: 公表コーパスでも 個人情報・匿名化・robots/API・再利用条件を record メモに保持（should_fix#3）。

## 5. 不変則整合（reconcile N-1〜N-4 / DD-CASEID-001 AN-1〜AN-5）

- **N-1**: 本DDの `case_key`(判例ノード) と `alo_matter_id`(受任案件) は別オブジェクト。受任案件の手元判決は **A1ノードへ identity evidence として接続**できるが、ノード自体を matter に代入しない。
- **N-2**: `case_type` 定義は**本DDが唯一**。CASEID-001 は §1.5 N-2 で「参照・整合のみ」と明記済（双方向一致）。
- **N-3**: A3(出口)は DDCASESOURCE 一次所有。本DDは `confidentiality_class` を参照するだけ。
- **N-4**: 本DD=エンティティ母型、CASEID-001=ID確定上流機能。重ねない。
- **AN-2(merge禁止)**: 審級・原処分↔取消訴訟・答申↔抗告訴訟・ADR↔執行決定は **別case_key＋`alo_edges`**（`appeal_of`/`review_of`/`annuls`/`remands`/`origin_decision`/`relative_resolved`）。同一事件性があってもノードは分ける。
- **AN-5(HOLD)**: 本DDは**設計確定のみ**。DDL / canonical case mint / DB write / alo_edges / embedding / MCP serve / export / jufu出口利用は **G2 production-readiness gate で別審査**。

## 6. why / alternatives_rejected

- **why 母型**: 判決専用スキーマに準司法を後付けすると、case_type が出口可否や forum 種別と混線する。3軸(§1)を最初に分けておけば、種別追加(答申/裁決/ADR)は enum 追加で済み、出口は DDCASESOURCE 側で独立に締められる。
- **rejected**:
  - 判決と準司法を別テーブルに分割 → 名寄せ・edge・CaseBundle guard が二重化、35層 fingerprints が割れる。**却下**（単一 `cases`＋case_type で吸収）。
  - confidentiality を case_type に内包（例 `confidential_case`）→ A1とA3の混線。種別と機密の直交性を失う。**却下**。
  - 答申・諮問を annotation として表現 → 「判断そのもの」が A2 に落ち、同一性が立たない。**却下**（A1 ノードとして扱う）。

## 7. follow-up / 散逸 sibling の再構成計画

本書(DD-CASE-001 母型)は critical-path（reconcile §4・N-2/N-4 依存）を充足。残り3 sibling は本書確定後に従属再構成：

1. **closure 本体**(`DD-CASE-SOURCE-CASEID_v0.4_closure`) → 本書§2-§5＋CASEID-001 で実質吸収済。形式 closure note として別出力可。
2. **`alo_source_registry_seed_v0.1.jsonl`**（41行・confidentiality_class 付与）→ builder `build_forum_registry_seed.py`(Box 2264377914086) が現存。**実行して再生成可能**。
3. **`registry_negative_test.py`**（9 assertion）→ §4 RP-01〜06 と §1 分離不変則から **テスト仕様を再構成**（matter_scoped_only の5点guard・open限定backfill・jufu global禁止を assertion 化）。

## 8. 昇格条件

- deterministic_self_verification = **done**（`registry_negative_test.py` v0.2 = **15/15 green, exit 0**。RP-01〜06＋must_fix#3〜#6 を符号化）
- independent_meaning_audit = **`DDCASESOURCE_PASS_WITH_NOTES`（2026-06-19, GPT-5.5 Pro）**。must_fix 6点を本版・seed・test に反映済（#1 recon_status 明記／#2 v0.4=blocked_unrecoverable_reconstructed／#3 open∧public のみ global／#4 commercial/restricted/manual/matter_confirmed 出口禁止 assertion／#5 same_matter は mcp_serve 限定／#6 record override）。
- owner_approval = **未了（ratify はオーナー専決。`owner_confirm_required: true`）**。

> accept 後の経路（監査 next_action）: owner ratify → DD台帳 backfill → forum_registry_seed 実生成（Mac CC, local TTL+CSV, 再現ログ＋SHA 添付）。production DDL / canonical mint / global embedding / MCP serve / export / claim_support は追加 record-level 出口設計まで **HOLD**。

---

### 付記：本 recon 版の限界
原本の逐語・数値（seed 41行の内訳、negative test の具体 assertion 文言、§D5' の原文見出し番号）は復元できていない。意味（3軸分離・case_type enum・RP-01〜06 の趣旨・不変則整合）は Box 残存材料で再構成済み。原本がローカルから発見された場合は本書を `superseded_by` で更新し差分照合する。
