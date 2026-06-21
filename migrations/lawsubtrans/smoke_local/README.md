# smoke_local — DD-LAWSUBTRANS-001 ローカル構造スモークテスト

`bash run_smoke.sh` で使い捨てローカル Postgres を立て、001→005 + verify_dry_run +
わざと違反 + append-only/CHECK ガードを検査する。

## これが検証すること（土台不要・安価）
- 001..005 ＋ stub R-1 view が順序通りエラー無く apply される（SQL の構文/列名/依存の健全性）
- 16 gate view が全て queryable（無データで verify_dry_run.sql → ALL GATES EMPTY）
- 各 gate に検知力がある（仕込んだ違反を捕捉：substantive_requires_evidence /
  old_law_survival_three_axis / formal_status_consistent_with_lawtime / mirror_consistent）
- append-only トリガが UPDATE/DELETE で RAISE、`ck_subchg_claim` が evidence 無し claim_support を拒否

## これが検証しないこと（偽陽性ゾーン。`../README.md` 参照）
backfill / formal_status 整合 / lawtime_resolved 結合を **実データ**で検査することはできない。
これらは materialize 済みの法令レイヤ（alo_law_work / alo_statutes / alo_edges）＋
DD-LAWTIME v0.2.2/v0.2.3 を要する。**本物の dry-run は Supabase branch 上で**
（`../README.md` の手順）行うこと。`stub_lawlayer.sql` は構造検査用の最小スタブにすぎない。

## ファイル
- `stub_lawlayer.sql` — alo_law_work/alo_statutes/alo_edges の最小スタブ ＋ lawtime R-1 view
- `violations.sql` — 仕込み違反（gate 検知力の確認）
- `run_smoke.sh` — 使い捨て PG を立てて上記一式を実行（root の場合は postgres ユーザへ降格）
