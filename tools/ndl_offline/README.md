# tools/ndl_offline — NDL オフライン照合パイプライン（R1/R2/R3）

DD-LITID FORWARD_ROADMAP v0.3 の WS-R を、ローカル実行できるスクリプトにしたもの。
上流（クラウド側 Claude）が機械処理を front-load 済み。ローカル実行者は `RUNBOOK_local.md` の
4ステップだけ行う。

## 監査ガード（v0.3 で CONDITIONAL GO の条件）
- source（ダンプ原本）を変更しない（read-only オープンのみ）。
- 出力は `out/` の **再生成可能な isolated artifact** のみ。**DB / canonical / Box source に書かない**。
- `R2_build_manifest.json` と `R2_rejects.tsv` を必ず生成（lineage: source_file/row/snapshot/parser/build_id）。
- `external_egress = prohibited`：索引・原本を外部へ出さない（R1 rights manifest の owner 決定に従う）。
- 索引一致は **candidate**。版の正誤は別途 adjudication（Q1, 独立2証拠）。confirmed/verified ではない。

## ファイル
| file | 役割 |
|---|---|
| `isbn_util.py` | ISBN10/13 → 13 正規化（共通） |
| `r1_probe.py` | inventory / sha256 / encoding・区切り・列の自動判定 |
| `r2_build_index.py` | 全CSVストリーム → `out/ndl_isbn_index.tsv` ＋ manifest ＋ rejects |
| `r3_coverage.py` | cohort-A ISBN を索引照合 → 被覆/候補/freshness |
| `run_all.sh` | R1→(目視)→R2→R3 オーケストレータ |
| `selftest.py` | 偽ダンプで通し検証（本番前の緑確認） |
| `input/cohortA_isbn.tsv` | 事務所蔵書 ISBN保有 5,397（DB由来・read-only 同梱） |
| `input/cohortA_noisbn.tsv` | 同 ISBN無 1,127（no-ISBN レーン設計用） |
| `out/` | 生成物（gitignore。ローカル保管・外部egress禁止） |

## 入出力の流れ
```
ダンプ(Box Drive, ~16.7GB)  ─r1→ schema/inventory
                            ─r2→ out/ndl_isbn_index.tsv (+manifest,+rejects)
input/cohortA_isbn.tsv ──────r3→ out/R3_coverage_report.md, out/cohortA_isbn_candidates.tsv
```

## まだやらないこと（HOLD）
A1 閾値 freeze / 既存 ndl_bib_id の verified 昇格 / 索引の hub・canonical 利用 /
DB write・backfill・promote・serving・外部公開。これらは別 gate（監査要）。
