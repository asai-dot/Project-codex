---
request_id: DD-TOCADOPT-001-IMPL
topic: 統一TOC採用ルール 5ステップ+7gate 実装の批判的監査 (実装者の自己申告 weak points 付き)
gate: implementation_review
supersedes: なし
parallel_related: [DD-TOCADOPT-001, DD-EDIDENT-001, DDLEGALLIBCONCORD, DDSELFHEAL]
current_governing_result: DDTOCADOPT_PASS_WITH_NOTES (design-only owner ratify 済 / production_apply=HOLD)
result_expected_filename: DD-TOCADOPT-001-IMPL_result.md
status: queued
queued_date: 2026-06-16
守秘: 設計・状態語彙・件数レベルのみ。実依頼者データ本文は含めない。合成データのみでテスト。
---

# DD-TOCADOPT-001 実装の批判的監査依頼

## 0. 依頼の趣旨 (重要)

owner から「ぱっと見すごく雑に見える。実装者が**適当に作った疑いのある箇所**を全部ピックアップして
監査に回せ」と明示指示。そこで本依頼は通常の PASS 狙いではなく、**実装者(CC)自身が自信のない/
近道した/設計を解釈で埋めた箇所を §3 に洗いざらい列挙**し、その各点について是正可否の判定を求める。
**甘い PASS は不要。赤入れを期待する。**

production apply / canonical projection / policy 本番切替は **HOLD 継続**。本実装は投影のみ・書込ゼロ。
テストは合成データのみ (実 corpus は ALOBookDX 本流にあり本 repo には無い)。

## 1. 監査対象 (branch claude/legallib-integration-design-Jgrtf)

owner ratify 済 v0.2 ACCEPTED の 5 ステップ採用ルールと §4 の 7 required gate を実コード化:

- `scripts/toc_adopt.py` — 5 ステップ採用エンジン (adopt_book / adopt_corpus)。
- `scripts/toc_adopt_gates.py` — 7 gate 機械検査 (run_gates)。
- `scripts/make_tocadopt_golden.py` + `tests/golden/tocadopt/synthetic_multisource.jsonl` — 7 多源シナリオ。
- `tests/test_tocadopt.py` (143 checks) — 回帰ロック + 安全不変条件 + 7 gate 実走。
- 実装契約 = `data/toc_merge_policy_unified_DRAFT.json` (本 DD で確定済)。
- stdlib 全体 778 checks green。

## 2. 各ステップの実装要約 (1行)

- Step1 同一性: priority 最上位 source を**基準1点**に固定し、他源を pairwise で `classify_edition_identity_v2`。`resolved_same/manual` のみ合議、別版疑い/不足は human_review。
- Step2 基底: **ノード数**一次→ページ被覆二次→priority tie-break。granularity_guard(最富源比0.2) 未満は base 不可。protected 源は非 protected に base を奪われない。
- Step3 補完: append_missing_only。各ノードに provenance 5項目 + toc_node_id。pdf_page は book 単位 offset で print 整合。章執筆者を ndl_partinfo から付与。
- Step4 合議: votes を provenance_origin 単位で集計、3 origin で consensus。authority_resolver で PDF/consensus/human_review。
- Step5 記録: 投影層のみ。projection_sha は入力順非依存。

## 3. 実装者が自信を持てない箇所 (= 赤入れ対象。全件 owner 指示で開示)

重大度: **H**=採用の正しさに直結 / **M**=精度・整合性 / **L**=様式。

### A. Step1 同一性ゲート
- **A1 (H)** 基準源を **priority 最上位1点に固定**し全他源をそこと pairwise 判定している。
  classifier 本来の「全ペア worst-case」とは挙動が違う。B↔C が同版でも、基準 A の bib が
  曖昧だと B/C を誤って human_review に落とす/拾う恐れ。基準1点方式は妥当か、全ペア
  グラフ連結性で合議集合を決めるべきか。
- **A2 (M)** 基準源が **node を持たない bib のみ源 (canonical 等)** でも基準に採れる。
  node を持つ最富源を基準にすべきでは。

### B. Step2 基底選択
- **B1 (H)** 設計は「**粒度(深さ)**」を一次基準と明記するが、実装は **ノード数**で代理した。
  「浅いが多ノード」が「深いが少ノード」に勝ちうる。粒度=深さで測るべきか、ノード数で
  良いか、複合(深さ×被覆)か。granularity_guard 自体も**ノード数比**で書いた。
- **B2 (H)** `legallib_simple_only` の張替えセマンティクス
  (`overwrite_only_if_all_simple` / `skip_if_existing_already_legallib`) を**実装していない**。
  「既存 base が simple のときだけ詳細源で張替え」という増分ロジックを、granularity-first の
  一発選択に**簡略化**した。protected 保護だけ別途実装。これは設計逸脱か、等価か。

### C. Step3 ノード補完
- **C1 (H)** `source_hash` 欠落時に **`sha256(title_norm)` を捏造代入**している。provenance
  完全性 gate4 は通るが、実 source snapshot を指さない**偽 hash**。invention 禁止の精神に
  反するのでは。欠落時は補完不可(review)に倒すべきか。
- **C2 (M)** `toc_node_id = sha256(isbn + title_norm)[:23]`。**同一 title_norm の繰り返し
  見出し**(「第1節」等)が衝突する。DD-TOCATTACH v0.3 の sticky id 仕様(snapshot 同一性に
  紐付く)と整合するか。locator も含めて一意化すべきか。
- **C3 (M)** pdf→print 変換を **book 単位の単一 offset** で全 pdf ノードに当てる。
  `page_is_pdf` 判定は「print_page/page_start/p が無く pdf_page だけ」というヒューリスティック。
  源ごと/章ごとに offset が違う本では誤変換。Phase0 の 94.9% 単一を根拠にしたが残り 5.1% は。
- **C4 (H)** `partinfo_kind_filter` (contents 採用 / volume_structure 拒否 / mixed_small review) を
  **完全に未実装**。ndl_partinfo の巻構成ノードを TOC として誤採用しうる。これは明確な取りこぼし。

### D. Step4 保護と合議
- **D1 (H)** consensus False のノードも **projection に含めている** (human_review に分離していない)。
  設計は「源が割れたら human_review」。非合議ノードを採用扱いのまま projection に載せて
  よいか、別レーン(pending)に分けるべきか。
- **D2 (H)** `adoptable` を **edition identity のみ**で判定。authority=human_review でも
  `adoptable=True` になりうる。apply_guard の広い gate (conflict/nodes_accounted 等) と
  不整合。adoptable の定義に authority と consensus も AND すべきでは。

### E. policy 契約の取りこぼし
- **E1 (H)** policy の legacy `rules` ブロック (`replace_if_higher_source: true`) を**無視**した。
  これは私の append_missing_only-only 実装と**矛盾**する可能性 (高位源で既存を置換すべき
  場面を全て無視している)。`rules` ブロックは廃止前提の残骸か、有効な契約か。
- **E2 (M)** policy の `confidence` map を**未使用**。tie-break は priority のみ。confidence を
  base 選択や consensus 重みに使うべきだったか。

### F. gate 実装
- **F1 (M)** gate3 で per-source override を読まず **0.2 をハードコード**(engine は per_source を
  読むのに gate は読まない)。不整合。
- **F2 (H)** gate1 は **「自己再現(source 順を変えても sha 一致)」しか検証できていない**。
  実 baseline (ALOBookDX 631クラスタ/116,727ノード) が無いため、「既存 projection を**別ロジック
  でも**完全再現」という gate1 の本質は未検証。比較器(sha+base分布一致)で十分か、もっと
  強い同値検査(ノード集合・親子・ページの一致)が要るか。baseline export 様式の指定も請う。
- **F3 (M)** gate2 は known_conflict fixture に publisher/page_count が欠けると v2 判定が
  変わりうる。fixture を identity 判定の回帰前提に使う妥当性。

### G. テスト網羅
- **G1 (M)** テストは**合成 7 シナリオのみ**。実データ無し。各 step の分岐は突いたが、
  組合せ爆発(別版+guard+pdf 同時など)や敵対的入力(title_norm 衝突・空ページ・循環親子)は
  未カバー。C1(本番)前に必須の合成カテゴリ追加の指針を請う。

## 4. 監査への質問

1. §3 の各点 (A1〜G1) について **是正必須 / 許容 / 設計誤解** の判定を。特に **H 9件**を優先。
2. 上記のうち、**本番 apply 検討の前に必ず潰すべき blocker** はどれか (C1 gate に追加すべき項目)。
3. C4(partinfo_kind_filter 未実装) と E1(rules ブロック矛盾) は、私の実装が policy 契約を
   満たしていない可能性。policy 側を直すか実装側を直すか、どちらが正か。
4. gate1 の実 baseline 比較 (F2): ALOBookDX からどの粒度の baseline を export させれば、
   「統合 policy が既存 projection を壊さない」を十分に保証できるか。
5. この実装を「雑」から「本番手前」へ上げるための **最小 must_fix リスト**を順序付きで。

> production apply / canonical / RDB / policy 本番切替 = HOLD 継続。本依頼は実装レビューのみ。
> 実装は report-only で投影のみ・書込ゼロ。テストは合成データ (実依頼者データ無し)。
