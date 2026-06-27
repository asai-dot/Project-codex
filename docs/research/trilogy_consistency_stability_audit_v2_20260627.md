# 設計三部作 横断整合性・安定性 再監査 v2（実データ投入前ゲート・closure 検証＋入口 DD 拡張）

> **date**: 2026-06-27 JST / **author**: 番頭(リモートClaude) / **status**: research record（v1 監査 6/24 の closure 検証＋入口 DD への拡張）
> **前監査**: `docs/research/trilogy_consistency_stability_audit_20260624.md`（v1・ドリフト7点と投入前チェックリスト §10）
> **問題意識（owner 再掲）**: DD は時系列バラバラに作られた。時的ずれによる矛盾／ドリフトが潜む。**実データを流す前に統一性・安定性を確認し、v1 で挙げた是正が本当に閉じたかを検証する。**
> **依拠**: v1 チェックリスト §10 と ratify 済み成果物（INDEP leaf / RECONCILE v0.3 / XMODAL v0.6 / XDOC v0.9a / joint manifest v0.2）の突合 ＋ Box 実体調査（LITID/LITLINK 凍結状態）＋ 適合性ハーネス（120テスト緑）。

---

## 0. 総合判定
**三部作（LAYOUT/XMODAL/XDOC）軸の時的ドリフトは設計レベルで閉じ、GPT 監査も各 DD で PASS。** v1 の7点中**6点が closed & ratified**。
ただし **実データ投入の前提は未充足**：
1. **§7（依存版固定）が唯一未閉鎖** — しかも事務的空欄ではなく、**入口 DD（LITID/LITLINK）がまだ単一の accepted 版に凍結されていない**という実体ブロッカー。
2. すべて**設計レベルの統一**であり、実データを実際に流す配線（DDL/alias/rename の適用）は各実装ゲートで **HOLD**（accepted≠deployed）。

→ 「意味は揃った・GPT 監査も通った。だが配線はこれから、かつ入口 DD の版凍結が先決」。

凡例：✅ closed&ratified / 🟠 設計closed・適用HOLD / 🔴 未閉鎖（前提ブロッカー）

---

## 1. v1 チェックリスト（§10）closure 検証
| v1 項目 | 是正の所在（ratify 済み） | 監査 | 状態 |
|---|---|---|---|
| 🔴 §1 独立性 registry 一元化 | **DD-INDEP-LINEAGE-001 v0.1**（正本・content_independence_group × observation_lineage_root の2軸）＋ XMODAL v0.6/XDOC v0.9a/RECONCILE v0.3 が一方向 consume | DDINDEP_PASS_WITH_NOTES（RESULT 2306834650821） | ✅ |
| 🔴 §2 snapshot 住所 | RECONCILE v0.3 §2 `law_authority_snapshot` typed contract（bitemporal＋hash）／corpus_snapshot_id→source_snapshots | DDRECONCILE_PASS_WITH_NOTES（2309127656929） | 🟠 設計closed（DDL=source_snapshots 列追加は HOLD） |
| 🔴 §5 block_type→facet | RECONCILE v0.3 §3 写像表（ALO=base組・header/footer 非absence・Formula=text+subtype） | 同上 | ✅ |
| 🟡 §3 coverage 用語 | RECONCILE v0.3 §4 `projection_typing_coverage` / `range_coverage` 分離 | 同上 | ✅ |
| 🟡 §4 asset/revision 命名 | RECONCILE v0.3 §5（`asset_id`/`source_text_revision_id` へ alias レベル統一・既存ID 再発行禁止） | 同上 | 🟠 設計closed（実 rename＝XDOC内部 text_revision 等の適用は HOLD） |
| 🟡 §6 canonicalization | RECONCILE v0.3 §6 **field-level canonicalization registry**（field_path→set\|multiset\|sequence・v1 の「XDOC §5 を正本」を昇格） | 同上 | ✅ |
| 🟡 §7 depends_on 版固定 | RECONCILE v0.3 §7 exact-pin **仕組みは定義**（id+version+content_hash+acceptance_ref・空欄は Phase1 gate fail） | 同上 | 🔴 **値が未充足**（§2 参照） |

**循環解消（v1 §1 の派生問題）**: XMODAL↔RECONCILE の相互参照を、leaf を pin して一方向 consume する DAG に変換。両監査が非循環を確認。joint manifest v0.2 §2 で in-edge のみを検証。✅

## 2. ★§7 ブロッカーの実体 — 入口 DD が未凍結（Box 調査）
§7 の pin が埋まらないのは**書き忘れではない**。exact-pin は accepted 成果物を要求するが、入口 DD にそれが無い：

**DD-LITID-001（実データの入口・84/611 ギャップ解消経路）**
- `biblio_identity_noisbn draft v0.1/v0.2`（2026-06-10・label=DESIGN_PASS_WITH_NOTES・Box folder 388663417438）— **draft 表記のまま**。
- 拡張が分岐進行中で未統合：`DD-LITID-001-ATTR`（attr observation layer・6/15・RESULT 2286160319588）／`DD-LITID-FP`（matching signal strengthening・6/16・RESULT 2287192002732）／`DD-LITID-PLAN 4route edition resolution`（6/18・RESULT 2293126734299）。
- 設計記録 `02_LIT_DESIGN_RECORD_CLEANED_20260615.md`（folder 389387126322）は存在するが、**単一の「DD-LITID-001 accepted vX.Y」凍結成果物が無い**。

**DD-LITLINK-001（外部リンク所有境界）**
- 専用の凍結 DD 成果物が**検出されず**。XDOC depends_on で版無し参照されるのみ（alo-kg/edges は関連だが DD ではない）。

→ **content_hash を今埋めることは、非 canonical な draft を pin する＝ exact-pin ゲートの目的に反し silent drift を再導入する。** ゆえに本監査は §7 を「埋めず未閉鎖」と記録する（正しい保守的判定）。

**§7 を閉じる正規手順（owner/upstream アクション・別ゲート）**：
1. LITID の draft v0.2＋ATTR＋FP＋PLAN-4route を**単一 DD-LITID-001 vX.Y に統合**し accept（凍結）。
2. LITLINK-001 を**独立 DD として起票 or 明示的に LITID 内へ吸収**し accept。
3. 凍結後の version＋content_hash＋acceptance_ref を RECONCILE §7（および XMODAL/XDOC の leaf pin と同様の依存 pin）へ記入 → Phase1 dependency gate 緑化。

## 3. 「設計統一」と「データ配線」のギャップ（実データ投入の実務前提）
v1/本監査の closure は**意味の統一**。実データが実際に矛盾なく流れるには、HOLD 中の以下の**適用**が必要（accepted≠deployed）：
- DDL: `control.source_snapshots` への `snapshot_kind=law_authority`＋bitemporal/hash 列追加（§2）。
- 命名適用: XDOC 内部 `text_revision`→`source_text_revision_id` の実 rename、asset_ref↔asset_id の alias マップ実体化（§4）。
- field canonicalization registry の実装（§6・各 artifact の profile_id/version 付与）。
- INDEP leaf の `content_lineage_binding`/`observation_acquisition_lineage` スキーマ実体化（leaf §2/§3・DDL/mint は HOLD）。
これらは**三部作の accept では deploy されない**。実装は各実装ゲートで個別 GO を要する。

## 4. 安定性（stability）所見
- **適合性ハーネス 120 テスト緑**（v1 時 105 → +15・INDEP leaf の独立カウント＋note5 保守化を含む）。単一 canonical_json 共有という最大の安定化資産は健在で、INDEP の独立判定（GROUP_UNKNOWN 保守化）まで executable に固定済み。
- ただしハーネスは**各 DD 内の整合**を見るもので、**DD 間語彙写像・入口 DD の版凍結は範囲外**（v1 §9 と同じ）。§2 の入口未凍結はハーネスでは検出されない。

## 5. 実データ投入前ゲート・残チェックリスト（v1 §10 更新）
- [x] ✅ §1 独立性一元化（INDEP leaf・ratified）
- [x] ✅ §5 block_type→facet（RECONCILE §3）
- [x] ✅ §3 coverage 用語（RECONCILE §4）
- [x] ✅ §6 canonicalization（RECONCILE §6・field-level へ昇格）
- [~] 🟠 §2 snapshot 住所（設計closed・DDL 適用 HOLD）
- [~] 🟠 §4 命名統一（設計closed・実 rename HOLD）
- [ ] 🔴 **§7 依存版固定 — 前提: LITID/LITLINK を単一 accepted 版へ凍結（最優先・入口）**
- [ ] 🟠 §3'（新）データ配線の実装 GO（DDL/rename/registry/leaf schema）— 各実装ゲート

## 6. 推奨アクション（最小・手戻り回避）
1. **入口 DD の凍結を最優先**：DD-LITID-001 統合 accept ＋ DD-LITLINK-001 の扱い確定（独立起票 or 吸収）。これが §7 と実データ入口の双方の前提。
2. 凍結後に RECONCILE §7 の pin を実値で記入し Phase1 dependency gate を緑化。
3. その後に初めて、データ配線（§2/§4/§6/leaf schema の DDL・実装）を実装ゲートで GO。
4. （任意）本 v2 監査を GPT 監査レーンへ投函し、closure 判定と入口凍結要件の妥当性を独立確認。

## 7. loop_state
research record（投入前ゲート v2）。**三部作軸の整合は設計閉鎖・ratified。実データ投入の次の前提＝入口 DD（LITID/LITLINK）の版凍結**。実装/DDL は引き続き HOLD。
