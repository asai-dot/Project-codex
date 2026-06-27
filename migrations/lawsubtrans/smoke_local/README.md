# smoke_local — DD-LAWTIME + DD-LAWSUBTRANS ローカル構造スモークテスト

`bash run_smoke.sh` で使い捨てローカル Postgres を立て、**lawtime(001_base→patch)→lawsubtrans(001→005)**
を連結して apply し、両 verify_dry_run・わざと違反・append-only/CHECK ガードを検査する。

## これが検証すること（土台不要・安価）
- 全 DDL/patch/trigger/view が順序通りエラー無く apply される（構文・列名・依存の健全性）
- **P0-1 backfill** が legacy unknown edge を `temporal_status='unchecked'` に実際に書き換える
  （NOT VALID → backfill → 検収 gate 空 → VALIDATE の本番手順を再現）
- lawtime gate 群 ＋ lawsubtrans 16 gate が clean データで全て 0 件（queryable）
- 各 gate の検知力：仕込んだ違反（lawsubtrans 4 + lawtime P0-2/3/4 3）を該当 gate が捕捉
- 安全弁：append-only トリガ（lawsubtrans×2 + lawtime eval）が RAISE、
  `ck_subchg_claim`・`ck_law_ref_two_tier` が不正行を拒否

## これが検証しないこと（偽陽性ゾーン）
**実データ**での backfill / formal_status 整合 / lawtime_resolved 結合は、materialize 済みの
**本物の**法令レイヤを要する。さらに `migrations/lawtime/` の base は **再構成(candidate)** であり、
正本 v0.2.x との突き合わせ（監査）が前提。本番 dry-run は Supabase branch 上で別途
（`../README.md` / `../../lawtime/README.md`）。

## ファイル
- `seed_pre_patch.sql` — lawtime base の参照データ（work/statute/succession/eval）＋ backfill 対象の legacy unknown edge
- `violations.sql` — lawsubtrans gate 検知力の仕込み違反
- `lawtime_violations.sql` — lawtime patch gate（P0-2/3/4）の仕込み違反
- `run_smoke.sh` — 使い捨て PG を立てて上記一式を連結実行（root の場合は postgres ユーザへ降格）
