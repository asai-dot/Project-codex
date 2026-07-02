# authority_wiring_regression_report — 20260702

- orch_id: ORCH-AUTHORITY-WIRING-20260702 / channel: wiring
- 実行者: producer（build_authority_v15.py 所有・L4-COVERAGE-LIFT 担当）
- 種別: 既昇格分の durability fold ＋ consumer 配線 ＋ read-only 回帰測定。**新規 canonical / DB / 外部公開なし。**
- 発注書: `classify-full:artifacts/periodical/ORCH-AUTHORITY-WIRING_order_20260702.md`

---

## 結論（受入基準に対する判定）

| 受入基準 | 結果 |
|---|---|
| build_authority_v15.py 再実行 = reconciled v15(924行) に一致 | ✅ **byte-identical**（md5 一致） |
| consumer 2本が新authority参照でエラーなく完走 | ✅ join(v15)=80.85% 完走 / L5(新hanrei)完走 |
| L5 court_miss は改善のみ（悪化ゼロ） | ✅ **date_only_court_miss 1242→1241（−1）, 悪化 0** |

> ⚠️ 1点だけ head の確認を要する差分あり（article join の被覆 −2,989）。**これは head 確定の
> reconciled v15 が内包する性質**（NORMALIZE 341 の「統合せず」de-list）であって producer が
> 持ち込んだ悪化ではない。詳細は §3・§NEEDS_DECISION。L5 court_miss ゲートは満たすため配線は完了。

---

## 1. durability fold（build_authority_v15.py）

reconciled v15 は「一回性ファイル」だったため、head 段1/段2 の確定分を build に取り込み、
**再実行で reconciled v15 を機械的に再生**できるようにした。入力 changelog を l4cov に vendor し
（`artifacts/periodical/journal_apply_changelog_20260701.csv`, casename bd28b62 由来）決定論適用:

- **NORMALIZE 341** — journal_canonical サフィックス除去（所収p / 研究叢書 等）。名補完のみ・行数不変の in-place rename。
- **MERGE_TO_EXISTING 7** — 創刊号,p / 別冊付録,p / 増刊,p の 7 行を本誌へ統合（source 除去 + target の article_count 加算 + note へ `merged<-…` 追記）。source-removed[i] と target-updated[i] は changelog 出現順で対応（ac 差分一致を実測確認）。
- **ISSN_RESOLVED 1** — 税理 の key を `ncid AN00080095` → `issn 0514-2512`（NDL SRU 確定）。

producer UPDATES（8 NCID 解決＋判例研究/駒沢法学論集 status 是正）と head changelog は、
MERGE で除去される 2 行（法学セミナー別冊付録,p / 増刊,p）を除き非重複。順序非依存で reconciled と一致。

**再実行ログ:**
```
[done] UPDATES=12 NORMALIZE=341 MERGE=7 ISSN=1 -> d1_journal_issn_authority_ALL_resolved_v15.csv (924 rows)
```
**検証:** 生成 v15 と reconciled v15（casename bd28b62）を `diff` → 差分ゼロ / md5 一致
`b59e3c06d3f298a73bd40502b5793888`。行数 931(v14) − 7(MERGE) = 924。

---

## 2. consumer 配線

| consumer | 変更 | 場所 |
|---|---|---|
| `tools/periodical/run_article_join_dryrun.py` | 既定 authority `v14 → v15` | l4cov（本コミット）＋ magazine（PR で同期） |
| `artifacts/periodical/l5_feasibility_build.py` | hanrei 入力を `20260605.csv`+`backfill6yr_20260617.csv` → `判例_identity_keys_dedup_canonical_20260702.csv` | magazine（PR） |

補足: magazine の `run_article_join_dryrun.py` は L4-COVERAGE-LIFT 改良（SPLIT_MAP / isbn per-issue
フォールバック）を欠く旧版。単なる参照差し替えではなく **l4cov 最新版（v15 参照込み）を同期**する
（本測定はすべて l4cov 最新版で実施）。classify-full が magazine を稼働中のため **直接 push せず PR**。

---

## 3. 回帰・payoff 測定（read-only）

### 3a. article join（labeled_v0.2.1 全 358,258 記事、l4cov 最新 join ツール）

| | joined | orphan | coverage |
|---|---|---|---|
| v14 authority(931) | 292,643 | 65,615 | 81.68% |
| v15 authority(924) | 289,654 | 68,604 | **80.85%** |
| Δ | **−2,989** | +2,989(全 `authority_unresolved`) | −0.83pt |

**per-journal 分解（rename 追従済）:**

- **GAINED +962（真の定期刊行物 join・8 NCID payoff）**
  月刊債権管理 +682 / TKC税研時報 +103 / 建築関係法令の研究 +44 / 立命館大学法学部ニューズレター +37 /
  保安と外勤 +30 / 法学論集(駒沢大学) +28 / 明治大学…ジェンダー法センター年報 +21 / 訟務月報 +14 / 軍事民論 +3
- **LOST −3,951**
  - 判例研究 **−570**：UPDATES で `seed_isbn_per_issue → collision_split`（機関混在の誤マージ回避＝**設計上の orphan受容**）。
  - **−3,381**：NORMALIZE 341 の対象＝記念論集 / 学会年報 / 研修叢書 / 弁護士専門研修講座 / 増刊総合特集 /
    別冊法学教室 基本判例シリーズ 等の**被引用 venue（単著書名等）**。changelog reason が明記する通り
    **「名補完(統合せず)」** の対象。v14 では isbn_per_issue の擬似 join になっていたものが v15 で de-list。
- 税理は **join 数不変（5,763 joined 両版）**。issue_id 接頭辞のみ `ncid:AN00080095 → issn:0514-2512`。

→ 差引 +962 − 3,951 = −2,989。**8 NCID の実 payoff（+962）は確保**。減少の主因は head 自身の
NORMALIZE de-list（−3,381、設計意図）＋設計上の collision_split（−570）で、**producer 起因の
精度劣化・誤マージは無し**。

### 3b. L5 court_miss（判例修正 payoff / 判例評釈 35,785 件）

同一 PILOT（classify-full 現行 pilot の read-only スナップショット）＋ 同一 JOIN（v15）で、
hanrei index のみ **旧 2 ファイル vs 新 dedup_canonical** に振り替えて比較。

| metric | OLD(2files) | NEW(canonical) | Δ |
|---|---|---|---|
| breakdown.matched_unique | 6,193 | 6,194 | **+1** |
| breakdown.matched_multi | 13,757 | 13,757 | 0 |
| **breakdown.date_only_court_miss** | **1,242** | **1,241** | **−1（改善）** |
| breakdown.no_match | 5,447 | 5,447 | 0 |
| breakdown.no_extract | 9,146 | 9,146 | 0 |
| hanrei_index_rows | 212,602 | 211,988 | −614（dedup） |

**per-article 遷移:** `date_only_court_miss → matched_unique` が **1 件のみ**、**悪化（matched→miss）= 0**。
改善記事＝`isbn:bj-200#p72`（八女簡・2000-10-12 → 判例ID 28070088）＝court化け復元による接合。
dedup で index 行が 614 減っても court_miss は悪化せず（正規化が court_key 化けを是正）。

> 発注書の想定「court化け15復元」に対し、判例評釈タイトル側の court_miss に実際に効くのは 1 件。
> 残りの復元は hyoshaku の (court,date) と交差しない（大半が matched_multi 側 or 非交差）ため court_miss に
> は現れない。**いずれにせよ悪化ゼロで gate 充足。**

---

## NEEDS_DECISION（head へ・非ブロッキング）

**article join 被覆 −3,381（NORMALIZE de-list 分）の扱い確認。**
changelog reason は当該 venue を「名補完(統合せず)」と明記しており、v15 で join 対象外になるのは
**設計意図と整合**（記念論集・学会年報等の単著書籍は定期刊行物 join の対象外＝precision 向上）。
ただし raw coverage 上は −0.83pt の movement。head の確認事項:

1. この de-list を意図通り受容する（推奨。記念論集等は periodical ではない）→ 本配線をそのまま採用。
2. 被引用 venue も接合したい場合は **article 側にも同じサフィックス正規化**を入れる別発注が必要
   （authority だけ正規化し article 側を未正規化にしたことが −3,381 の機序）。

producer 判断: **1 を推奨**。durability fold と L5 gate は独立に成立しており本配線は完了扱い。

---

## 継続性（RESULT）

- **read_log_commit**: `casename-dict bd28b62`（reconciled v15 ＋ journal_apply_changelog_20260701.csv の取得元）。v14 は casename/l4cov 共通 md5 `fdc23effaa33f59b8436d4ba72c24ce5`。
- **read_digest_id**: reconciled v15 md5 `b59e3c06d3f298a73bd40502b5793888`（生成 v15 と一致）。changelog: object=journal / NORMALIZE 341・MERGE 7(src)+7(tgt)・ISSN_RESOLVED 1。
- **read_standing_ids**:
  - authority v14 = `d1_journal_issn_authority_ALL_resolved_v14.csv`（931行, md5 fdc23eff…）
  - hanrei 旧 = `判例_identity_keys_20260605.csv`(178,318) + `…_backfill6yr_20260617.csv`(34,284)
  - hanrei 新 = `判例_identity_keys_dedup_canonical_20260702.csv`(211,988)
  - labeled = `…/labeled_v0.2.1/article_meta_labeled.jsonl`（358,258 記事）
  - L5 PILOT = classify-full 現行 `article_type_local_pilot_v0.1.csv` の read-only スナップショット（判例評釈 35,788）

## 安全確認

- 判例元2ファイル・v14・reconciled v15 は不変（read-only）。新規 canonical / DB / 外部公開なし。
- classify-full worktree は一切変更せず（read-only 参照のみ。reset/checkout/clean 不使用、wake/watch 不使用）。
- 全測定は read-only 再実行。DB/Box/edge 書込なし。
