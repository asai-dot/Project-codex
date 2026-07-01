# journal authority 段1 誌名正規化 report v0.1 — read-only / dry-run

- orch_id: ORCH-JOURNAL-AUTHORITY-FIX-20260701 / channel: journal
- 種別: **read-only / dry-run**。authority本体・canonical・DB反映・外部publishは本発注の対象外(段2=owner GO)。
- 入力(read-only): 修正候補 `journal_authority_corrections_v0.1.csv`(370件, worktree-casename-dict 85a7bd2) /
  journal authority `d1_journal_issn_authority_ALL_resolved_v14.csv`(931行)
- 成果物(本ブランチ, P##系不使用): `journal_authority_norm_preview_v0.1.csv`(370行 verdict付き) + 本report

## 1. verdict 内訳(全370件・欠けなし)

- 総数 **370** / blank verdict **0**(全候補にverdict付与)

| issue | 件数 | verdict内訳 |
|---|---|---|
| CITATION_FRAGMENT | 169 | NORMALIZE 162 / MERGE_TO_EXISTING 7 / NEEDS_DECISION 0 |
| TRUNCATED_PAREN | 179 | NORMALIZE 179(号数欠落 174 + 内容欠落 5) |
| DUP_ISSN | 22 | TRUE_SAME 20 / MISASSIGN 1 / NEEDS_DECISION 1 |

- 全体: NORMALIZE 341 / TRUE_SAME 20 / MERGE_TO_EXISTING 7 / MISASSIGN 1 / NEEDS_DECISION 1

## 2. MERGE_TO_EXISTING(統合先は全て authority に実在)

CITATION_FRAGMENT のうち **7件**。掲載位置サフィックス(創刊号/別冊付録/増刊 + ,p)を除去した core 名が
既存 journal_canonical に**厳密一致**した候補のみ MERGE。架空の統合先は生成していない(実在チェック=0違反)。

| 元候補 | 統合先(実在) |
|---|---|
| 法学セミナー別冊付録,p | 法学セミナー |
| 法学セミナー増刊,p | 法学セミナー |
| 比較憲法学研究創刊号,p | 比較憲法学研究 |
| 白鴎大学大学院法学研究年報創刊号,p | 白鴎大学大学院法学研究年報 |
| 志学館法学創刊号,p | 志学館法学 |
| 白鴎法学創刊号,p | 白鴎法学 |
| 松山法学創刊号,p | 松山法学 |

> 注: 本段では preview のみ。実際の統合(authority書換)は段2 owner GO。

## 3. 破壊的統合ゼロの確認

- **TRUNCATED_PAREN 179件は全て verdict=NORMALIZE**(破壊的統合=0件)。
  非NORMALIZE(=統合)件数: **0件**(要件どおりゼロ)。
- 正規化は「末尾の未閉じ括弧を閉じる名補完のみ」。別誌への統合・authority行の削除/併合は一切行わない。
- CITATION_FRAGMENT の MERGE_TO_EXISTING は authority 実在誌への表記寄せ提案(preview)であり、
  段1では authority に書かない(dry-run)。破壊的操作なし。

## 4. high-risk 一覧(head へ戻す)

### 4a. DUP_ISSN — 別誌誤付与疑い(MISASSIGN)
- `判例タイムズ | 民事法研究` — ISSN 0438-5896=['判例タイムズ', '民事法研究']。判例タイムズ(seed_verified,ac10778)に別誌'民事法研究'(ac367)が同ISSN付与=別誌誤付与疑い。段2でISSN分離要(read-only)

### 4b. DUP_ISSN — 判定保留(NEEDS_DECISION)
- `女性と法(法学セミナー増刊 総合特集シリーズ | 憲法訴訟(法学セミナー増刊)』所収p | 法学ガイド | 法学セミナー | 法学セミナー別冊付録,p | 法学セミナー増刊,p` — ISSN 0439-3295: 法学セミナー family(別冊付録/増刊/女性と法/憲法訴訟)は同一誌異表記=TRUE_SAME相当だが'法学ガイド'(ac81)は別誌の可能性。head判断要

### 4c. TRUNCATED_PAREN — 号数/年度が号数以外の内容欠落(missing_content, 目視要)
5件。括弧内が号数でなく年度/周年の断片で切れており、括弧補完のみでは内容不明。
- `下級審商事判例評釈(昭和` → `下級審商事判例評釈(昭和)`
- `下級審商事判例評釈(平成` → `下級審商事判例評釈(平成)`
- `下級審商事判例評釈(平成元年-` → `下級審商事判例評釈(平成元年-)`
- `法と政治の現代的課題(大阪大学法学部創立` → `法と政治の現代的課題(大阪大学法学部創立)`
- `法学と政治学の現代的展開(岡山大学創立` → `法学と政治学の現代的展開(岡山大学創立)`

### 4d. DUP_ISSN — TRUE_SAME だが要確認(低優先・段2で表記寄せ時に目視)
同一ISSN・authority確認済だが表記差が大きい/別会名で、段2の表記寄せ時に念のため確認したい候補:
- `神奈川法学 | 神奈川法学(学生論文集)` — ISSN 0453-185X=['神奈川法学', '神奈川法学(学生論文集)']。異表記/略称/別冊/創刊号/大学改称による同一誌の複数表記(増刊含む)=同一誌。破壊的統合はせず段2で表記寄せ(read-only)
- `日本国際経済法学会年報 | 経済法学会年報` — ISSN 1342-1301=['日本国際経済法学会年報', '経済法学会年報']。異表記/略称/別冊/創刊号/大学改称による同一誌の複数表記(増刊含む)=同一誌。破壊的統合はせず段2で表記寄せ(read-only)
- `秋田法学(ノースアジア大学) | 秋田法学(秋田経済法科大学)` — ISSN 0286-2859=['秋田法学(ノースアジア大学)', '秋田法学(秋田経済法科大学)']。異表記/略称/別冊/創刊号/大学改称による同一誌の複数表記(増刊含む)=同一誌。破壊的統合はせず段2で表記寄せ(read-only)
- `桐蔭法学(桐蔭学園横浜大学) | 桐蔭法学(桐蔭横浜大学)` — ISSN 1341-3791=['桐蔭法学(桐蔭横浜大学)', '桐蔭法学(桐蔭学園横浜大学)']。異表記/略称/別冊/創刊号/大学改称による同一誌の複数表記(増刊含む)=同一誌。破壊的統合はせず段2で表記寄せ(read-only)

### 4e. TRUNCATED_PAREN — 号数欠落フラグ(missing_issue_number, 段2で号数補完)
174件。百選/演習等シリーズ名の末尾(号数)切れ。誌join自体は有効、号数は段2(CiNii/NDL照合)で補完。
(件数多につき個別列挙は preview CSV の missing_flag=missing_issue_number を参照)

## 5. 安全・スコープ確認

- 段1は **read-only / dry-run**。authority本体/canonical/DB反映/外部publish は本発注の対象外(段2=owner GO / HOS-003)。
- 識別子補完(CiNii/NDL照合)は段2。本発注では未実施。
- 判定に迷う候補は NEEDS_DECISION にして本reportの high-risk に計上(silent流し=なし)。
- 参照 standing: HOS-001(force push禁止) / HOS-002(external_share false) / HOS-003(canonical/DB/公開はowner GO)。
