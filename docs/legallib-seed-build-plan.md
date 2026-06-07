# legallib → biblio 取込プラン v0.5.1（ライブスキーマ準拠 ＋ INGEST監査応答）

> status: レビュー用（v0.5.1）。**v0.1〜v0.3（alo.works/toc_nodes/fingerprints/メダリオン）は撤回・superseded。**
> 正本(SoT)は Box の ALO 仕様書＋CODEX設計＋**ライブ `biblio` スキーマ**。
> 対象DB: Supabase `asai-dot's Project`（`nixfjmwxmgugiiuqfuym`）の **既存 `biblio` スキーマ**。
>
> **v0.5 の差分**: GPT お目付け役の `legaldb v0.5 DESIGN_RESULT`（MODIFY_REQUIRED）の横断指摘 F1/F2/F5/F6 を
> 本 biblio 層に落とし込み（§A〜§E）。
> **v0.5.1 の差分**: 本プラン自身への監査 `20260606_legallibbiblio_v0.5_INGEST_RESULT.md`（判定 **INGEST_NEED_MORE**、
> 設計方向は全項目「採る／修正して採る」）の指摘を反映 → §G。著者IDを誤統合0構造保証へ（per-occurrence 既定）、
> terms scheme を `LEGALLIB_RAW_INDEX` に、重複/drift/非改変の観測クエリを sanity_checks に追加。
> PASS には生JSONサンプル＋dry-run evidence が必要（§G の6点）。

## 0. 状況（ライブ確認済み 2026-06-06）
`biblio` は稼働中。bib_records 10,326 / bib_toc 552,544 / authors 2,200 / terms 554 / bib_terms 0。

| source | 件数 | 備考 |
|---|---|---|
| asai-bookshelf | 6,624 | 事務所所蔵(BookDX)。form_type細分類・ISBN高率 |
| bencom-library | 3,802 | BOOK/PERIODICAL/WEB。ISBNほぼ無し |
| **legal-library** | **0** | **未投入＝本タスク** |

ローダ正本: `github.com/asai-dot/asai-biblio-ingest`（private）の `load_bencom.py` / `ingest.py`。
取込3層方針: コード=GitHub正本 / ドキュメント=Box正本 / 構造化データ=Supabase正本。

## 1. 結論
**legallib は既存 `biblio` への source 追加**。bencom・asai-bookshelf と同じテーブル形状に載せ、`load_bencom.py` に倣った `load_legallib.py` を書くだけ。スキーマ変更なし（＝Data API再公開も不要）。

## 2. conform先（既存スキーマ・変更しない）
ライブ確認済みの列：
- `biblio.bib_records`(PK bib_id text): title, title_yomi, subtitle, responsibility, edition, publisher, pub_place, pub_year(int), series, volume, physical, isbn, issn, ncid, ndl_bib_id, ndc, ndlc, language, note, **source**, raw(jsonb), imported_at, updated_at, source_url, source_hash, form_type
- `biblio.authors`(PK author_id text): name, name_yomi, name_roman, alt_names(text[]), birth/death_year, dates_note, ndl_auth_id, viaf_id, source, raw, updated_at, **normalized_key**
- `biblio.bib_authors`(PK bib_id,author_id,role,ordinal): role default 'creator'
- `biblio.bib_toc`(PK bib_id,ordinal): **ordinal(0始まり) / level(int) / page(int,null可) / text** — フラット構造
- `biblio.terms`(PK term_id): term, term_yomi, scheme, broader_id(self FK), scope_note, source, raw / `bib_terms`(PK bib_id,term_id)

## 3. マッピング（legallib → biblio）
| legallib | → biblio | 規則 |
|---|---|---|
| 内部book_id | `bib_records.bib_id` = `LEGALLIB:{book_id}` | 決定論的・source-local |
| isbn | `isbn` | あれば。**マージキーにはしない**（同定はauthorityで後） |
| 書名/出版社/出版年/責任表示 | title/publisher/pub_year/responsibility | source-thinはauthority層で解決、biblioは忠実保全 |
| 生JSON | `raw` (jsonb) | 全保全。`source_hash`=sha256, `source_url`=legallib URL |
| — | `source` = `'legal-library'` / `form_type`='BOOK' | |
| 著者 | `authors` + `bib_authors` | `LEGALLIB-AUTH:{md5(normalized)}`、`normalized_key`でdedup、**複合著者は分割しない**(bencom方針)、role='creator' |
| `{l,p,t,level}` | `bib_toc` | ordinal=配列位置(0始まり)、level=level、page=p、text=t。**parent/toc_node_id等は不要**（bib_tocはフラット） |
| 巻末索引 | terms/bib_terms | scheme='LEGALLIB'。**後フェーズ**（bencom同様まず空でも可） |

## 4. ローダ手順（load_bencom踏襲・冪等）
取込順（FK厳守）: `authors → bib_records → bib_authors → bib_toc`（→ terms/bib_terms 後）。
- 500/1000件バッチ upsert、決定論ID（再実行で同一）、`--dry-run`、`--limit`、`SUPABASE_SCHEMA=biblio`、service_role key。
- 実測（bencom 55万TOC）約3分 → legallib 2,751冊も同程度。

## 5. ゲート/検証（sanity_checks.sql 流用 + 追加）
- `source='legal-library'` の bib_records が legallib件数(2,751)と一致
- bib_toc 孤児 0（FK）/ ordinal が book内 0始まり連番
- 既存 source（asai-bookshelf/bencom）が**一切改変されない**
- 再実行 diff 0（冪等）
- normalized_key 衝突で別人を統合していない（誤統合0）

## 6. 後続（biblioの外・別フェーズ）
- **横断同定（マスター）**: `authority.publication/source_record/publication_author_evidence/publication_author_claim`（未構築）。ISBNで asai-bookshelf(所蔵)↔legallib↔bencom を **promotion制で**突合、**版は束ねない**(DDL-20260428-01)、誤マージ0。
- **control lineage**: snapshot/ingest_job/batch（bencom契約どおり薄く追加）。
- **catalog/serving/telemetry**: アプリ投影は後。
- **雑誌**: legallib PERIODICAL 422号は次スコープ（巻号正規化未確定）。

## 7. 要決定／ブロッカー
- `bib_id` 採番 = `LEGALLIB:{legallib_book_id}` で良いか（ISBN基準にしない方針でOKか）
- `form_type` = 'BOOK' 統一か、asai-bookshelf式の細分類（treatise/qa…）を付与するか
- 巻末索引 terms を今やるか後か
- **コード置き場**: `load_legallib.py` は private repo `asai-biblio-ingest` に置くのが筋（私の現GitHubスコープは `project-codex` のみ＝直接pushは別途権限/手段が要る）。当面このrepoにドラフトを置き、後で移送も可
- **legallib生JSONの実トップレベル列**（書名/著者/出版社等のキー名）確認 → マッピング確定（1冊実物が要る）

---

# v0.5 増分（legaldb v0.5 監査整合）

上位設計 `STATIC_DB_INTEGRATION_PLAN v0.5`（判例/法令/文献DB全体）への GPT 監査
`20260606_legaldb_v0.5_DESIGN_RESULT.md`（**DESIGN_MODIFY_REQUIRED**）の横断指摘のうち、
書誌(biblio)層に効く F1（anchor governance）/ F2（識別子責務分離）/ F5（文献identifier table）/
F6（citation/treatment は candidate）を本プランに落とし込む。

## §A 識別子責務表（F2 への回答）— biblio は manifestation/expression 外部IDと source-local キーのみ持つ

GPT 指摘 F2:「`alo_work_uri / external_work_id / expression_id / manifestation_id / locator` の責務を
分離せよ。さもないと v0.4 の source_uri 分裂が別名で再発する」。biblio をこの責務表に明示的に写像する：

| FRBR/責務 | 定義 | legallib biblio での持ち方 | 列 |
|---|---|---|---|
| **alo_work_uri**（ALO正準・Work） | 版を束ねた抽象著作の同一性 | **持たない**（後述） | — |
| **external_work_id** | 外部標準のWork識別子 | **持たない**（後述） | — |
| **expression/manifestation 外部ID** | 版・刷の外部識別子 | legallib内部book_id・ISBN | `bib_id`内・`isbn` |
| **source-local record key** | 「このソースが見た1版」の記録キー | `LEGALLIB:{book_id}` | `bib_records.bib_id`(PK) |
| **locator**（章節） | 版固有の位置参照 | TOCの出現順・階層・頁 | `bib_toc.(ordinal,level,page)` |

**要点（GPT への主張）**:
- **ISBN は Work 識別子ではなく manifestation（版・刷）識別子**。よって ISBN をマージキーにしないのは
  DDL-20260428-01（版を束ねない）と F2（Work と manifestation を混同しない）の**両方に整合**する。
- **biblio 層は意図的に Work URI を mint しない**。biblio = 「各ソースが観測した1 manifestation の忠実保全」
  （source-thin）。版を束ねる Work 同一性は **authority 層で promotion 制・誤マージ0・版非束ね**で後段。
  → これにより「source_object_uri を Work IRI に固定して既存URIと衝突」という F2 の地雷を biblio では踏まない
  （そもそも biblio に Work IRI を置かないため）。
- `bib_id='LEGALLIB:{book_id}'` は **source-local record key** であって canonical URI ではない。
  canonical 化（alo_work_uri）は authority 層の仕事。biblio の bib_id は外部に対する同一性を主張しない。

## §B anchor ⊥ locator 規律（F1/F3 への回答）— bib_toc は locator であって anchor ではない

GPT 指摘 F1/F3:「offset/ordinal は expression 固有の **locator** であり、Work/Expression 横断の
**anchor** に使ってはいけない。anchor は mint・lineage 管理せよ」。

- `bib_toc.(bib_id, ordinal)` は **locator**。再スクレイプで TOC が変われば ordinal はずれ得る = それで正しい
  （locator は版固有・再計算可能でよい）。
- biblio は **TOC ノードに stable_anchor_id を mint しない**。章節の安定アンカー（検索/RAG/章節ナビ用）は
  serving/authority 層の関心事として後段に切り出す。biblio は raw の決定論的射影に徹する。
- **版固有性の担保**: bib_toc は `raw`(jsonb) の決定論的射影であり、`raw` の同一性は `source_hash`(sha256) で
  追跡する。raw が変われば source_hash が変わり再射影で検知できる。= F3「offset は text_version と複合で持て」の
  biblio 版（ordinal は bib_id=その source の版レコード に内属し、版同一性は source_hash が担う）。

## §C candidate 規律（F5/F6 への回答）— 索引・著者・雑誌記事は truth に直結しない

GPT 指摘 F6:「citation/treatment を未定義のまま本番 edge に入れると candidate を truth 扱いする v0.4 regression」。
biblio で「観測」と「同定」を分け、後者を candidate に留める：

- **巻末索引 terms**: scheme='LEGALLIB' で**生の索引語を忠実保全するのみ**。語彙ハブ（alo_hubs/Term=sense）への
  attach・broader 付与は **candidate**（後フェーズ・promotion 制）。biblio.terms に入れること自体は truth 主張ではない。
- **著者**: `LEGALLIB-AUTH:{md5(normalized)}` は **source-local の名寄せ**であって人物同一性の確定ではない。
  横断の person 同定（所蔵↔legallib↔bencom↔CiNii）は authority/evidence/claim で candidate→reviewed→promoted。
- **雑誌記事（次スコープ）**: F5 に従い、記事を biblio に投入する際は **article_work_id を ALO が mint し、
  DOI/NDL/CiNii/誌面文献番号/巻号頁は identifier 子テーブルにぶら下げる**。巻号頁だけの一致は candidate match。
  （現フェーズは書籍のみ。雑誌は本規律を満たす設計が固まってから。）

## §D over-reach ラベル（F・§3 への回答）— 確定度を主張ごとに明示

GPT 指摘「research-backed / primary-verified / grey-lit / design-synthesis を各主張につけよ」。本プランの確定度：

| 主張 | ラベル | 根拠 |
|---|---|---|
| biblio スキーマ形状（bib_records/bib_toc 等の列） | **primary-verified** | ライブDB実測 2026-06-06 |
| bib_toc がフラット（親を持たない） | **primary-verified** | ライブDB実測 + bencom raw 実物 |
| load_bencom.py の取込順・冪等・決定論ID | **primary-verified**（パターン） | 既存ローダ稼働実績 |
| legallib 生JSONのトップレベル列名（書名/著者/出版社キー） | **design-synthesis（未検証）** | 実物1冊未取得＝TODO。ローダにTODO明示 |
| ISBN=manifestation 識別子という FRBR 解釈 | **research-backed** | FRBR/USLM の Work⊥Manifestation 区別 |
| 雑誌記事 article_work_id+identifier子テーブル | **design-synthesis** | legaldb v0.5 F5 を踏襲、実装未着手 |

## §E 上位設計（legaldb v0.5）への入れ子

- 本 biblio 層は legaldb v0.5 の**文献(literature)レイヤの最下流＝忠実保全層**に当たる。
  legaldb v0.5 の dual-anchor / Work IRI / citation edge は **authority 以上の層**の話で、biblio は
  その**素材（manifestation 観測）を欠損なく貯める**役割に限定する（責務の上下分界）。
- legaldb v0.5 が MODIFY_REQUIRED なのは主に **法令時間軸（DD-LAWTIME 依存）と識別子責務と treatment 語彙**。
  **書籍 biblio 取込はこれらに依存しない**（法令時間も treatment も書籍メタには不要）。よって
  **legallib 書籍取込は legaldb v0.5 の保留事項にブロックされず、先行して着手可能**。
- ただし「後段 authority 昇格」を設計する時点で、§A の責務表 4〜5 列分離と §C の candidate 規律を必須とする。

## §F v0.5 で確定した回答（旧 §7 ブロッカーの解消状況）

1. `bib_id='LEGALLIB:{book_id}'`（ISBN非キー） → **確定**。§A で FRBR/DDL-20260428-01/F2 と整合を示した。
2. `form_type`: 書籍は **'BOOK' 統一**（asai-bookshelf 式の細分類は authority/serving 層の派生属性として後段）。
   雑誌は 'PERIODICAL' だが次スコープ。
3. 巻末索引 terms: **生保全のみ今フェーズ可・語彙attachは後**（§C）。まず空でも可。
4. コード置き場: 当面 `project-codex/loaders/` にドラフト、確定後 `asai-biblio-ingest` へ移送。
5. **残る唯一の hard ブロッカー**: legallib 生JSONの実トップレベル列名（§D で design-synthesis＝未検証）。
   実物1冊で `load_legallib.py` の TODO 5箇所を確定すれば実装着手可能。

---

# v0.5.1 増分（INGEST監査 NEED_MORE への応答）

監査 `20260606_legallibbiblio_v0.5_INGEST_RESULT.md`：判定 **INGEST_NEED_MORE**（hard regression なし・
設計方向は §A〜§E すべて「採る／修正して採る」）。PASS に上がらなかった唯一の理由は **生JSON未確認**で
推測 ingest を許せないため。以下、指摘のうち**サンプル不要で即反映できる分を実装済**。

## §G-1 反映済（コード/SQLに落とした分）
- **Finding 2 著者誤統合（実装変更）**: `make_author_id` を **per-occurrence 既定**へ。
  `LEGALLIB-AUTH:{book_id}:{ordinal}:{md5[:8]}` で出現ごと一意＝**biblio内で別人を構造的に統合しない**
  （誤統合0を保証）。横断同定は authority で candidate→reviewed→promoted。`--author-id-mode dedup` で
  従来の md5 名寄せもオプトイン可。あわせて bib_authors.ordinal を著者順に修正（旧 0 固定バグ）。
- **Finding 5 terms scheme**: 生索引語は `scheme='LEGALLIB_RAW_INDEX'` とし raw 性を明示。broader/hub attach
  は禁止（NULL固定）、語彙ハブへの接続は authority 側。
- **Finding 3 重複の可視化**: `sanity_checks.sql ⑨` に legal-library×他source の ISBN一致 duplicate
  candidate レポート（統合しないが観測する）。
- **Finding 7 既存source非改変 / dry-run**: `⑪` に取込前後で突合する行集合ハッシュ test、`⑩` に著者誤統合0の
  不変条件チェック、`⑫` に source_hash ベースの TOC drift 検知の足場（Finding 4）。

## §G-2 PASS に必要な追補（生JSONサンプル待ち＝Phase 0 で取得）
監査が PASS_WITH_NOTES へ上げる条件として挙げた6点。`loaders/INSTRUCTION_legallib_inspect_and_ingest.md`
の Phase 0 出力がそのまま充足する：
1. legallib raw JSON **3サンプル**（通常書籍 / 索引あり / 深いTOC）
2. 確定 **mapping table**（top-level / author / TOC / index）← `--inspect` 出力で確定
3. `--dry-run --limit 3` の出力例
4. 既存 asai-bookshelf / bencom に **差分0** の test（`⑪`）
5. **再実行 diff 0** の test（`⑥`）
6. 著者誤統合を起こさない初期ID戦略 ← §G-1 で per-occurrence 既定化して充足

## §G-3 再監査フロー
Phase 0 報告（3サンプル＋mapping＋dry-run）が返ったら、本プランを v0.5.2 として `supersedes:
20260606_legallibbiblio_v0.5_INGEST` で `to_gpt/` に差分再投函 → PASS_WITH_NOTES を取得 → owner ratify →
Phase 1（実投入）。
