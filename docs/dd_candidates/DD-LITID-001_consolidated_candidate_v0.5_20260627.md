# DD-LITID-001 v0.5（統合版）— 文献同一性・観測層・4信号 fingerprint・独立性 leaf binding candidate

> **id**: DD-LITID-001 / **version**: candidate v0.5（**consolidated**）/ **supersedes & absorbs**: v0.2-draft（biblio_identity_noisbn・Box 2275006797196）/ DD-LITID-001-ATTR v0.1（属性観測層・Box 2286087523073）/ DD-LITID-FP（4信号 fingerprint・Box 2287161796030）/ DD-LITID-PLAN 4route v0.1（運用計画・Box 2292468018025）
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-27 JST
> **lifecycle**: candidate（**設計のみ**）。DDL/DB/既存 lit_id 移行/backfill/mint/OCR/embedding/canonical promotion/serving/Box mutation は **HOLD**。
> **version 整理**: cleaned design record（Box 2286222789037・6/15）は「DD-LITID-001 **v0.4**」を latest-pointer として記帳していたが、discrete な凍結 accepted 成果物は存在せず、実体は上記4断片に分散していた。本 v0.5 は**その4断片を単一の凍結候補に畳む**（v0.4 ポインタの不整合を解消）。
> **depends_on（pin）**: **DD-INDEP-LINEAGE-001 v0.1**（独立性 lineage 正本・accepted・RESULT 2306834650821・content_hash a7856be1…）/ NDL SRU dataset（authority）/ 既存 control.* governance。
> **監査系譜**: v0.2 `DESIGN_PASS_WITH_NOTES`（RESULT 2275637858392）・ATTR `DDLITID_ATTR_DESIGN_PASS_WITH_NOTES`（2286160319588）・FP/PLAN `DESIGN_PASS_WITH_NOTES`。本 v0.5 は統合再監査（gate=DDLITID）対象。

---

## 0. 統合の射程（4断片→1・何を畳んだか）
| 断片 | 主内容 | v0.5 での位置 |
|---|---|---|
| v0.2-draft | 同一性3層（work/item/asset）・ISBN=証拠・fingerprints 正本・resolution_log・serial/article・rights ゲート・E3/E4 fingerprint・provenance_group/source_lineage | §1 同一性モデル／§3 fingerprint／§5 解決／§7 権利 |
| ATTR v0.1 | 観測層の対称化（scalar/分類も多観測→決定的 projection）・厚さ≠正しさ・anti-hallucination 接地・Stage1/2 分離・attr_registry | §2 観測層／§6 正しさ原則 |
| FP | 4信号 fingerprint（pub_date/edition/page_count/TOC）・TOC を no-ISBN 主証拠に | §3 fingerprint 強化 |
| PLAN 4route | holding/edition/work/source_biblio_item/authority・NDL ハブ O(n)・可逆性で工程分離・4カウント | §1 拡張モデル／§8 運用パイプライン |
| 共通 | provenance_group / source_lineage / origin_publisher（同一供給元を独立票にしない） | **§4 独立性 leaf binding（最重要）** |

**統合で良くなった点**：(a) 同一性と属性が**同じ「多観測→決定的 projection」型**で対称に揃う、(b) 独立性の数え方が**入口でも三部作と同一の leaf 正本**に束ねられる、(c) 4ルート運用と同一性スキーマが1文書で筋を通す。

## 1. 同一性モデル（統一）
v0.2 の3層に、PLAN の holding/authority/source 軸を統合。**「対象の同一性」と「所有」と「観測源」を分離**する。
```text
biblio_work        抽象著作・シリーズ（版違いを束ねる上位クラスタ）    uri alo:lit:work:{opaque}
biblio_item        特定刊行物＝版/刷（= edition / manifestation）       uri alo:lit:item:{opaque}   ★TOC/PDF/chunk の中心
biblio_asset       保有実体（local_pdf/box_file/physical/scanned）       uri alo:lit:asset:{opaque}
holding            自所が現に所有する実体（物理＋裁断）＝所有の SoT     -- PLAN 由来。asset に owns
source_biblio_item 4ルート各々の生書誌レコード（ソース固有 ID 不破壊）  -- 複数 source が同一 item を指してよい（版を束ねない）
authority          NDL（＋CiNii/KAKEN）＝edition/work 解決の権威ハブ     -- §8 突合の中心
```
- **item = edition**（単行本では同義）。`record_kind ∈ {book_edition, serial_issue, article, chapter, web_resource}`。serial/article は `parent_item_id`/`container_item_id` で親子維持（単行本ルールで誤マージしない）。
- **ID 不変原則**：ISBN が後から見つかっても `item_uri`/`toc_node_id` は変えない（`identifier(isbn13)` を足すだけ）。旧 `alo:book:isbn/manual:*` は alias 保持。
- **ISBN は証拠であって主キーでない**（正規 ID は opaque ULID/UUID・外部 ID から決定的生成しない）。
- **G_LITID_ID_STABLE**：正規 item_uri/toc_node_id は外部 ID 発見で不変。**G_LITID_SERIAL_NOT_BOOK_MERGE**：serial/article を単行本 fingerprint で混ぜない。

## 2. 観測層（append-only 観測＝正本 → 決定的 projection＝派生）
TOC で確立した「多観測→決定的 projection」を **scalar/分類にも対称適用**（ATTR の本丸 R1）。**二重正本にしない**＝単値列は派生。
```text
biblio_item_attr_observations  -- append-only・正本（削除しない）
  obs_id ; item_id? ; source_item_id ; attr_key ; attr_scheme? ; value_raw ; value_norm
  source_system ; provenance_group ; observed_at(主張時点) ; created_at(取得時点)
  medium_origin(digital|paper_scan) ; ocr_accuracy_rank? ; rights_profile ; raw_payload_ref
  is_active ; supersedes_obs_id?            -- 訂正は新行＋supersedes（旧は is_active=false で保全）
biblio_item_attr_canonical     -- 決定的 projection・派生（再計算可能・projection_version）
  item_id ; attr_key ; attr_scheme ; canonical_value ; cardinality(single|multi)
  agreement_count ; contributor_groups[] ; conflict_status(single_source|corroborated|disputed)
  field_confidence            -- ★Stage2 へ繰延（Stage1 は null・接続点のみ予約）
attr_registry                  -- 属性ごとの規律
  attr_key ; attr_scheme ; cardinality ; rollup_scope(item|work) ; value_type ; norm_rule ; priority_profile ; currency_sensitive
toc_observations / alo_toc_nodes   -- v0.2 §5.5 既存（観測→canonical TOC）。本層の先行実装＝同型
```
- **時点モデル**：取得時点（transaction・append-only で as-of 再現）／主張時点（observed_at）／版は item 粒度（valid-time を属性で持たない・DDL-20260428-01「版を束ねない」）。
- **rollup**：分類/件名/著者＝work 合議（multi）／page_count/pub_year/edition_statement/volume＝item 固有（single）。
- **G_LITID_OBS_APPEND_ONLY**：観測 update/delete 0。**G_LITID_PROJECTION_DETERMINISTIC**：同一観測群→2回 projection で hash 一致。**G_LITID_NO_SCALAR_SECOND_SOT**：biblio_item scalar は canonical の派生（独立書込み0）。

## 3. fingerprint 証拠（E1–E5・FP 反映）
```text
E1 isbn13            正規化＋チェックディジット検証後のみ id_type=isbn13（非ISBN値は載せない）
E2 vendor ids        lionbolt/bencom/legallib/box_file/pdf_sha256 …（ベンダー内では強いが正規 ID にしない）
E3 biblio_fingerprint_v1 = sha256(title_norm + publisher_norm + pub_date + page_count + edition_statement_norm + volume_no_norm)
                     ★FP: year → pub_date（年月日）に細粒度化（年同一でも月日で別版弁別）
E4 toc_fingerprint_v1 = sha256(headings_norm列 + level列 + page_range列 + article/form_number列)
                     ★FP: no-ISBN 層（弁コム/legallib・TOC 100%）では準・主キー級に格上げ。page範囲ずれ=版差候補
E5 pub_date+edition+page_count+TOC の合議      ISBN 無しでも版レベル確定に近づく4信号
```
- **判定**：強書誌一致＋TOC 高一致＝自動候補／一部一致＝人手／タイトルのみ・出版社のみ・年のみ＝**禁止**。
- **既知 gap（FP）**：弁コム biblio raw に page_count 無し → NDL `ndl_pages` から補完。pub_date は各ソース別フィールド→年月日へ正規化1本化。
- **G_LITID_VALID_ISBN13** / **G_LITID_FP_COLLISION**（未レビュー衝突0で自動マージ）。

## 4. ★独立性＝DD-INDEP-LINEAGE-001 leaf へ binding（v2 監査の最重要発見・循環なし consume）
入口が独自語彙（provenance_group/source_lineage/origin_publisher）で持っていた「同一供給元を独立票にしない」反こたつ記事の核を、**三部作と同じ leaf 正本へ一方向 binding** する。入口と confirmed/eligible で独立カウントが食い違わないようにする。
```text
# 正本は leaf（DD-INDEP-LINEAGE-001 §5）。LITID は写像して consume（独自に再定義しない）。
provenance_group        → leaf same_origin_collapse_key         （転載/同一供給元 TOC を1票へ collapse）
source_lineage          → leaf upstream_lineage_id              （上流原稿/版元/editorial 系譜）
origin_publisher / redistributor_chain → leaf content_independence_group 算定の入力
medium_origin/OCR run（観測 pipeline）  → leaf observation_lineage_root（同一 raw は1系統・OCR違いは別票でない）
独立裏取り数 agreement_count = leaf content_independent 準拠（同一 group 内一致は多数決にしない）
独立性 pin: id=DD-INDEP-LINEAGE-001 / version=v0.1 / content_hash=a7856be1…/ acceptance_ref=RESULT 2306834650821
```
- **G_LITID_INDEP_SOURCE_LEAF**：独立カウント正本は leaf。LITID は provenance_group/source_lineage を leaf に binding して consume し、独自定義しない。
- **G_LITID_PROVENANCE_NO_DOUBLE_COUNT**：agreement_count は leaf collapse 後に算定（PLAN: 同 origin=0.5証拠/異 origin=1.0証拠 もこの binding に従う）。
- **G_LITID_UNKNOWN_LINEAGE_CONSERVATIVE**：upstream/collapse 不明の観測だけでは独立を立てない（leaf note5）。

## 5. 同一性解決（可逆・disputed で止める）
```text
identity_candidates + resolution_log   -- merge/split を即実行せず候補＋履歴（可逆）
identity_status: provisional | candidate | resolved | split_required | deprecated_alias
```
- 値が割れたら（single 基数）**勝手に多数決せず disputed で人手へ**（薄くても正しい1値 ＞ 厚いが曖昧）。
- **G_LITID_RESOLUTION_LOG**：自動/人手の merge/split に根拠。**G_LITID_CONFLICT_SURFACED**：single 基数の値割れは必ず disputed（静かな上書き0）。

## 6. 厚さ≠正しさ・anti-hallucination（owner 方針）
- **採用値は必ず実観測（obs_id＋source＋raw_payload_ref）に接地**。観測の無い値は存在できない＝でっち上げの余地を**データ層で構造的に排除**（serving/RAG は採用値とその出所のみ）。
- **単独の権威観測（例 NDL 1件）でも採用可**（裏取り数は採用の必須条件でない）。厚さは KPI にしない。
- **Stage1（綺麗な層別観測＋採用値抽出）→ Stage2（field_confidence 重み付け）**を**並行しない**（混ぜると汚れる・owner 確定）。
- **G_LITID_ADOPTED_VALUE_GROUNDED**：canonical 採用値は ≥1 obs_id に接地（接地100%が KPI）。

## 7. 権利ゲート（rights_profile 継承）
購読サービス由来データは種別ごとに利用範囲を分け、観測→projection→serving で rights が閉じる。raw payload=local/Box 限定・正規化メタ=個人機械内検索・本文/embedding=別承認。
- **G_LITID_RIGHTS_INHERITED**：rights_profile が観測から serving まで継承され閉じる。**DD-LIT-NORIGHTS-001 整合**：独立 rights DD は作らない（各 DD 内の source traceability で扱う）。

## 8. 4ルート運用パイプライン（PLAN 4route・参照統合）
自所物理/裁断・LION BOLT・弁コム・legallib の4ルート＋NDL を、**NDL をハブに O(n)**（4ルート総当り O(n²) を避ける）で版同定。**可逆性で工程分離**：
```text
🔴 不可逆・安価 → 取得時に必ず捕捉: source_provenance_chain / origin_publisher / redistributor_chain
   / rights_profile / medium_origin / 取得時刻・主張時刻（取り損ね=復元不能）
🟢 可逆 → 本番分布で較正: pub_date 配点 / page_count 許容差 / TOC 類似閾値 / disputed TTL（proxy で決め打ちしない）
🟠 不可逆・高価 → shadow 実証後にゲート開放: candidate→confirm promote / canonical serving 反映 / DDL / backfill
```
- **4カウント**：work（著作）/ edition（版・刷）/ holding（所有実体）/ access（購読閲覧・所有でない）を区別。
- **Phase 0–6**：背骨確定→raw 投入（append-only・ノーリスク）→正規化/fingerprint→NDL 突合 shadow→実分布較正→promote/projection/count→定常運用（増分マッチ）。
- 詳細手順は PLAN 4route（本 DD に統合・実行は実装ゲートで個別 GO）。

## 9. DD-LITLINK-001 の扱い（**別 DD として維持・推奨**）
LITLINK（文献→法令/判例/語彙/他文献/書式の link signal・candidate・alo_edges export）は **LITID に吸収しない**。
- **理由**：LITID＝「どの本が同じ本か（同一性）」、LITLINK＝「その本が何を参照するか（リンク/所有境界）」で責務が異なる。三部作は両者を**別々に**依存（XDOC v0.9 §8 OWNERSHIP_NO_REDEF が block_ref/lit_link/xdoc_alignment を区別）。吸収すると LITID が肥大し所有境界がぼける。
- **ただし LITLINK も別途凍結＋leaf consume が必要**：lit_link_candidate の corroboration（独立裏取り）も §4 と同じく leaf へ binding。LITLINK の凍結は本 v0.5 とは別タスク（owner 判断）。
- **G_LITID_LINK_OWNERSHIP**：link/edge は LITLINK の責務。LITID は identity のみ（再定義しない）。

## 10. ゲート一覧（統合・dedup）
ID_STABLE / SERIAL_NOT_BOOK_MERGE / OBS_APPEND_ONLY / PROJECTION_DETERMINISTIC / NO_SCALAR_SECOND_SOT / VALID_ISBN13 / FP_COLLISION / **INDEP_SOURCE_LEAF / PROVENANCE_NO_DOUBLE_COUNT / UNKNOWN_LINEAGE_CONSERVATIVE** / RESOLUTION_LOG / CONFLICT_SURFACED / ADOPTED_VALUE_GROUNDED / RIGHTS_INHERITED / LINK_OWNERSHIP。

## 11. 受入試験（全自動 PASS が条件）
1. ISBN 後発でも item_uri/toc_node_id 不変（alias 追加のみ）。
2. scalar/分類が観測→決定的 projection（2回で hash 一致）・biblio_item scalar は派生。
3. 採用値は必ず obs_id 接地（観測なき canonical=0・anti-hallucination）。
4. **provenance_group/source_lineage が leaf へ binding され、同一供給元の TOC 再配信が独立2票にならない**（§4・leaf content_independent 準拠）。
5. **不明系譜の観測だけでは独立にしない**（leaf note5）。
6. single 基数の値割れ→disputed（静かな上書き0）。
7. serial/article を単行本 fingerprint で誤マージしない。
8. 4信号（pub_date/edition/page_count/TOC）で edition_suspected を真別版/表記揺れ/同名異本に腑分け。
9. work/edition/holding/access の4カウントが定義通り分離。
10. rights_profile が観測→serving で閉じる。

## 12. owner 決定事項（残るもの・要 ratify）
1. **LITLINK を別 DD 維持**（推奨）か LITID 吸収か。→ 推奨：別維持（§9）。
2. **本 v0.5 を DD-LITID-001 の凍結正本**とし、v0.2-draft/ATTR/FP/PLAN を superseded とするか。→ 推奨：そうする。
3. §2 観測層の biblio_item scalar を VIEW 化 or キャッシュ列（推奨：当面キャッシュ列・正本は観測）。
4. classification を multi・work rollup（推奨：そうする）。
5. field_confidence は Stage2（推奨：段階分離）。
6. 自所保有/原典到達（held_by_office/shelf_locator/fulltext_access）を厚い属性に（推奨：採用）。

## 13. GO / HOLD / loop_state
- **GO**：v0.5 統合 design ratify／leaf pin 整合（§4）／DDLITID 再監査投函／Stage1 観測 dry-run（射影シミュレーション・重みは出さない）。
- **HOLD**：DDL/DB/既存 lit_id 移行/backfill/mint/OCR/embedding/canonical promotion/serving/Box mutation／canonical の本番反映。
- loop_state = **consolidated candidate（v0.5・4断片を1本化・独立性を leaf へ binding）→ DDLITID 再監査 → owner ratify で入口 DD 凍結**。凍結後に RECONCILE §7 の DD-LITID-001 pin（version+content_hash+acceptance_ref）を実値化し Phase1 dependency gate を緑化。
