# P1 ブロッカーB: Wave URL 実在性確認 結果（read-only web）20260625

> doc_kind: 確認記録（read-only web） / author: Claude / date: 2026-06-25 / owner: 浅井
> 親: 02_P1_DICT008_ACCEPT_READINESS §1.B / DD-DICT-008 §13
> gate: read-only web 検索のみ。取得・DB・accept は実行しない。

## 0. 結論（一行）

**未確認4 Wave のいずれも新規 bedrock(rank100-102) を追加しない。** W1c は既存 rank101(有斐閣)と
**同一編者で実質重複**、W1b は構造化辞書でなく web コラム連載、W3a/W3b は低権威・散在の専門用語集(rank≥103 attach 領域)。
→ **bedrock は現有資産(e-Gov rank100 + 有斐閣 rank101 + 学陽 rank102)で完結**。B は accept の物理的ブロッカーではない。

## 1. 確認結果（4件）

| Wave | 対象 | 実在 | 形式 | 評価 |
|---|---|---|---|---|
| **W1b** | 参議院法制局「法令用語の例」 | ✅ 有 | **web コラム連載**「法律の[窓]」(HTML記事: column018 法令用語と法解釈 / 052 用語の定義 / 065 送り仮名 / 089 題名・略称 / 091 漢字使用 等) | 構造化辞書でなく解説記事。enrichment 候補だが bedrock ではない。スクレイプ要 |
| **W1c** | 内閣法制局「法令用例集」 | △ 単独web版なし | 内閣法制局の用語編纂物＝**有斐閣法律用語辞典(内閣法制局法令用語研究会編)＝既存 rank101**。別途 web 用例集は不見当(あるのは「漢字使用等」H22長官決定=表記規則) | **既存 rank101 と重複**。Wave から外す or「rank101でカバー済」と明記 |
| **W3a** | 法務省 民事局/刑事局 用語集 | ✅ 有 | web HTML(moj.go.jp/Houmu_Show/term, KIDS 民事局/刑事局=簡易版) | 一般向け軽量用語集。低権威=rank≥103 領域。bedrock ではない |
| **W3b** | 金融庁・経産省・消費者庁 ガイドライン用語集 | ✅ 散在 | web HTML(金融庁 監督指針/ガイドライン群, J-FLEC 用語集 等。単一の用語集なし) | DICT-008 の「散在」記述どおり。**rank≥103 専門 attach** 領域 |

## 2. accept への含意（DICT-008 §6.1 ブロッカーB の解消）

- **B は解消**: 4件とも実在性・形式を確認。**新規 bedrock を足さない**ため accept の前提を満たす。
  - W1c → 「rank101(有斐閣)でカバー済」として Wave 計画から除外 or 注記。
  - W1b → enrichment(将来 rank?)候補。bedrock-first ゲートに影響なし。
  - W3a/W3b → rank≥103 specialty attach（DD-DICT-008 の attach-only 方針どおり。canonical 昇格しない）。
- bedrock 物理ゲート(rank≥103 は anchor 不可)は現有3辞書で成立。**Wave 未取得は accept をブロックしない**。

## 3. 残るブロッカー（owner レビューのみ）

B が解消したので、DICT-008 accept の残りは **owner レビュー A1/A2/A3 だけ**（02 §1.A）:
- A1: DICT-008 v0.2 本体 OK/NO
- A2: 34層 §4.1(bedrock-first)/§9(gate 2本) 改訂計画 review
- A3: DDL gate 2本＋§2.3.1 gate 条件改訂の影響範囲 review

→ owner がこの3点を判断すれば accept 可。Wave 取得は accept 後の enrichment 作業に降格。

## 4. ゲート

read-only web 検索のみ実施。取得・スクレイプ・DB・accept は未実行（別ゲート）。
W1c の Wave 除外、W3a/W3b の rank 確定は DICT-008 amendment（owner 承認）で反映。

## Sources
- [法律の［窓］｜参議院法制局](https://houseikyoku.sangiin.go.jp/column/index.htm)
- [法令用語と法解釈｜参議院法制局](https://houseikyoku.sangiin.go.jp/column/column018.htm)
- [法令における用語の定義｜参議院法制局](https://houseikyoku.sangiin.go.jp/column/column052.htm)
- [法令における漢字使用等について（H22 内閣法制局長官決定）](https://www5d.biglobe.ne.jp/Jusl/Bunsyo/BunHoureiH22.html)
- [有斐閣法律用語辞典（内閣法制局法令用語研究会編）](https://www.amazon.co.jp/dp/4641000174)
- [用語集｜ほうむSHOW（法務省）](https://www.moj.go.jp/Houmu_Show/term/index.html)
- [告示・ガイドライン・Q&A・法令解釈事例集一覧：金融庁](https://www.fsa.go.jp/common/law/kokuji.html)
- [用語・金融商品｜J-FLEC](https://www.j-flec.go.jp/public/learn/glossary/)
