---
request_id: 20260619_DB-OBSERVED-SNAPSHOT_litid
decision_id: DD-LITID 書籍同定パイプラインの DB 実測スナップショットによる前提検算（ドライラン計画 v0.1 の前提更新）
request_type: 観測検算 (OBSERVATION / premise-update gate)
topic: ISBN→NDL ドライラン計画 v0.1 の前提を Supabase 実測で検算した結果の監査
作成日: 2026-06-19
監査対象: artifacts/DB_OBSERVED_SNAPSHOT_litid_20260619.md（本依頼に要点同梱・§3）
source_hash: sha256:14c8e97d4128faf14145386ff9a0cb1ce63d6aaf335505c86472a323bb745e53
source_commit: e2f5a30 (branch claude/book-identification-progress-7yjxpc)
関連監査: ISBN→NDL read-only ドライラン計画 v0.1（監査中, to_gpt file 2294748599823）/ DD-LITID-PLAN v0.1（DESIGN_PASS_WITH_NOTES）
result_expected_filename: 20260619_DB-OBSERVED-SNAPSHOT_litid_RESULT.md
status: queued
gate: OBSERVATION。**read-only 観測の妥当性と、それがドライラン計画に与える前提修正の可否のみ。** DDL/実装/backfill/本番突合/promote は対象外。
---

# GPT Pro お目付け役 監査依頼: DB 実測スナップショット（DD-LITID 前提検算）

## 0. 独立監査の要請（迎合不要）

監査中のドライラン計画 v0.1 の前提を、Claude が Supabase 実データ（read-only）で検算した。
**結論ありきの追認は不要。** 観測の読み方の誤り・見落とし・過大解釈を厳しく疑ってほしい。
特に「自所は92%解決済みだから穴埋めだけ」という縮約が**楽観に倒れていないか**を見てほしい。

## 1. なぜ回すか

ドライラン計画 v0.1 は「ISBN持ち3ルート（self_scan / LION BOLT / legallib）を NDL に当てる」前提。
実測したところ**前提が動いた**。監査中の計画の射程が変わるため、観測の妥当性と前提修正の可否を問う。

## 2. 観測条件（再現性）

- source: Supabase project `nixfjmwxmgugiiuqfuym`、`execute_sql` の **SELECT/profile のみ**（DB無変更）。
- method: count/filter による被覆率・クロス集計。書込・DDL・promote 一切なし。
- 全文・全クエリ結果は source_hash の現物（artifacts/DB_OBSERVED_SNAPSHOT_litid_20260619.md）。

## 3. 観測要点（数字は実測）

**3-1. bib_records(10,326) に実在するソースは2つだけ**
- asai-bookshelf（自所）6,524：ISBN 82.7% / **ndl_bib_id 76.7%** / NDC 84.4% / edition 6.5%
- bencom-library（弁コム）3,802：ISBN 0.2% / NDL 0% / NDC 0%
- **LION BOLT・legallib は bib_records に行ゼロ＝未投入。** 計画が想定する3ルートのうち2つが未着。

**3-2. 自所の ISBN×NDL 実クロス（6,524）**
- ISBN有&NDL有 4,976（ISBN保有の92%が既に解決済み）/ ISBN有NDL無 421 / ISBN無NDL有 26 / **両方無 1,101**
- → 穴は (421 ISBN抽出余地) + (1,101 古書/奥付欠落の難所) に局在。

**3-3. 弁コム no-ISBN shadow は既存**＝`bookdx.holding_bencom_link`(1,737)
- 全件 title_norm+publisher_norm fingerprint。high(isbn_holding+fp) 962 / **medium(noisbn+fp) 775**。
- 775 は単証拠寄り＝DD-LITID-001「2独立証拠で confirm」の要対象。

**3-4. 媒体レイヤ `bookdx.holdings`(6,524)**：scanned=has_pdf 611、**cut=0 / has_toc=0（フラグ未投入）**。

**3-5. 文献(記事)層**：authority.publication(7,348) は論文/記事レイヤ。Mac の d1law/bunken 系は
D1-Law 文献メタ＝書籍4ルートと別ドメイン（DD-PERIODICAL寄り）。本件の書籍スコープ外と判断。

## 4. これがドライラン計画 v0.1 に与える前提修正（Claude の提案）

| 計画の前提 | 実測 | Claude 提案の修正 |
|---|---|---|
| ISBN持ち3ルートを当てる | 実在は self/own 1ルートのみ | **自所1ルート先行**（計画§8の懸念が現実化） |
| NDL解決をこれから測る | 自所はISBN保有の92%解決済み | 計測は既存DB値で即可能、焦点は穴(421+1,101) |
| bengo4 no-ISBN は今後別レーン | 既に1,737件存在 | shadow は増設でなく**既存775件の confirm精査**から |

## 5. 特に厳しく監査してほしい点（前提を疑え）

1. **「92%解決済み」の落とし穴**: ndl_bib_id が埋まっている=正しく版粒度で解けている、とは限らない。
   過去の解決が ISBN完全一致のみで、刷違い/重版を別bibidに割った/版違いを1bibidに潰した可能性は
   この被覆率からは見えない。**既存 ndl_bib_id の品質検証なしに「穴埋めだけ」へ縮約してよいか。**
2. **穴の局在(1,101)を過小評価していないか**: 両方無し1,101は自所の16.9%。古書/加除式/奥付欠落が
   ここに濃縮しているなら、件数は少なくても**版同定の難所そのもの**。先送りしてよいか。
3. **既存775件(medium)の扱い**: 単証拠で既に張られたリンクを「shadowで作るもの」と同列に精査するのか、
   それとも**既成事実として遡及検証**が要るのか。confirm 済みでない前提でよいか。
4. **legallib/LION BOLT 未着で先行する妥当性**: 自所先行で得た分布/閾値感を後合流ルートに
   そのまま当ててバイアスが出ないか（計画§9-4 の再確認）。
5. **観測の十分性**: この read-only 観測だけで「前提修正OK」と判断してよいか、本実装ゲート前に
   追加で測るべき指標（既存ndl_bib_idの版粒度QA、1,101の内訳推定 等）はないか。
6. **スコープ線引き**: 文献(記事)層を書籍4ルートから切る判断は正しいか、それとも同一基盤に乗せるべきか。

## 6. 期待する判定

`OBSERVATION_VALID`（観測妥当・前提修正可） / `VALID_WITH_NOTES` / `REMEASURE_REQUIRED`（測り直し要） / `HOLD`

## 7. 返答フォーマット

```text
status:
verdict_summary:
observation_validity:
- 読み方の妥当性:
- 見落とし/過大解釈:
adversarial_findings:
- 「92%解決済み」の品質:
- 穴(1,101)の過小評価:
- 既存775件medianの扱い:
- 後合流バイアス:
- スコープ線引き(文献切り出し):
premise_update_decision: (ドライラン計画 v0.1 の前提を更新してよいか)
must_fix:
should_fix:
additional_measurements_needed:
final_gate:
```

## 8. 監査上の注意

本件は read-only 観測の妥当性と前提修正の可否のみ。DDL/実装/backfill/本番突合/promote/serving/
外部公開は許可しない。

## 9. banto 自己申告

- 観測は SELECT のみ。DB は無変更。スナップショットは branch claude/book-identification-progress-7yjxpc
  にコミット済（e2f5a30）、PR #24 に反映。
- **未実施**: 既存 ndl_bib_id の版粒度QA（正しく解けているかの抜き取り検証）、1,101件の内訳推定、
  775件 medium の個別精査。いずれも次段（要承認/追加観測）。
- 既知の不確実: cut/has_toc フラグが0なのは「裁断/目次が無い」のか「別管理で未投入」なのか未確認。
