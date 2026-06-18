# WO: 雑誌号同定の ISSN seed 拡張（11誌 → 主要誌全体）実行計画 v0.1

```yaml
wo_id: WO-PERIODICAL-ISSN-SEED-EXPANSION-20260618
created_at: 2026-06-18 JST
author: Claude (claude.ai head / 浅井さん指示「NDL書誌をseedに昇格させて号同定を広げる」)
type: 既存延長（DD-PERIODICAL-001 v0.2 の P-6「ISSN seed表」を実体化する実行WO）
supabase_project: nixfjmwxmgugiiuqfuym
gate: READ_ONLY_STRICT + STAGING_ONLY（production apply / canonical promotion は本WO非対象・owner ratify待ち）
parent:
  - DD-PERIODICAL-001_periodical_identity_edges_v0.2-draft_20260611.md (Box 2279118801516)
  - 20260612_periodical_staging_landed_HANDOFF_to_codex.md (Box 2279264661263)
  - 20260615_DD-PERIODICAL-001_v0.2_GPTPRO_RESULT.md (Box 2285783042127)
  - 04_ALO_雑誌レイヤ技術仕様書_v0.1.docx (Box 2163612387610)
```

---

## 0. 目的（なぜこれをやるか）

雑誌オブジェクトの最大のボトルネックは「号(issue)を一意に固定する同定キー＝ISSN×巻号の作り込み不足」。
2026-06-18 実測で、号ID付与の現況は次のとおり:

- canonical(ISSN化済) **1,923号 / 11誌** ← 手動seed 11誌に依存
- 仮ID/未同定 **924号**（全2,847号の32%）

この924号を分解すると（実測・SELECT検証済み）:

| 区分 | 号数 | 誌数 | 扱い |
|---|--:|--:|---|
| **実在誌（ISSN seedで同定可能）** | **817** | **47** | ★本WOのseed対象 |
| 年版もの（書籍の誤分類） | 91 | — | DD P-7: periodical_issue でなく書籍/yearbookレーンへ。**ISSNを当てない** |
| 法律事務所ニュースレター | 14 | — | ISSN無しが通常。review / no-ISSN 確定 |

817号は上位に強く偏る（パレート）:

| 誌名(journal_norm) | 仮ID号数 | seed状態 |
|---|--:|---|
| jcaジャーナル | 216 | NO_seed |
| 税経通信 | 208 | NO_seed |
| ビジネス法務 | 66 | NO_seed |
| 戸籍 | 58 | NO_seed |
| 交通事故民事裁判例集 | 50 | NO_seed |
| 季刊刑事弁護 | 40 | NO_seed |
| 法律時報e-book | 36 | NO_seed |
| 労働判例 | 33 | NO_seed |
| 人事の地図 | 24 | NO_seed |
| 金融法務事情 | 15 | NO_seed |
| ビジネスガイド / 労働経済判例速報 | 各10 | NO_seed |

→ **上位 ~12誌の ISSN を seed するだけで、817号の約94%が canonical 化できる**見込み。
本WOは「全47誌を一度に」ではなく、**号数の多い実在誌から順に（パレート順）**seedを積む。

---

## 1. スコープと非スコープ

### やること（本WOの守備範囲）
- A. 対象誌リストの確定（read-only・本書で完了済み）
- B. ISSN authority seed 表の**スキーマ設計**と**叩き台データの作成**（staging領域 / Boxファイル）
- C. NDL書誌からの ISSN×誌名×巻号 抽出（**Mac worker 側**。NDL gz はローカルのみ）
- D. 拡張seedでの号ID再付与を **staging の新カラムに dry-run**（既存値は上書きしない）
- E. 被覆率リフトの計測レポート（journal/year別、誤同定サンプル監査）

### やらないこと（HOLD・owner ratify 判断待ち / 別gate）
- production schema への apply / DDL / migration
- jp: 仮ID → issn: canonical の**本固定**（staging dry-run までで止める）
- accepted edge 作成 / canonical promotion
- NDL書誌全件(240万)の DB 投入（本WOは対象誌の抽出のみ）
- 外部送信・再配布・有償DB本文の要約

---

## 2. データ破損ゼロの担保（CRITICAL）

1. **production は READ ONLY**。全SQLは `SET TRANSACTION READ ONLY;` を先頭に置く。
   既存テーブル(`biblio.*` / `authority.*` / `staging_periodical.issue_stage` 既存列)は **一切 UPDATE/DELETE しない**。
2. **既存 issue_id を上書きしない**。再付与結果は `issue_stage` に**新カラム `issue_id_v2` / `issue_id_status_v2`**（または別 staging テーブル `issue_stage_seedv2`）として**追記**し、旧 `issue_id` と**並置**して比較する。差分が出たら必ず両方残す。
3. **seed は append-only + provenance 必須**。各 ISSN 行に「根拠(NDL bib id / 公的ISSNレジストリ)・確定状態(confirmed/review/rejected)・誌名異表記・有効期間・改称前後」を持たせる。確定していないものは `review` 止まりで canonical 付与に使わない。
4. **promotion は二重ゲート**。`jp:` → `issn:` の本固定は (a) seed行が `confirmed` かつ (b) 巻号(通巻)連続性チェックPASS の**両方**を満たした号だけ。staging dry-run で両ゲートを可視化し、production 反映は **owner ratify + rollback bundle 作成後**に別WSで実施（本WO外）。
5. **冪等・再現性**。全成果物に SHA256、dataset_version / seed_version / parser_version を全行付与。Box `データ種別分離_20260611/_inventory`(388953248767) にミラー。

---

## 3. フェーズ計画（手戻り最小の順序）

> 順序の肝: **(P1) 非雑誌を先に外す → (P2) seed土台を作る → (P3) NDLで埋める → (P4) dry-runで効果測定 → (P5) owner判断**。
> 非雑誌(年版91/NL14)を先に分離するので、ISSNを当てに行く無駄打ち＝最大の手戻り要因をゼロにする。

### P1. 非雑誌の分離（read-only・staging印付け）　担当: ここ(codex) / 即可
- `issue_stage` の年版パターン91号・newsletter14号に **`lane_hint`（=yearbook / newsletter / journal）を新カラムで付与**（既存列は触らない）。
- yearbook 91 は DD P-7 の書籍/yearbookレーンへ回す候補として固定（本WOではseed対象から除外するだけ。移送は別WO）。
- 出力: `p1_lane_split.json`（journal/yearbook/newsletter の確定内訳）。

### P2. ISSN authority seed スキーマ＋叩き台　担当: ここ(codex)
- seed表設計（下記§4）。既存 confirmed 11誌＋本書の上位実在誌で**叩き台 seed**を作る。
- 公知ISSN（判時/判タ/ジュリスト/NBL/商事法務/金商 等は既confirmed）を起点に、上位誌の ISSN 候補を `review` で起票。
- 出力: `issn_seed_v2_draft.csv`（status=confirmed/review 混在）＋ Boxミラー。

### P3. NDL書誌での ISSN×誌名×巻号 抽出　担当: **Mac worker（NDL gz はローカル `~/ndl_work/` のみ）**
- 対象は §0 の上位実在誌（**全件投入ではなく対象誌のみ**）。NDLの ISSN / ISSN-L / 誌名異表記 / 巻号表記 / 改称履歴を抽出。
- P2叩き台の `review` 行を NDL根拠で `confirmed` に昇格、または不一致を `rejected`。
- 誌名正規化は **共有normalizer（DD P-5）**を使い、雑誌・書籍で同一ロジック（剥がしトークン: `【特集】/空括弧/No./通巻/年月号/版`）。
- 出力: `issn_seed_v2_ndl_evidence.jsonl`（各ISSNに ndl_bib_id 等の根拠）＋ SHA256。

### P4. 拡張seedで号ID再付与（staging dry-run・既存非破壊）　担当: ここ(codex) read-only計測 + worker生成
- 拡張seed適用後の号IDを **`issue_id_v2`** として算出（旧 `issue_id` と並置・上書き無し）。
- ゲート計測:
  - `gate_issn_seed_evidence`: 使用ISSNが全て seed.confirmed か（review/rejected を canonical に使っていない）
  - `gate_issue_no_continuity`: 同一ISSN内で通巻番号の連続性・重複が破綻していないか
  - 被覆率リフト: canonical 1,923 → ? / 仮ID 924 → ?（journal/year別）
  - 誤同定サンプル: v1→v2 で issue_id が変わった号を 50件 human/GPT監査
- 出力: `p4_coverage_lift_report.md` + `p4_changed_issues_sample.csv`。

### P5. owner ratify 判断（本WO外・別WSへ申し送り）
- P4の被覆率・誤同定サンプル・rollback bundle を添えて owner へ。
- ratify後にのみ: `jp:`→`issn:` 本固定、production apply、canonical promotion を**別WO**で実施。

---

## 4. ISSN authority seed 表（設計案）

GPT監査 P-6 の指示（seed source / review status / effective period / journal title variants を持たせる）に準拠。

| カラム | 型 | 必須 | 備考 |
|---|---|---|---|
| issn | text PK | ○ | ハイフン付き正規形（例 0448-0791） |
| issn_l | text | | ISSN-L（改称統合キー） |
| journal_norm | text | ○ | 正規化誌名（共有normalizer後） |
| title_variants | text[] | | 異表記・旧誌名・英題 |
| status | text | ○ | `confirmed` / `review` / `rejected` |
| evidence_source | text | ○ | `ndl` / `owner_manual` / `public_issn_registry` |
| ndl_bib_id | text | | NDL書誌ID（evidence_source=ndl 時） |
| valid_from / valid_to | date | | 改称・休刊の有効期間 |
| renamed_from / renamed_to | text | | 誌名改称の前後ISSN |
| seed_version | text | ○ | 既定 `issn_seed_v2_20260618` |
| note | text | | review理由・owner確認メモ |

**規律（DDの号ID方針と整合）**:
- `confirmed` 行の ISSN だけが `issn:{ISSN}#{通巻}` canonical 付与に使える。
- `review`/`rejected` は dry-run の候補表示までで、本固定不可。
- `jp:{journal_norm}#{issue_no}` は恒久URIでない旨を schema comment / view 名で明示（DD既定）。

---

## 5. 役割分担（環境制約の明示）

| 作業 | 実行者 | 理由 |
|---|---|---|
| read-only 計測 / staging新カラム dry-run設計 / 計画文書 | **codex（このセッション）** | Supabase read + Box書込が可能 |
| NDL gz パース（ISSN×誌名×巻号抽出） | **Mac worker** | NDL書誌はローカル `~/ndl_work/` のみ。リモートからは触れない |
| seed の confirmed 昇格の最終承認 / production ratify | **owner（浅井さん）** | canonical固定は owner判断（DDのHOLD境界） |

---

## 6. close 条件（満たさなければ未了）

- [ ] P1: 年版91 / NL14 / 実在誌817 の分離が `lane_hint` 新カラムで固定。既存列の変更0。
- [ ] P2: `issn_seed_v2_draft.csv` 生成（confirmed/review 区別あり）。Boxミラー + SHA256。
- [ ] P3(worker): 対象誌の NDL根拠付き ISSN seed が `confirmed` 昇格。根拠(ndl_bib_id)併記。
- [ ] P4: `issue_id_v2` を**並置追記**で算出（旧issue_id上書き0）。被覆率リフト・誤同定50件監査・2ゲートの結果をレポート。
- [ ] 全SQLが `SET TRANSACTION READ ONLY` 下、**production mutation 0件 / DDL 0件 / canonical mint 0件**をセッションログで証明。
- [ ] お目付け役監査レーンへ RESULT 1本で報告。

---

## 7. 想定リフト（仮説・P4で実測して確定）

- 上位~12誌 seed → 817号の約94%（≈768号）が canonical 化見込み。
- canonical 号: 1,923 → ≈2,690（68% → 約94%）。
- 残差: 年版91（書籍レーン）・NL14（ISSN無し）・希少誌のISSN未確定分。

> 数値は P4 dry-run で確定する。本節は着地目標であって結果ではない。
```

---
本ファイルは実行指示の計画書であり、production への投入指示ではない。
production apply / canonical promotion は §1 非スコープ・owner ratify 待ち（HOLD）。
