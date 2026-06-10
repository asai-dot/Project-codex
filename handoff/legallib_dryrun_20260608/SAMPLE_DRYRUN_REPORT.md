# legallib 接合 サンプル・ドライラン 実機検証レポート（web 側）

- 実行: 2026-06-10 / web CC
- 入力: Box `20260608_legallib_join_sample/`（resolver_sample.jsonl 43行 / legallib_dl_sample 42 JSON / _inspect_output.json）
- canonical 側: Box `app/data/toc/`（個別 ISBN を実取得）/ books.json は 33MB のため web からは全件取得不可（後述）
- 結論: **接合ツールは実データで概ね期待どおり動作。ただし重大1件（converter のネスト未対応）を発見し本セッションで修正。加えて要判断3件。**

---

## 0. 何を実機実行したか
- **Tier 1（resolver 全 43 行・実データ）**: `validate_resolver` / `detect_mismerge` / バケット振り分けを実行。
- **Tier 2（converter＋policy ゲート・実データ代表ケース）**: 実 legallib ノード変換、実 toc に対するゲート判定。
- 環境制約: 全 42 legallib＋全 toc＋33MB books.json を web の context に載せるのは不可。よって Tier 2 は代表 ISBN を実取得して検証、books.json 突合は近似（Mac 全実行で確定すべき部分を明示）。

## 1. 確認できた「正しく動く」点（実データ）
- **converter のキー前提一致**: title=`label` / level=`level` / page=`pdf_page`（96.6%）。実データと完全一致。
- **誤マージ0ガード（実データ）**: `blocked_bad_isbn` ×2 / `blocked_missing_isbn` ×1 / `blocked_ambiguous_isbn` ×2 / `blocked_ambiguous_book` ×2 — **全て期待どおり**検出。
- **バケット振り分け**: `human_review`→review_queue ×5 / `defer_new`→defer_staging ×4 — 一致。
- **policy ゲート（実 toc）**: `9784130311908`（openbd・24ノード・フラット・全simple）→ **overwrite_simple**（期待一致）。
- Tier 1 の guard/routing は **16/16 一致**（policy 要の23行は Tier 2 へ）。

## 2. 発見

### F1【重大・本セッションで修正済】legallib TOC はネスト（children 木）で、converter が子を取りこぼしていた
- 実 legallib（例 115441）の `toc` は **`{level,label,pdf_page,kind,children:[...]}` の木**。フラットな列ではない。
- 旧 `convert_legallib_nodes` は**トップレベルのリストのみ**処理し `children` を再帰しなかった → 115441 は本来 **12 ノード**だが **2 ノードしか出力されず子10件が欠落**。
- 同様に `inspect_legallib_dir` も非再帰で、`level_histogram: 全て level=1` と**誤報告**（実際は深いネスト）。ワーカーの「flat が混じる」観測の正体。
- **修正**: `flatten_nodes()`（pre-order DFS）を追加し、変換前にネストを平坦化。`inspect` も再帰集計（`top_level_nodes` / `nested` を併記）。
- **再検証**: 115441 → **12/12 ノード**、depth l1/l2/l3 正、parent_toc_node_id 復元正、pdf_page 転載正。回帰テスト `test_nested_children` 追加。全 157 checks 緑。

### F2【要判断・resolver 規約】空 ISBN の auto_accept が defer 期待だが blocked_bad_isbn になる
- サンプルの 4 行（355062/72945/250067/185908）は `bucket=auto_accept` かつ `isbn=""` で **`defer_staging` 期待**。だが `blocked_bad_isbn` 期待の 2 行（292812/210974）と**入力が同一形状**。
- ツールは両者を区別できず**6行すべて `blocked_bad_isbn`**。
- 推奨: **「canonical 対象なし」は `bucket=defer_new` で表現**（auto_accept は有効 ISBN を持つ不変条件を維持）。代替として「auto_accept＋空ISBN → defer_staging」にツール側を寄せる手もあるが、規約側で揃える方が安全。

### F3【要判断・policy/ラベリング】bencom の深い既存 TOC が status=simple のため上書き対象になる
- `9784641046429` の既存 toc は **bencom・104ノード・3階層ネスト＋ページ番号**の**リッチな目次**。だが全ノード `toc_status="simple"`。
- simple-only ゲートは「全 simple かつ非保護ソース」で上書き可と判定 → **overwrite_simple**。ワーカー期待は **route_human_review**。
- 根本原因: **`toc_status` の付与が実態とズレ**（構造化済 bencom が "simple" 扱い）。simple-only ゲートはラベルの正確性に依存する。
- 推奨（いずれか owner 判断）: (a) 上流で構造あり/ページありの TOC は非 simple にラベル是正、(b) ゲートが構造深さ・ページ有無も見て保護、(c) bencom を保護ソースに含める。

### F4【軽・preflight】validate_resolver が重複 book_id で hard-fail する
- 重複 book_id（ambiguous_book テストの 224420×2）で `validate_resolver` が exit 1。だが本体 `detect_mismerge` は重複 book_id を `blocked_ambiguous_book` として**安全に処理する設計**。
- 推奨: preflight の重複 book_id を **error→warning** に下げる（本体ガードに委ねる）。

## 3. books.json 突合について（web 制約）
- books.json は 33MB で web の context に取得不可。よって `blocked_missing_isbn`（合成 9789999990001）と `create`（実 ISBN・toc 無し）の厳密な区別＝**実 books.json 突合は Mac 全実行で確定**してください。
- 本検証では known_isbns を「実サンプル ISBN=在籍／合成=不在」で近似。誤マージ系・gate 系の結論はこの近似に依存しません（ISBN形式と既存tocのみで判定するため）。

## 4. 本セッションでのコード変更（PR #5）
- `scripts/legallib_to_canonical.py`: `flatten_nodes()` 追加、変換前に平坦化（F1 修正）。
- `scripts/inspect_legallib_dir.py`: children 再帰集計（`top_level_nodes`/`nested`）。
- `tests/test_legallib_join.py`: `test_nested_children` 追加。全 157 checks 緑。

## 5. 次アクション
1. **F2/F3/F4 は owner/resolver 判断**（GPT DD に回す候補）。特に F3（toc_status ラベリング）は接合の安全性に直結。
2. **Mac で全 43 行＋実 books.json の完全ドライラン**を実行し、本レポートの近似部分（missing_isbn / create 区別、全 overwrite/review 件数）を確定。F1 修正後の converter で再取得すると legallib 側のノード数が実数（children 含む）になる点に注意。
3. 確定後、承認 ISBN を `--only-isbns` で `legallib_join_apply.py --commit`。
