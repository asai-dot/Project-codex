# DD-LITID-001 v0.2 レビュー補強 ── 積層(thin→thick)の観点【査読メモ v0.1】

- 作成: 2026-06-15 / Claude（リモートセッション・浅井さん指示）
- 対象: `DD-LITID-001_biblio_identity_noisbn_draft_v0.2`（Box 2275006797196）＋ GPT監査 `DESIGN_PASS_WITH_NOTES`（2275637858392）
- 立場: 本設計の**採用方向は支持**。override でなく `PASS_WITH_NOTES` の notes を「積層」観点で1段深める査読補強。最終権限は owner＋お目付け役。
- **重複回避（既出ゆえ扱わない）**: fingerprints正本化／entity_type='biblio_item'／serial・article親子／rights gate／provenance_group(TOC)／publisher_norm保守的exact／work_id初期nullable／§3 required gates。

> 視座: DD-LITID は **「どう同定するか(identity)」** を厚く設計しているが、**「同定後に各ソースの薄い属性をどう積層して厚い正準値にするか(projection/merge)」** が手薄。基本戦略「巨人の肩に乗る＝薄いを編んで厚く」の心臓部は projection 側にある。以下はそこに集中した穴。

---

## R1【最重要】scalar属性に「観測層」が無い ── 積層が scalar で成立しない

- **箇所**: §5.2 `biblio_item`（title/publisher/pub_date/page_count/**genre** 等を**単値カラム**で保持）／§5.5 は `toc_observations` という多観測層を**TOCにだけ**用意。
- **問題**: 同定で N 個の source-item が1つの `biblio_item` に解決した時、**genre・page_count・pub_date 等の scalar はどのソースが勝つかが未定義**で、単値カラムゆえ**他ソースの値は捨てるしかない**。「LION BOLT genre＋弁コム category＋legallib 分野＋NDL分類を合議して厚くする」が**構造的に不可能**になる。TOCには観測層があるのに scalar には無い非対称が本丸の穴。
- **根拠**: §5.5 で TOC は `toc_observations(source_system, provenance_group, confidence, observed_at)` と多観測設計。scalar に同等物が無い。
- **推奨修正**: TOC と対称に **`biblio_item_attr_observations`** を新設。
  `(item_id, attr_key, value, value_norm, source_system, provenance_group, confidence, observed_at, parser_version, rights_profile)`。
  `biblio_item` の scalar 列は**この観測群からの決定的 projection（正規値）**とし、原観測は append-only で保全（「データ落とすな」＝bib_toc→toc_nodes の map正本主義と同型）。これが無いと R3〜R6 が効かない。

## R2【regression】分類(NDC/NDLC/件名)が新スキーマに居場所を失っている

- **箇所**: §5.2 `biblio_item` は `genre`(単値) のみ。**`ndc`/`ndlc`/`subjects` 列が無い**。
- **問題**: 既存 `bib_records` には `ndc`/`ndlc` 列があり蔵書で投入実績（5,503/5,020）。新 `biblio_item` で**置き場が消えている**＝移行で分類が落ちる。今日確認した「NDLにNDC/NDLCは在る・parse済み」という最良の積層素材の出口が無い。
- **根拠**: live 実測（親doc §5.6）＝asai-bookshelf に ndc/ndlc 投入済み。§5.2 に対応列なし。
- **推奨修正**: 分類は scalar 単値でなく **R1 の attr_observations＋subject層**で持つ（NDC/NDLC/件名/ベンダーgenre を別 `scheme` で併存）。`biblio_item` には正規分類の projection だけ置く。

## R3 属性レベルの「衝突」と「時点」が表現できない

- **箇所**: §5.2 `identity_status`（item 単位の provisional/candidate/resolved/split）。
- **問題**: (a) **属性の不一致**（弁コム pub_year 2019 vs legallib 2020、genre 保険法 vs NDC 324）を表す場所が無く projection で**静かに上書き**される。属性衝突は厚さの裏のリスクであり、同時に**誤同定の検知シグナル**（束ねた途端に矛盾＝マージ誤りの疑い）。(b) ソース再取得で値が変わる（弁コム後から abstract 追加、LION BOLT 再OCRで accuracy_rank 変化）時の **supersession/as-of** が未定義。
- **推奨修正**: attr_observations に `observed_at`＋append-only を必須化、projection に **conflict フラグ**（同一 provenance_group 外で値が割れたら `disputed`）。disputed は人手 review と誤同定監査の入力へ。

## R4 信頼度の「伝播モデル」が無い ── 厚くしても“重み付き”にならない

- **箇所**: §5.5 `alo_toc_nodes.canonical_confidence/source_votes`、§5.3 identifier `confidence`。
- **問題**: 個々に confidence はあるが、**属性ごとの正規値に「権威×新しさ×OCR品質×合議」を合成した field_confidence を出す関数が未定義**。積層の対価は検索/RAGの重み付け（評価設計 C7）だが、その重みを serving が消費できる形で**出力していない**。厚い＝列が増えるだけになりかねない。
- **推奨修正**: `field_confidence = f(source_priority, recency, ocr_accuracy_rank, provenance-group-deduped agreement_count)` を決定的に定義し、projection の各正規値に付す。serving は relevance 重みに使う。

## R5 OCR品質(accuracy_rank/source_type)が観測の信頼度に未接続

- **箇所**: §5.5 `toc_observations.confidence`、§5.4 `biblio_asset`。
- **問題**: LION BOLT `accuracy_rank(A/B/C)`・`source_type(scan/digital)`・`vertical` は「この観測テキストをどれだけ信じるか」の一級メタだが **observation.confidence の seed に使う規定が無い**＝C-rank縦書きscanのTOCとA-rank digitalのTOCが同じ重みで合議に入る恐れ。
- **推奨修正**: 取込時 `confidence_seed = g(accuracy_rank, source_type, vertical)` を入れ R4 へ伝播。asset 側にも OCR品質を保持。

## R6 provenance_group を「属性観測層」へ拡張（R1 の必須帰結）

- **箇所**: §5.5 provenance_group は **TOC観測にのみ**定義。GPT P1 も identifier/metadata 側は示唆止まり。
- **問題**: 弁コム×legal-library が同一出版社メタ/TOCを再配信なら **genre や year の一致も独立でない**。R1 を入れるなら provenance_group は scalar 属性にも**必須**。合議 confidence(R4) は provenance_group で**1票に畳んでから**数える。
- **推奨修正**: provenance_group を attr_observations の第一級次元にし、agreement_count は group 単位で算定。

## R7 work層と item層の「属性ロールアップ」が未定義

- **箇所**: §5.1 `biblio_work`（work_id 初期nullable）／§5.2 item 中心。
- **問題**: 分類・件名・ジャンルは**版を越えて安定**（「会社法」のNDCは版が変わっても概ね同じ）＝**work層で合議すると強い**。物理属性（page_count・TOC・ISBN）は item層。work_id を late/nullable にすると、**版横断のジャンル合議という最も効く積層を取り逃す**。
- **推奨修正**: 「どの属性が work へ rollup（分類/件名/ジャンル/著者）か、どれが item 固有（物理・TOC・版表示）か」の**属性別 scope 表**を設計に追加。work 合議は candidate→promotion 制で誤結合を防ぐ。

## R8 ジャンル/分類の正準語彙・crosswalk が無い（合議の前提）

- **箇所**: §5.2 `genre`（自由値）。
- **問題**: LION BOLT genre[]・弁コム category/series・legallib 分野・NDC は**語彙が別物**。crosswalk 無しに「合議ジャンル」を作ると apples-to-oranges。
- **推奨修正**: ピボットを **NDC**（NDLにあり標準・安定）に取り、各ベンダー genre→NDC範囲の crosswalk を `subject_scheme`＋対応表で持つ。自前 `genre_l2` を作るならこの上に。

## R9 「自所保有(蔵書)」が identity source / 属性として弱い

- **箇所**: §5.3 id_type enum（isbn/ndl/cinii/doi/lionbolt/bencom/legallib/box/pdf...）に**蔵書(bookdx)由来IDが無い**。
- **問題**: 事務所にとって「この本を**物理的に持つか／棚はどこか**」は最重要の実務属性。asset に physical_copy はあるが、**蔵書を identity source として明示・「自所保有」を厚い属性に projection** する設計が薄い。
- **推奨修正**: id_type に `bookdx_id` を追加、projection に `held_by_office`(bool)＋`shelf_locator` を昇格属性に（research時の「すぐ参照可」シグナル）。

## R10 「厚さ」を測る指標が無い ── 積層の効果が観測されない

- **箇所**: lane plan は identity 進捗（cluster/confirmed/held）を台帳化。厚さの指標が無い。
- **推奨修正**: item/コーパス単位で **thickness 指標**（属性数・裏取りソース数(provenance dedup後)・conflict率・field_confidence分布・held_by_office率）を IDENTITY_PROGRESS か serving health に追加。評価設計 C1/C3/C7 の前段メータ。

---

## まとめ（優先度）

- **本丸 = R1**（scalar属性の観測層）＋ **R2**（分類の居場所喪失）。この2つが無いと積層は scalar で成立しない。`toc_observations` と対称に **attr_observations 層＋subject/scheme 層**を足すのが最小で最大の修正。
- 次点 = **R4/R5/R6**（field_confidence と OCR・provenance の伝播）＝厚さを“重み”に変える配線。
- 設計判断 = **R7（work/item rollup scope）・R8（NDCピボットcrosswalk）**。
- 実務価値 = **R9（自所保有属性）**。観測 = **R10（thickness指標）**。
- いずれも DDL/backfill を要さず、**設計追補（owner decision＋お目付け役）**段で足せる。採用方向そのものは支持。
