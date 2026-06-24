# P17: ローカルちゃん発注書 — D1文献編931誌 authority 完遂ハンドオフ

```yaml
artifact: P17_local_agent_handoff
generated_at: 2026-06-24 JST
audience: Mac側 Claude Code（ローカルちゃん）。フルデータ（931リスト/NDLバルク/labeled jsonl）が手元にある実行環境。
intent: 頭部155誌(記事被覆~74.65%)まで手検証済みの authority を、残りロングテール~776誌へ自動拡張し、頭部pending12誌を潰して931誌を完遂する。
gate: read-only検証 + authority CSV 拡張のみ。DB投入/canonical promotion/accepted edge化/外部公開はHOLD（DD-PERIODICAL-001のowner GOが要る）。
```

## 0. 現在地（クラウド側がここまでやった）
- 成果物: `artifacts/periodical/d1_journal_issn_authority_head_20260623.csv`（**155誌**）
  - verified 67 / correction 5 / ncid_fallback 13 / class_bessatsu_jurist 58 / **pending 12**
  - 記事被覆 約74.65%（225,546 / 302,130）
- ビルダ: `tools/d1_bunken/build_journal_issn_authority_v0.1.py`
  - `--ndl`/`--seed` は任意。seedのみ指定すると931全誌をseed優先で出力し、残りは`unresolved`。
  - normalize: NFKC + 旧字マップ + 接尾ノイズ除去 + 括弧修飾落とし。
- 別冊ジュリスト系（全〇〇判例百選）は NCID **BN01263667** の号として単一シリアルに集約済み。

## 1. やってほしいこと（ローカルちゃんのタスク）

### Task A — NDL誌名突合でロングテールを自動解決（本命）
Mac上のフルデータでビルダを **--ndl 付き** で回す。これが手検証では届かない~776誌を一気に埋める。

```bash
cd ~/Project-codex
python3 tools/d1_bunken/build_journal_issn_authority_v0.1.py \
  --labeled <build/labeled_v0.2.1/article_meta_labeled.jsonl のパス> \
  --ndl     <NDL書誌バルク jsonl|tsv のパス> \
  --seed    artifacts/periodical/d1_journal_issn_authority_head_20260623.csv \
  --out     artifacts/periodical/d1_journal_issn_authority_ALL_resolved.csv
```
- 出力status: `seed_*`(頭部確定・最優先) / `ndl_unique`(誌名→ISSN一意=採用) / `ndl_ambiguous`(複数ISSN候補=改題/隣接誌の疑い、**要レビュー**) / `unresolved`(NDL該当なし)。
- 末尾サマリの `resolved/931` を記録。`ndl_unique` がどれだけ稼げたかが成果。

### Task B — `ndl_ambiguous` のレビュー（精度の要）
複数ISSN候補が出た誌は**自動採用しない**。下記「隣接誌の誤マージ厳禁」リストに当たるものは exact一致のみ採用、判断つかなければ `pending` のまま残す。**偽マージを1件出すより未解決で残す方が良い**（owner方針: 下流精度優先）。

### Task C — 頭部 pending 12誌を潰す
WebSearch（NDL/CiNiiのタイトルはスニペットに出る。Portal/CiNii直fetchは403なので不可）で1誌ずつ確定し、head CSVの該当行を verified/correction/ncid_fallback に更新:

| 誌 | メモ（クラウド側の到達点） |
|---|---|
| 判例評論 | 判例時報の別冊。独立ISSNか判例時報号従属か要判定 |
| 銀行法務 | 銀行法務21(0385-0048)と**別誌**。混同厳禁 |
| 月刊債権管理 | 0914-417X は月刊民事法情報のISSN（衝突検出済）→誤採用するな |
| 法令ニュース | 要検証 |
| 発明 | 発明推進協会。ISSN要確認 |
| 医療判例解説 | 要検証 |
| 判例評論/法曹/手形研究/民事研修/中央労働時報/季刊労働者の権利 | head CSV内に重複行あり。確定値の方を残し重複整理 |

### Task D — マージ & 最終化
- A の `ndl_unique` + B の採用分 + C の確定分を head CSV に統合（または ALL_resolved.csv を正本化）。
- 重複行を整理（append順の重複が残っている）。
- 被覆%を再計算してサマリ md（P18）を書く。

## 2. 絶対に守る制約（owner固定ルール）
- **隣接誌の誤マージ厳禁（exact一致のみ採用）**:
  戸籍≠戸籍時報 / 登記研究≠月刊登記情報≠登記インターネット / 銀行法務≠銀行法務21 /
  金融法務事情≠旬刊金融法務事情 / 月刊債権管理≠月刊民事法情報。部分一致は ambiguous 行きで人手判定。
- **内部DB由来ISSNを鵜呑みにしない**。実際に複数誤っていた（税経通信=他誌ISSN混入, ビジネス法務/交通事故民事裁判例集/ビジネスガイド=未登録番号）。権威ソース（NDL/CiNii/ISSN Portal/出版社）で実誌名一致を確認できたものだけ verified。
- **キー優先**: ISSN-L > ISSN > NDLBibID > NCID。ISSN無し実務書/書籍系は NCID または isbn_per_issue。
- **gate**: DB投入・canonical promotion・accepted edge化・外部公開（Box/社外共有/再配布/fine-tuning/外部ベンダー処理）は**禁止**。authority CSV作成と検証のみ。`external_share_allowed` は全行 false。
- **ブランチ**: 開発は `claude/magazine-object-analysis-seg9cr` のみ。
- model id を commit/PR/artifact に書かない。

## 3. 完了の定義 (DoD)
1. 931誌中 `resolved`（seed_* + ndl_unique + 採用ambiguous + pending解決）の比率を最大化、残unresolvedは大学紀要/廃刊会報中心であることを明示。
2. `ndl_ambiguous` は全件レビュー済み（採用 or pending明記、未レビュー0）。
3. 頭部 pending 12 は確定 or 「現時点で権威ソース確認不可」を理由付きで記録。
4. P18サマリ md（被覆%、status内訳、残ロングテールの性質、未解決理由）を artifacts/periodical/ に作成。
5. ブランチへ commit & push。

## 4. データのありか（Mac内、クラウドからは見えない）
- 931 canonical リスト / by_journal_canonical 件数: `build/labeled_v0.2.1/summary_labeled.json` と `article_meta_labeled.jsonl`
- NDL書誌バルク: `ndl_download.py` 出力（雑誌レイヤ仕様§2.2/§5, ~240万レコード, title+issn(+ncid)）
- 931スケルトン: `artifacts/periodical/d1_journal_issn_authority_ALL.csv`（旧seed, 参考）
- 正本マップ（データ所在）: ローカル `docs/alo/INDEX_LATEST.tsv`（Box未ミラー）

## 5. 困ったら
- ビルダがseedを拾わない → head CSVのstatus綴り（verified/correction/ncid_fallback）と key_value 非空を確認（pendingはseed採用されない仕様）。
- NDL突合が0件に近い → norm_title の旧字/接尾ノイズ吸収を疑う。NDL側titleにも括弧修飾(出版者)が付くことがある。
- 判断に迷う隣接誌 → owner（asai@asai-lo.com）に上げる。勝手にマージしない。
