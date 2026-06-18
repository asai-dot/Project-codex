# WO-D1HANREI-REFETCH-001（草案）: 判例→判例 直接引用（参照判例）の取得

> doc_kind: WORK ORDER 草案 / **設計のみ・実行承認ではない** / status: DRAFT（owner GO 必須・外部アクセス）
> author: Claude / date: 2026-06-18 / owner: 浅井
> 親: DD-DATAARCH-001 v0.2（関係層④a KG）/ relationship_layer_status_20260617 tier C
> 優先度: **silver 順序 #3** — 「反例が引く反例」を入れる唯一の経路。**外部取得のため owner GO + 別 WO 必須**。
> gate: 本草案は**設計のみ**。実取得（D1 再 DL）は owner GO・D1 セッション干渉回避策の合意後に発火。

## 0. 一行
現 D1 raw_hanrei は判例"一覧"エクスポートで **参照判例/参照条文フィールドを含まない（grep 0）**。
判例→判例 直接引用を入れるには **D1 全レコード（詳細）再取得**が必要。本 WO はその取得仕様を設計のみ確定する。

## 1. 不在の事実（measured）
- 関係層 tier C: **判例→判例 直接引用 = 0**。
- 根拠: `alo-ai/work/d1law_ingest_20260603/raw_hanrei/*.rtf` に参照判例フィールドが無い（grep 0）。
- 影響: 「反例が引く反例（後続判例が過去判例をどう引くか）」が現データから一切組めない。引用グラフ創発の最終ピース欠落。

## 2. 取得設計（実行は HOLD）
- 取得単位: 判例 canonical 192,998 を母集合に、**参照判例・参照条文を含む詳細レコード**を再取得。
- 段階: canary（小バッチ・フィールド存在と粒度の検証）→ 差分取得（既取得 192,998 との id 突合・重複回避）→ 本取得。
- 出力（取得後・別パケットで write）: `hanrei_cites_hanrei`（case→case）/ `hanrei_cites_statute`（case→条文）candidate。
  `citing_id` / `cited_id` / `cite_context` / `decision_status`(strong|review) / `evidence`。

## 3. リスク・制約（owner 判断事項）
- **外部サービスアクセス**（D1）= owner GO 必須。
- **D1 セッション干渉注意**（既存 D1 作業との衝突回避策の合意が前提）。
- 取得規律・クォータ・content-type 検証・rights/access policy の確認。
- 取得は build側①生レイヤへの append のみ。silver（参照ID解決）・canonical 化は後続別パケット。

## 4. 順序上の位置（背景メモ §6）
silver-1（掲載位置→判例ID）/ silver-2（TOC→論点section）が先。本 WO は silver-3。
1–3 が揃って初めて、引用グラフからの論点創発が乗る。

## 5. 本 WO で決めない / やらない
- 実取得そのもの（owner GO + 干渉回避合意後の別発火）。
- 参照判例 ID 解決・canonical mint・production mapping（後続別パケット）。

## 6. ゲート
- 本草案は read-only の設計記録。**外部取得・DDL・DB write はすべて HOLD**。
- 発火条件: owner GO ∧ D1 セッション干渉回避策の合意 ∧ canary 検証計画の確定。
