# lawdelta real-lane runbook（L3：実データで精度を測る）

精度プラン [`PLAN_lawobject_precision_v0.1`](../../docs/PLAN_lawobject_precision_v0.1.md) の **L3（real-lane 素材）**
を、demo fixture から**実 e-Gov 標準 XML** に進めるための手順。`scripts.lawdelta` を実法令で回し、
L1 ハーネス（`scripts.eval`）で delta_kind の precision/recall を測れる状態にする。

## 0. この環境の制約（重要）
- **e-Gov 法令 API は許可リスト外（HTTP 403）**。サンドボックスでは e-Gov を直接叩けない。
- 一方 **GitHub の clone は通る**。よって実 XML は GitHub ミラー経由で入手する。

## 1. 実 XML の入手元（サンドボックスで実証済み）
本ランブックの初回実行で使った 2 つの**実民法 XML**（いずれも e-Gov 標準 XML v3）:
| 役割 | 入手元 | 版 |
|---|---|---|
| OLD | `japanese-law-analysis/japanese_law_xml_schema` の `src/tests/129AC0000000089_20230614_505AC0000000053.xml` | 民法 2023-06-14 projection |
| NEW | `aluqas/gitlaw-jp` の `laws/129/129AC0000000089/current.xml`（`current.json.revision_id = 20251001_505AC0000000053`） | 民法 2025-10-01 施行 projection |

> どちらも `git clone` で取得（e-Gov 非経由）。**XML 本体（各 1.5MB）はリポジトリに入れない**（外部データ）。
> 本番/較正で版を増やすときは gitlaw-jp の git 履歴 or 別ミラー、ネットワーク許可環境では e-Gov API v2
> の時点取得を使う。

## 2. 実行（再現コマンド）
```sh
python -m scripts.lawdelta <OLD.xml> <NEW.xml> \
  --law-id 129AC0000000089 \
  --from-rev 129AC0000000089_20230614_505AC0000000053 \
  --to-rev   129AC0000000089_20251001_505AC0000000053 \
  --snapshot-id reallane_minpo_<date> \
  --out out/ --run-id reallane_minpo
```

## 3. 初回実行の結果（real-lane 検証 ✅）
- パース: 実民法 **1164 条**を抽出（`art:3-2` 等の枝番・削除 shell 19 件も正しく処理）。
- diff: **1167 行**（no_change 1146 / **substitution 14・insertion 4・repeal 2・join 1 = 21 条の実改正**）。
- **全 gate pass**（実データでも実質フィールド非混入・provenance 完備 等が成立）。
- ＝ producer が fixture でなく**実 e-Gov 標準 XML で動く**ことを実証。

## 4. gold への昇格（**公式データから機械生成**。人手目視ではない）
gold の正解 `delta_kind` は**改正法の「改め文」が公式に明記している**（「第七百三十三条を削る」＝repeal、
「第七百七十二条を次のように改める」＝substitution、「…の次に次の一条を加える」＝insertion）。
したがって gold は**権威ある公式データから機械生成**する。人手は最終スポット監査のみ（21 条を目視で
ラベル付けする作業ではない）。これは PLAN_DD-LAWSUBTRANS P3／本リポの `tests/gold/README.md` が
当初から定めた方針（**名大「改め文」16 パターン・公式新旧対照表を検証器に**）と同じ。

**gold ソース（優先順）**:
1. **e-Gov 法令 API v2 改正履歴/改め文**（`law_revisions` 等）＝機械可読の一次データ。
   ＊本サンドボックスは e-Gov が allowlist 外で HTTP 403。**取得には e-Gov の allowlist 追加が必要**
   （環境設定の問題であって、人手検証が要るわけではない）。
2. **改正法の標準 XML の改め文**を 改め文パーサ（名大16パターン）で解析 → (対象条, 操作) を抽出。
   ＊該当改正法（令和4年法律102号 親子法制 / 令和5年法律53号 IT化）は gitlaw-jp の本クローンには
   未収録（溶け込み済み現行法のみ保持）。要 e-Gov もしくは改正法を含むミラー。
3. **公式新旧対照表**（法務省/各府省が法案附属で公開, moj.go.jp 等）。表を機械パース。

**gold 生成 → 採点**（ソースが揃ったら）:
- 改め文/改正履歴から `tests/gold/lawdelta_minpo_20230614_20251001.gold.jsonl`（`delta_kind`＝公式由来）を
  自動生成（candidate ワークリストの `delta_kind` を埋める）。
  ```sh
  python -m scripts.eval --task lawdelta \
    --gold tests/gold/lawdelta_minpo_20230614_20251001.gold.jsonl \
    --pred out/law_textual_delta_reallane_minpo.jsonl \
    --key article_path --label delta_kind --out out/eval_reallane_minpo --min-f1 0.9
  ```
  → delta_kind 単位 P/R で lawdelta 閾値（`SUBST_MIN`/`RENUMBER_SIM`）を**数字で**較正（L1 達成）。

> **示唆**: 改め文が操作を断定している以上、**改め文パースは text-diff より上位の真実源**。lawdelta の
> text-diff は「改め文が取れない/溶け込み済みしか無い」場合の代替・補完と位置づけ、改め文が取れるなら
> そちらを gold かつ第一次抽出に使うのが筋（→ DD-LAWREF/接続軸の改め文レーンとして要検討）。

## 5. 留意（不確実点・honest）
- candidate の `delta_kind_pred` は **producer 予測であって正解ではない**。gold は §4 の公式データ由来で埋める。
- OLD/NEW は出所が異なる（テスト fixture vs gitlaw projection）。両者とも民法標準 XML だが、**projection 差**
  （施行時点の違い）を見ているので、単一改正法でなく**期間内の複数改正の合算**である点に注意。
  単一改正の純粋な P/R を測るなら、その改正の施行直前/直後の 2 版を揃える。
- OLD/NEW は出所が異なる（テスト fixture vs gitlaw projection）。両者とも民法標準 XML だが、**projection 差**
  （施行時点の違い）を見ているので、単一改正法でなく**期間内の複数改正の合算**である点に注意。
  単一改正の純粋な P/R を測るなら、その改正の施行直前/直後の 2 版を揃える。
