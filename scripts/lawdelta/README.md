# lawdelta — 条文テキスト差分検出器（DD-LAWSUBTRANS-001 Phase 2 / T1 producer）

2つの consolidated revision（e-Gov 法令標準XML or 条文JSONL）を入力に、条単位の
textual delta を **Akoma Ntoso `textualMod` 準拠の分類**で出力する。

```
python -m scripts.lawdelta OLD NEW --law-id 129AC0000000089 \
    --from-rev <law_revision_id> --to-rev <law_revision_id> \
    --snapshot-id <source_snapshot_id> --out out/
```

出力: `out/law_textual_delta_<run>.jsonl`（T1 契約）＋ gate 結果付き summary。**DB書込みゼロ。**

## 設計原則（DD-LAWSUBTRANS-001 §0/§4）

本検出器は**形式の観測のみ**を行う。`delta_kind` はテキストに何が起きたかであり、
**実質的変更の主張ではない**。出力に substantive 系フィールドが混入しないことを
`gate_no_substantive_fields` で強制し、「textual_delta のみを根拠とした実質変更主張」は
DD §4 `amendment_not_auto_substantive` が禁止する。

## アルゴリズム（世界標準への接地）

多段 anchor-then-relax アラインメント。各段の出典は調査正本
`docs/reference/REFERENCE_law_substantive_transition_prior_art.md` 及び下記。

| Phase | 内容 | 先行事例 |
|---|---|---|
| A | **条番号アンカー**。同番号ペア→ no_change / substitution。類似度 < `SUBST_MIN`(0.50) の同番号ペアは**破断**しプールへ | consolidation 系（Norma-System, legislation.gov.uk effects は被改正条文を番号で指す）／破断は git **diffcore-break** |
| A' | 「第X条 削除」shell（`Delete="true"`/本文「削除」）→ repeal（番号は残る）。削除番号の再利用→ insertion | e-Gov XML v3.0 仕様（30_law_layer §4.4） |
| B1 | 未マッチ集合間の**高信頼リネーム**: `pair_score ≥ RENUMBER_SIM`(0.92) を類似度降順 greedy | git **diffcore-rename**（候補対の類似度スコア→greedy best-first。既定閾値50%、法令域は0.6–0.7 が precision 側） |
| C | **split/join**: 非対称 containment（`CONTAIN_PART`=0.55、被覆 `SPLIT_COVERAGE`=0.60）。relocate より先に判定（whole-vs-part の中位類似が relocate に勝ってしまうため） | MinHash 文献の containment 概念、AKN `textualMod` の split/join |
| B2 | **relocate 級**（0.60 ≤ s < 0.92）greedy | 同上 git 系 |
| 昇格 | **ブロックシフト**: 数値オフセットが一致するペアが2件以上（繰上げ/繰下げ）なら relocate→renumber | GumTree の move 検出に相当する run 整合性。USLM が renumber を第一級操作とする理由（識別子破壊） |
| 吸収 | 同番号 substitution に未マッチ旧条が containment で吸収→ **join**、対称で **split** | AKN join/split。第423条が第424条を吸収する型 |
| fallback | 破断した同番号ペアが最後まで未マッチなら substitution に復帰（repeal+insertion より正） | diffcore-break の復元と同型 |
| 残余 | repeal / insertion | — |

`pair_score` = 本文類似度（difflib ratio, NFC+空白除去）に**見出し（caption）類似度を10%混合**。
見出しは安価で強いアラインメント証拠（Toyama/Ogawa 系の知見）。長さ比 `LENGTH_RATIO_GATE`(0.30)
の git 型プレフィルタで候補対を絞る。

### delta_kind と AKN `textualMod` の対応

OASIS AKN Core v1.0 の TypeOfTextualMods は **repeal / substitution / insertion /
replacement / renumbering / split / join**。本実装の `relocate` は **AKN 型ではなく拡張**
（番号変更を伴う移動＋実質編集。AKN では renumbering+destination で表現される）。
`replacement`（全部改正型）は law 全体差し替えであり revision 層（DD-LAWTIME）の管轄。

### 日本特有の知見（重要）

- 名大 小川/外山グループは**改め文が16の正規表現パターンに形式化可能**であることを示した
  （…を…に改める→substitution／…を加える→insertion／…を削る→repeal／第X条を第Y条と
  する→renumber）。Springer: 10.1007/978-3-540-78197-4_34
- **lawhub の教訓**: 改め文の機械解釈は brittle で停滞した。**consolidated 版同士の diff**
  （本実装の方式）が頑健。改め文/新旧対照表は将来の**検証器**として使う（Phase 2.1）。
  https://github.com/lwhb/lawhub
- デジタル庁 法制事務デジタル化（2024）は逆方向（編集済み溶け込み条文→改め文/新旧対照表の
  自動生成）を構築中。操作分類の整合先として参照。

## 制約・次段

- v0.1 は**条粒度**。項・号粒度（`art:X:para:n` path）への細分は Phase 2.1
  （DD T1 `article_path` は既に下位粒度を許容）。
- 附則（SupplProvision）は対象外（lawtime の管轄）。
- 閾値は fixture 検証値。実 e-Gov revision ペアでの較正は production gate（DD §7）で行う。
