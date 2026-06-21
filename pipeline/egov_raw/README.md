# pipeline/egov_raw — e-Gov 条文各号の raw 取得置き場（L0 observation）

§5「記載事項の床」の **top-down 正準リスト＝条文各号** を e-Gov から read-only 取得した生データと、
そこから抽出した **law/article/item anchor**（`requirement_floor --canonical` の入力源）を置く。

## これは何
- `scripts/egov_fetch.py` の出力先。**read-only / GET のみ / L0 observation**。
- procedure への紐付け・floor accepted化・DB write は **HOLD**（owner ratify を経る別工程）。

## 取得のしかた（**outbound 許可の環境**で実行）
このリポの web セッションは network policy で e-Gov が 403（未開放）。**owner の Mac か、許可レーンの
環境**で以下を回す。`laws.e-gov.go.jp`（JSON 包みなら `elaws.e-gov.go.jp`）を許可すれば足りる。

```bash
# 一括（_targets.json の対象すべて）
python scripts/egov_fetch.py --targets pipeline/egov_raw/_targets.json \
    --raw-dir pipeline/egov_raw --out pipeline/egov_raw

# 単発（例: 会社法199条1項各号）
python scripts/egov_fetch.py --law-id 405AC0000000086 --article 199 --paragraph 1 \
    --raw-dir pipeline/egov_raw --out pipeline/egov_raw/kaishaho_199_1.anchors.json
```

落ちるもの: `{law_id}.xml`（raw）＋ `*.anchors.json`（各号 anchor）。**コミットして持ち帰る**と、
web セッション側で後続（床突合・coverage）を進められる。

## 対象の足し方
`_targets.json` の `targets` に `{law_id, article, paragraph, out}` を足す。law_id は e-Gov 法令ID。
