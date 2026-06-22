# WO-PERIODICAL-JOURNAL-REGISTRY v0.1（誌マスタ + 決定的リゾルバ + 常設監査）

```yaml
wo: WO-PERIODICAL-JOURNAL-REGISTRY
version: 0.1
generated_at: 2026-06-22 JST
depends_on: [P5_id_decisions, P7_resolution_gate_correction, P9_backfill_result, P10_precision_audit]
status: design（read-only artifact / DDL適用は owner GO後）
intent: 解決ロジックをCSV/artifactからDBへ移し、新規データを自動canonical化。二重キー誤スプリットを根絶し、ドリフトを常設監査で自動検知。
scope: A(誌マスタ+リゾルバ) + B(標準監査ビュー)
```

## 0. 背景（なぜ今これか）
現状 issue_id は**バッチbackfillで一回ずつ手当て**。キー優先順(P5)・通巻式・年月↔通巻クロスウォークは
すべて CSV/artifact 内にあり、DBには無い。よって新規号/新ソースが入ると `issue_stage` は provisional に逆戻りし、
毎回手作業。さらに NCID採番誌は将来ISSNが露出すると `ncid:` と `issn:` が別idに割れる（潜在誤スプリット）。
→ **誌マスタにキーと規則を集約し、リゾルバviewで決定論的に再導出**する。

## 1. スキーマ設計（3テーブル + 1リゾルバ + 監査view群）

### 1.1 `staging_periodical.journal_registry`（誌マスタ：1誌1行）
```sql
CREATE TABLE staging_periodical.journal_registry (
  journal_id     text PRIMARY KEY,              -- 安定スラッグ（例 'jca','zeikei'）
  canonical_name text NOT NULL,                 -- 正式誌名（表示用）
  issn_l         text,                          -- キー（P5優先順: ISSN-L > ISSN > NDLBibID > NCID）
  issn           text,
  ndl_bib_id     text,
  ncid           text,
  preferred_key  text NOT NULL,                 -- 'issn'|'ncid'|'ndlbibid' = issue_id接頭辞の採用キー
  tsuukan_rule   text NOT NULL,                 -- 'direct'|'formula'|'ndl_actual'|'ym_terminal'
  formula_anchor jsonb,                         -- formula時: {"anchor_ym":"2016-01","anchor_tsuukan":703}
  manifestation  text NOT NULL DEFAULT 'print', -- 'print'|'ebook'|'separate'
  parent_journal_id text REFERENCES staging_periodical.journal_registry(journal_id),
  status         text NOT NULL,                 -- 'confirmed'|'candidate'|'ncid_key'|'needs_pull'|'new_no_issn'
  evidence_source text,
  note           text
);
```

**tsuukan_rule タクソノミ（issue_id生成の分岐）**
| rule | issue_id 生成 | 該当誌 |
|---|---|---|
| `direct` | `key#{issue_no}`（issue_noが既に通巻） | 判例集・判例速報・号番運用の月刊 |
| `formula` | `key#{anchor_tsuukan + 月数差}` | jcaジャーナル |
| `ndl_actual` | `key#{crosswalk(year,month)}` | 税経通信 |
| `ym_terminal` | `key#{YYYY-MM}`（通巻が存在しない） | ビジネス法務・ビジネスガイド |

### 1.2 `staging_periodical.journal_alias`（別名・変種 → journal_id）
```sql
CREATE TABLE staging_periodical.journal_alias (
  alias       text NOT NULL,                    -- journal_norm の変種
  journal_id  text NOT NULL REFERENCES staging_periodical.journal_registry(journal_id),
  match_type  text NOT NULL,                    -- 'exact'|'prefix'|'regex'
  reason      text,                             -- '旧字'|'号番ノイズ'|'表記ゆれ'
  auto_apply  boolean NOT NULL DEFAULT true,    -- false=人手確認要（合併号等）
  PRIMARY KEY (alias, journal_id)
);
```

### 1.3 `staging_periodical.tsuukan_crosswalk`（年月↔通巻：ndl_actual誌用）
```sql
CREATE TABLE staging_periodical.tsuukan_crosswalk (
  journal_id text NOT NULL REFERENCES staging_periodical.journal_registry(journal_id),
  year       int  NOT NULL,
  month      int  NOT NULL,
  tsuukan    int  NOT NULL,
  src        text,
  PRIMARY KEY (journal_id, year, month)
);
```
→ 既存 `artifacts/periodical/crosswalk/{zeikei,jca}_tsuukan_xwalk.csv` をロード（jcaはformula誌だが実値検証用に保持可）。

### 1.4 リゾルバ `staging_periodical.issue_id_resolved`（view：決定論的再導出）
```sql
CREATE VIEW staging_periodical.issue_id_resolved AS
WITH mapped AS (   -- journal_norm を registry へ（直接 or alias 経由）
  SELECT s.provisional_book_id, s.journal_norm, s.issue_no, s.issue_year, s.issue_month,
         COALESCE(r_direct.journal_id, r_alias.journal_id) AS journal_id
  FROM staging_periodical.issue_stage s
  LEFT JOIN staging_periodical.journal_registry r_direct
         ON r_direct.canonical_name = s.journal_norm
  LEFT JOIN staging_periodical.journal_alias a
         ON a.match_type='exact' AND a.alias = s.journal_norm AND a.auto_apply
  LEFT JOIN staging_periodical.journal_registry r_alias
         ON r_alias.journal_id = a.journal_id
)
SELECT m.provisional_book_id, m.journal_id, r.preferred_key, r.tsuukan_rule,
  CASE
    WHEN r.manifestation <> 'print' THEN NULL          -- 別manifestationは別id空間（合流させない）
    WHEN r.tsuukan_rule='direct' AND m.issue_no IS NOT NULL
      THEN key_prefix(r) || '#' || m.issue_no
    WHEN r.tsuukan_rule='formula' AND m.issue_year IS NOT NULL AND m.issue_month IS NOT NULL
      THEN key_prefix(r) || '#' ||
           ((r.formula_anchor->>'anchor_tsuukan')::int
            + (m.issue_year::int*12 + m.issue_month::int)
            - (substr(r.formula_anchor->>'anchor_ym',1,4)::int*12
               + substr(r.formula_anchor->>'anchor_ym',6,2)::int))::text
    WHEN r.tsuukan_rule='ndl_actual'
      THEN key_prefix(r) || '#' || x.tsuukan::text          -- 命中時のみ
    WHEN r.tsuukan_rule IN ('ndl_actual','ym_terminal')      -- ndl未命中はymへフォールバック
      THEN key_prefix(r) || '#' || m.issue_year || '-' || lpad(m.issue_month,2,'0')
    ELSE NULL
  END AS issue_id_resolved,
  CASE ... END AS status_resolved   -- canonical / canonical_ym / unresolved
FROM mapped m
JOIN staging_periodical.journal_registry r ON r.journal_id = m.journal_id
LEFT JOIN staging_periodical.tsuukan_crosswalk x
  ON x.journal_id=m.journal_id AND x.year=m.issue_year::int AND x.month=m.issue_month::int;
-- key_prefix(r): preferred_key に応じ 'issn:'||issn / 'ncid:'||ncid 等を返すヘルパ
```
**効果**: 新規 `issue_stage` 行はこのviewを通すだけで canonical/canonical_ym/unresolved が決定。
backfillは「viewと実体の差分を当てる」**冪等リコンサイル**に一本化。

## 2. registry seed（28誌・既決定の集約）

| journal_id | canonical_name | key | preferred | tsuukan_rule | manifest | status |
|---|---|---|---|---|---|---|
| zeikei | 税経通信 | issn 0387-2866 | issn | ndl_actual | print | confirmed |
| jca | jcaジャーナル | issn 0386-3042 (issn_l同) | issn | formula(2016-01=703) | print | confirmed |
| biz_homu | ビジネス法務 | issn 1347-4146 | issn | ym_terminal | print | confirmed |
| biz_guide | ビジネスガイド | issn 0387-7035 | issn | ym_terminal | print | confirmed |
| kotsu_minji | 交通事故民事裁判例集 | issn 0389-6544 | issn | direct | print | confirmed |
| hogaku_kyoshitsu | 法学教室 | issn 0389-2220 | issn | direct | print | confirmed |
| kinyu_homu | 金融法務事情 | issn 2185-3223 | issn | direct | print | confirmed |
| rodo_hanrei | 労働判例 | issn 0387-1878 | issn | direct | print | confirmed |
| lt | law&technology | issn 1346-812X | issn | direct | print | confirmed |
| keisatsu_ronshu | 警察学論集 | issn 0287-6345 | issn | direct | print | confirmed |
| horitsu_jiho | 法律時報 | issn 0387-3420 (issn_l同) | issn | direct | print | confirmed |
| jurist | ジュリスト | issn 0448-0791 | issn | direct | print | confirmed |
| hanrei_times | 判例タイムズ | issn 0438-5896 | issn | direct | print | confirmed |
| shoji_homu | 旬刊商事法務 | issn 0289-1107 | issn | direct | print | confirmed |
| kinyu_shoji | 金融・商事判例 | issn 0287-9956 | issn | direct | print | confirmed |
| nbl | NBL | issn 0287-9670 | issn | direct | print | confirmed |
| minsho | 民商法雑誌 | issn 1342-5056 | issn | direct | print | confirmed |
| horitsu_hiroba | 法律のひろば | issn 0916-9806 | issn | direct | print | confirmed |
| katei_saiban | 家庭の法と裁判 | issn 2189-1702 | issn | direct | print | confirmed |
| rokei_sokuho | 労働経済判例速報 | ncid AN00327835 | ncid | direct | print | ncid_key |
| koseki | 戸籍 | ncid AN00274615 | ncid | direct | print | ncid_key |
| toki_kenkyu | 登記研究 | ncid AN00157564 | ncid | direct | print | ncid_key |
| keiji_bengo | 季刊刑事弁護 | ncid AN10468265 | ncid | direct | print | ncid_key |
| horitsu_jiho_ebook | 法律時報e-book | (なし) | — | — | ebook→horitsu_jiho | separate |
| ho_tetsugaku | 法と哲学 | issn 2188-711X(未検証) | issn | direct | print | candidate |
| jinji_chizu | 人事の地図 | (なし) | — | ym_terminal | print | needs_pull |
| jcaa_biz | jcaaビジネスジャーナル | (なし) | — | direct | print | new_no_issn |

※「ISSNが来たら preferred を ISSN-L>ISSN へ自動昇格」を registry 更新で一元処理 → 二重キー誤スプリット根絶。

## 3. alias seed（誤スプリット予防：P10で発見した変種）
| alias | journal_id | match_type | reason | auto_apply |
|---|---|---|---|---|
| 警察學論集 | keisatsu_ronshu | exact | 旧字 | true |
| `^jcaジャーナル\[\d{4}\.\d{2}\]号$` | jca | regex | 号番ノイズ | true |
| 労働経済判例速報660・ | rokei_sokuho | exact | 合併号 | **false**（人手確認） |
| law&technology「…」特別公開版 | （別manifestation） | — | 特別公開版 | 対象外 |
| 戸籍特別版 | （別manifestation） | — | 特別版 | 対象外 |

## 4. 標準監査ビュー（B：常設・ドリフト自動検知）
| view | 検知対象 | 期待 |
|---|---|---|
| `audit_false_merge` | issue_id ごと distinct(年月)>1 | 0件 |
| `audit_false_split` | (journal_id,年,月) ごと distinct(issue_id)>1 | 0件 |
| `audit_tsuukan_monotonic` | formula誌の通巻連番ギャップ／ndl誌の増刊飛びログ | formula誌=ギャップ0 |
| `audit_key_collision` | 同一 journal_id に issn:と ncid: が併存 | 0件（二重キー検知） |
| `audit_unregistered` | issue_stage の journal_norm が registry/alias 未登録 | 監視（新誌・新変種の早期発見） |
| `audit_resolver_drift` | issue_id_resolved ≠ 実体 issue_id | リコンサイル要件を可視化 |

→ P10で手で回した監査が**新データ着地時に自動再評価**される。特に `audit_resolver_drift` が
「再ロードで provisional に戻った行」を即surface＝手作業backfillの再発を検知。

## 5. 適用順（GO後）
1. DDL: 3テーブル作成（mutation：CREATE）。
2. seed投入: registry 27行 + alias + crosswalk（既存CSVから）。
3. リゾルバ + 監査view作成。
4. `audit_resolver_drift` を実行し、現 canonical群と view の一致を検証（M1/M2の再現＝回帰テスト）。
5. 監査view群が全0であることを確認 → P11 として結果artifact化。

## 6. スコープ外 / 要確認
- `issue_stage` のコメント "audit only"：本マスタ＆昇格を**本流パイプラインへ反映する経路**は別WO（要owner確認）。
- 外部入力待ち（人事の地図ISSN・税経2026 NDL再取得・法と哲学検証）は registry 更新で即反映される設計。
- セキュリティ別件：`biblio.*` 4テーブル RLS無効（advisor critical）。periodical外だが要対応。
