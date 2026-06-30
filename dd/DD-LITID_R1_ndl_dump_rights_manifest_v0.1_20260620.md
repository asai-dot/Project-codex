# DD-LITID R1 — NDL ダンプ rights/egress manifest ＋ freshness lane v0.1

- 作成日: 2026-06-20
- 位置づけ: FORWARD_ROADMAP v0.3 WS-R R1（rights/access/egress 記録）＋ residual_gap #6（freshness lane）。
- 監査根拠: v0.3 RESULT must_fix #2 / residual_gaps #3,#6。R2(CONDITIONAL GO) 着手の**前提記録**。
- read-only 設計。本 manifest の owner 欄が埋まるまで R2 全量索引ビルドは開始しない。

## 1. 対象データ（Box 観測 20260620）

| 項目 | 値 |
|---|---|
| 格納 | Box `…/ALO共有フォルダ/ALOナレッジデータベース関連フォルダ（外部共有）/…/NDL_書誌情報_raw` |
| 本体 | `ndl_all_records_001〜161.csv`（各約105MB、最終 045MB）≈ **16.7GB** |
| 付随 | `ndl_law_isbn.txt`（116MB）、`NDC320〜329` クラス別フォルダ |
| folder_id | 368936853333 |

## 2. rights/egress manifest（**owner が値を確定**）

```yaml
source_acquisition_basis:        # 取得経緯（例: NDL一括ダウンロード/購入/提供）  TODO(owner)
terms_or_access_basis_reference: # 利用規約/契約の参照                          TODO(owner)
internal_use_class:              # internal_only | restricted | open            TODO(owner)
storage_location:                # 派生索引の保管先（例: Mac local trusted）     TODO(owner)
allowed_processors:              # 処理してよい主体/環境                          TODO(owner)
external_egress: prohibited      # prohibited | conditional | allowed  ★既定=prohibited
derived_artifact_retention:      # 索引の保持/再生成方針                          TODO(owner)
cleanup_or_rebuild_policy:       # 破棄・再ビルド方針                            TODO(owner)
owner_decision_at:               # 決定日                                       TODO(owner)
owner_decision_by:               # 決定者                                       TODO(owner)
```

**既定ガード（owner が上書きするまで有効）**
- `external_egress = prohibited`：ダンプ原本・派生索引を外部（クラウドLLM/外部env/公開）へ出さない。
- 処理は **Mac local trusted のみ**。出力は local isolated artifact。Box source / DB / accepted_identity_state を変更しない。

## 3. freshness lane（residual_gap #6）

ダンプは或る snapshot 時点の写し。**snapshot 以降の新刊はダンプに無い**＝照合失敗でなく「鮮度抜け」。

- `dump_snapshot_year`（= R1 で確定。CSV 内 or ファイル日付から推定）を基準に:
  - `pub_year >= dump_snapshot_year` の no-hit → **`freshness_miss`** レーン（matching failure に混ぜない）。
  - 実測: cohort-A の ISBN有NDL無 421 のうち **53件が 2024+**＝最有力の freshness_miss 候補。
- freshness_miss の扱い: ライブNDL API 補完 or 新しい snapshot 取得要求（別 gate）。**no_hit_after_valid_isbn の真の NDL欠落とは別集計**。

## 4. R2 着手の必要条件（再掲・全充足で CONDITIONAL GO）
1. 本 manifest の owner 欄確定（特に internal_use_class / external_egress / storage_location）。
2. Mac/local trusted 第一選択、外部 data env へ搬出しない。
3. source manifest/hash/parser version/build manifest を保持。
4. canonical/DB に write せず、再生成可能な isolated artifact に限定。
5. reject/error/duplicate report を同時生成。
6. source file を変更しない。

→ 機械処理（R1 probe / R2 build / R3 coverage）は `tools/ndl_offline/` のスクリプトで実施（RUNBOOK_local 参照）。
