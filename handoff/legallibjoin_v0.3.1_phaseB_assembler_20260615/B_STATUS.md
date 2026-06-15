# legallibjoin v0.3.1 Phase B — books アセンブラ構築 + plumbing 検証 (2026-06-15)

> **report-only**: canonical / legallib / final_toc 一切書き換えなし。apply は HOLD 継続。
> evidence は **検証用 (golden-10) であり authoritative ではない**（理由は §3）。

## 1. 成果物

| ファイル | 内容 |
|---|---|
| `scripts/assemble_books.py` | concordance_pipeline 用の実データ book 入力アセンブラ。legallib 詳細TOC + resolver(book_id→ISBN) + canonical bib を結合し `{isbn,title,source_meta,sources}` を生成。**`--extra-sources` で第2 node 源を後から合流できる前方互換設計**。 |
| `validation_run_golden10/` | 既知 conflict golden 10 冊で end-to-end を回した report-only 出力（plumbing 検証）。 |

## 2. 検証結果（golden-10, report-only）

```
assemble: books=10  matched_isbn=10  with_2plus_node_sources=0   (← 退化を実証)
pipeline: risk={high:10}  apply_allowed=0   final_toc_written=false / toc_dir_written=false
```

- **evidence ⑤ apply_guard は実データで正しく機能**: golden 10 冊すべて `allowed=false`。
  refusal = `whitelist_required`（whitelist 未指定）＋ `edition_identity_resolved`（golden は
  実際の版衝突なので identity 未解決＝正しく検知）。→ ゲートは物理拒否している。
- **evidence ④ concordance は退化**: `matched=0`, 全ノード orphan, `all_nodes_accounted_for=True`
  （silent discard 無しは満たすが、cross-source 一致が 0）。

## 3. なぜ authoritative でないか（look-before-build で判明した本質）

ローカルに **node を持つ源は legallib 1 つだけ**:
- canonical `books.json` … bib のみ・**toc array = 0**（頁数欄も無し）。
- bencom（弁コム）… 書式 docx 索引であって book TOC node ではない。
- lionbolt / openbd / bib_toc の **node データはこの worktree に無い**（RESULT.md 等の文書のみ）。

concordance は title が **2 源以上**で一致したとき matched になる。単一 node 源では
全ノードが必ず orphan になり、cross-source conflict も立たない。
→ 意味のある evidence ④⑤ には **第2の node 源**が要る。これは mainline TOC-attach 側の
multi-source corpus（lionbolt / ndl_partinfo / bencom / bib_toc）であり、
**DD-TOCADOPT-001 が統合中**の対象そのもの（同DD §8.1 の projection dryrun=631クラスタ/116,727ノードが実在の多源 corpus）。

## 4. authoritative evidence ④⑤ までの依存（2 つ）

1. **A = DD-EDIDENT-001 の ratify + 実装**（強化版 classify_edition_identity）。
   現状 evidence は旧 classify。golden の版衝突は旧版でも high に落ちているが、
   過検知 226 の回収は強化版でしか効かない。
2. **第2 node 源の供給**（mainline bib_toc / lionbolt / bencom corpus）。
   `assemble_books.py --extra-sources <corpus>` で合流 → 1 コマンドで authoritative 化。

## 5. 次アクション（依存解消後）

```
# 第2源が来たら（例）:
python3 scripts/assemble_books.py \
  --legallib-dir ~/alo-ai/work/legallib_dl \
  --resolver     ~/alo-ai/work/legallib_dl/_resolve/resolver_decisions.normalized.jsonl \
  --canonical    <canonical books.json> \
  --extra-sources <2nd_source_nodes_dir> \
  --out          books_all.json
python3 scripts/concordance_pipeline.py --books books_all.json --only-isbns <owner_whitelist> --out evidence_dir
```

→ 強化 classify で all_nodes_accounted_for 照合 + apply_guard 拒否ログを golden 込みで生成
→ owner ratify → 初めて apply 検討（apply は HOLD のまま別ゲート）。

## 6. owner 判断（1 入力）

第2 node 源をどう供給するか:
- **(a)** mainline TOC-attach の multi-source corpus を legallibjoin レーンに渡す（DD-TOCADOPT-001 の統合を待たず、現存 corpus を `--extra-sources` で接続）。
- **(b)** DD-TOCADOPT-001 の統合 corpus 完成を待ってから authoritative run（重複構築を避ける）。

たたき台 = **(b)**（DD-TOCADOPT-001 が同じ多源統合をやっており、別経路を作ると二重管理）。
ただし (a) なら今すぐ意味のある ④⑤ baseline が出せる。
