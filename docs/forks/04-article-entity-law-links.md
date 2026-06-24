# Fork 4 — 論文 entity ＆ 法令リンク（アイデア B・F）

> 上位: [`../00-metadata-join-fabric.md`](../00-metadata-join-fabric.md)
> 依存: Fork 1（所蔵紐付け部分）

## 目的

雑誌「タイトル　著者」を `{title, authors}` に分解 → 著者検索 / 引用組み立て。
TOC ↔ e-gov 法令の相互リンク（引用グラフの芽）。

## 前提資産

- 指示書: Box `cc_instruction_legallib_journal_article_parser_20260605.md`(2266423916572)
  （parse_rate 80% hard / 90% soft、出力 schema 確定済）
- 雑誌 422号 / 124,529 toc nodes
- git 履歴の `data/egov` 痕跡（法令データ）

## 最初の一歩

1. article parser を全422号スイープ → `articles_extracted.jsonl`
2. 著者正規化（同名著者の disambiguation は背骨の resolver パターンで）
3. TOC見出し / 論文中の条文・判例参照を抽出して e-gov 法令へリンク

## 検収

- parse_rate ≥ 80%（hard）
- 著者横断検索が成立
- 法令リンクのサンプル目検

## 関連 DD（TOC→法令リンクの精度設計）

- **DD-LINKBOOT-001**（反復・文脈累積リンキング）: GPT 監査 `DDLINKBOOT_PASS_WITH_NOTES`(2026-06-08)・
  owner ratify 方向。required_patches 7点を反映した v0.1.1＋B検証prototype計画は
  [`DD-LINKBOOT-001_v0.1.1_and_B_plan.md`](./DD-LINKBOOT-001_v0.1.1_and_B_plan.md)。
  canonical DD は Box `alo/`。high アンカーを主題化し medium を主題prior＋境界/外国ガードで昇格、
  promoted precision ≥0.95（層化gold≥300）まで production 禁止・`claim_support_eligible=false` 維持。
  上流 = DD-TOCLEGALREF v0.2、主入力 = legallib 詳細TOC（bib_toc 661K）。
