# journal 段2 識別子外部照合レポート (ORCH-JOURNAL-ISSN-RESOLVE / channel=jissn)

- 種別: read-only 外部照合→提案のみ。canonical/DB反映は owner GO(本成果物では書かない)。
- 照合経路: producer NDL SRU (dcndl / `isPartOf` の `iss.ndl.go.jp/issn/*` 抽出) を再利用(`tools/periodical/journal_issn_resolve.py`)。exact main-title + 出版者(責任表示)一致の serial のみ採用。ISSN 捏造ゼロ(NDL由来のみ)。head の手組み broad-match は不採用。
- dup-ISSN ガード: 提案候補 ISSN を authority `d1_journal_issn_authority_ALL_resolved_v14.csv`(全 issn key_value=379件) と照合。別誌割当済は COLLISION として提案除外。
- ISSN_NOT_EXIST は exact-title 記事レコード≥2 の確証がある場合のみ(1件以下は AMBIGUOUS で head へ=精度優先)。
- 対象24誌 = held 10(journal_authority_stage2_proposal_v0.1.csv / v14 unresolved) + NCID→ISSN 昇格候補 14(seed_ncid_fallback)。
- 注意: `ndl_hits_total`/`exact_title_records` は NDL SRU の live 応答で毎回わずかに変動しうる(verdict/ISSN 判定には影響しない)。

## verdict 内訳 (24誌)
- ISSN_RESOLVED: 1
- ISSN_NOT_EXIST: 10
- COLLISION: 2
- AMBIGUOUS: 11

## ISSN_RESOLVED (1)
- **税理** → ISSN `0514-2512` (NDL出版者: ぎょうせい 編 ; 日本税理士会連合会 監修)
  - evidence: NDL isPartOf issn/05142512 evidence=71 bib=4486887 pubName『税理 : 税理士と関与先のための総合誌 / ぎょうせい 編 ; 日本税理士会連合会 監修』[1996-2025]

## COLLISION (2) — dup-ISSN ガード発火・提案せず(NCID/held維持)
- **月刊債権管理** ✗ 衝突先: 季刊事業再生と債権管理(seed_verified)
  - v3候補 ISSN 1348-8953 は authority で別誌『季刊事業再生と債権管理(seed_verified)』に割当済(誤マージ)。NDL exact-title hits=0(独自ISSN無)。提案せず・NCID/held維持
- **判例評論** ✗ 衝突先: 判例時報(seed_verified)
  - NDL isPartOf issn/04385888 evidence=1 bib= pubName『判例評論』[2018-2018] ／ dup-ISSN: 0438-5888 は別誌『判例時報(seed_verified)』に割当済→提案せず

## AMBIGUOUS (11) — head/owner 判断へ(推測ISSN不採用)
- **TKC税研時報** (現keep: held): NDL exact main-title 一致=0・独自ISSN根拠不足(hits=2)→実在/ISSN確定できず head/owner へ
- **建築関係法令の研究** (現keep: held): NDL exact main-title 一致=1・独自ISSN根拠不足(hits=44)→実在/ISSN確定できず head/owner へ
- **立命館大学法学部ニューズレター** (現keep: held): NDL exact main-title 一致=1・独自ISSN根拠不足(hits=130)→実在/ISSN確定できず head/owner へ
- **保安と外勤** (現keep: held): NDL exact main-title 一致=0・独自ISSN根拠不足(hits=10)→実在/ISSN確定できず head/owner へ
- **永世中立** (現keep: held): NDL exact main-title 一致=0・独自ISSN根拠不足(hits=347)→実在/ISSN確定できず head/owner へ
- **東洋法学会会報** (現keep: held): NDL exact main-title 一致=0・独自ISSN根拠不足(hits=0)→実在/ISSN確定できず head/owner へ
- **軍事民論** (現keep: AN00020468): NDL exact main-title 一致=0・独自ISSN根拠不足(hits=82)→実在/ISSN確定できず head/owner へ
- **登記インターネット** (現keep: AA11407650): NDL exact main-title 一致=0・独自ISSN根拠不足(hits=82)→実在/ISSN確定できず head/owner へ
- **月刊登記先例解説集** (現keep: AN00328066): NDL exact main-title 一致=0・独自ISSN根拠不足(hits=34)→実在/ISSN確定できず head/owner へ
- **研修** (現keep: AN00327540): NDL exact main-title 一致=0・独自ISSN根拠不足(hits=384)→実在/ISSN確定できず head/owner へ
- **週刊法律新聞** (現keep: AN10042106): NDL exact main-title 一致=0・独自ISSN根拠不足(hits=44)→実在/ISSN確定できず head/owner へ

## ISSN_NOT_EXIST (10) — serial実在/独自ISSN未付与・NCID維持
- **明治大学法科大学院ジェンダー法センター年報** (NCID維持: —(held)): NDL exact-title records=20(hits=54)だが isPartOf ISSN 無し→serial実在・独自ISSN未付与。NCID/held維持
- **訟務月報** (NCID維持: —(held)): NDL exact-title records=2(hits=392)だが isPartOf ISSN 無し→serial実在・独自ISSN未付与。NCID/held維持
- **労働法律旬報** (NCID維持: AN00327813): NDL exact-title records=193(hits=388)だが isPartOf ISSN 無し→serial実在・独自ISSN未付与。NCID AN00327813 維持
- **法曹** (NCID維持: AN00327187): NDL exact-title records=27(hits=390)だが isPartOf ISSN 無し→serial実在・独自ISSN未付与。NCID AN00327187 維持
- **速報判例解説** (NCID維持: AA12241495): NDL exact-title records=8(hits=388)だが isPartOf ISSN 無し→serial実在・独自ISSN未付与。NCID AA12241495 維持
- **地方税** (NCID維持: AN00126094): NDL exact-title records=48(hits=393)だが isPartOf ISSN 無し→serial実在・独自ISSN未付与。NCID AN00126094 維持
- **民事月報** (NCID維持: AN00327733): NDL exact-title records=195(hits=390)だが isPartOf ISSN 無し→serial実在・独自ISSN未付与。NCID AN00327733 維持
- **労働法令通信** (NCID維持: AN00327799): NDL exact-title records=198(hits=400)だが isPartOf ISSN 無し→serial実在・独自ISSN未付与。NCID AN00327799 維持
- **判例セレクト** (NCID維持: AA1115468X): NDL exact-title records=3(hits=388)だが isPartOf ISSN 無し→serial実在・独自ISSN未付与。NCID AA1115468X 維持
- **警察時報** (NCID維持: AN00327438): NDL exact-title records=23(hits=396)だが isPartOf ISSN 無し→serial実在・独自ISSN未付与。NCID AN00327438 維持

## 受入基準セルフチェック
- 24誌すべてに verdict: 24/24 OK
- ISSN_RESOLVED は evidence(NDL record id/bib) 必須: OK
- dup-ISSN ガード全件通過(COLLISION を提案に混ぜない): OK
- 提案ISSN が authority 別誌と衝突しない: OK
- exact title 一致でない候補は本採用しない(推測ISSN=0): OK
