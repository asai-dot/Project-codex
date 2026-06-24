# DD: 著者(オーサー)モデルの統一 — 設計資料2版の食い違い裁定 v1 (2026-06-23)

- status: 実DB照合済(2026-06-23, read-only)。裁定の方向は実装で裏付け済。§8参照
- 関連: KAKEN_lean_plan_v1（§0.5 KAKEN first-class / §4.1 リンク層）
- 目的: 「繋ぎこみの器」を確定する。著者モデルが正本2版で食い違っており、これが決まらないと人↔論文↔KAKEN↔判例の結線設計に進めない。

---

## 1. 食い違い（事実）

| 版 | alo_persons の姿 | リッチ属性(専門/所属/学位/受賞) |
|---|---|---|
| `ALO_文献・著者スキーマ v1.0`(3/9) | — | **7テーブルすべて「L1 典拠」**（person_external_ids / specialties / affiliations / degrees / awards） |
| `03 文献レイヤ技術仕様書 v0.1`(3/10) | **薄い**（person_id / name_display / family / given / **crid のみ**） | （持たない） |
| `00 全体技術仕様書 v0.1` §4 | 文献主要テーブル = `alo_works, work_identifiers, **alo_persons**` ＝薄い側を採用 | — |

## 2. 裁定基準（上位の確定原則が決める）

正本の序列は **全体仕様書 ＞ データ編成指針 ＞ 個別レイヤ仕様書**。上位がこう定めている:

- 全体 §3「**Canonical/Derived分離は確定済み・再議論しない**」
- 編成指針 原則2「**Canonical is Thin（情報量でなく"責務"を限定）**」／原則3「価値は複数ソースの**重ね合わせ＝L2**から生まれる」
- リンクレイヤ §4「同一性解決ハブは **`fingerprints`**（entity_type=person, fp_type別 active partial-unique）」＋ `resolution_log`

→ よって **`文献・著者スキーマ v1.0` が7テーブルを全部「L1」と置いたのが上位原則違反**。裁定は「版の取捨」ではなく「**層の置き直し**」。

## 3. 確定モデル（層で分離。KAKENは捨てず置き場所を正す）

```
L0 Raw     ext_kaken_projects_raw / ext_cinii_person_raw / ext_researchmap_raw / ext_ndl_*_raw
              （payload/source_system/source_record_key/fetched_at/parser_version/payload_hash）
   │
L1 Canonical(薄い)  alo_persons … person_id / person_uri / name_raw / name_norm / name_reading / person_type
   │                fingerprints(entity_type=person) … 同一性ハブ ★fp_type拡張(下記)
   │                resolution_log … 名寄せ判断履歴
   │
L2 Curated Overlay  person_specialties / person_affiliations / person_degrees / person_awards
                    （source='kaken'|'researchmap'|'cinii'|'manual' で並列保持・劣化させない）
   │
L3 Derived          著者signals（AUTHOR_AUTHORITY等）, 共著グラフ(work_authors自己結合)
```

### 各テーブルの帰属（v1.0 の7テーブルを再分類）
| v1.0 のテーブル | 裁定 | 層 |
|---|---|---|
| alo_persons | 薄く保つ（identity + hub のみ） | L1 |
| person_external_ids | **fingerprints に吸収**（重複のため。下記） | L1(fingerprints) |
| person_specialties | 採用、ただし **L2 へ再分類** | L2 |
| person_affiliations | 採用、**L2** | L2 |
| person_degrees | 採用、**L2** | L2 |
| person_awards | 採用、**L2** | L2 |
| work_authors | そのまま（記事×著者中間） | L1 |
| resolution_log | そのまま | L1 |

### 識別子の置き場所（重複の解消）
`fingerprints`（リンクレイヤ正本の同一性ハブ）と `person_external_ids`（v1.0）が**二重定義**。
→ **`fingerprints` に一本化**。ただし現行 fp_type は `crid/orcid/isbn/doi/...` のみで **KAKEN系が無い**。
**fp_type を拡張する（これが繋ぎこみの実装上の肝）:**

- 追加: `nrid`（CiNii研究者番号・人↔論文の一次キー）/ `kaken_id`（eradCode）/ `researchmap_id` / `ndl_auth_id`
- ISSN は従来通り対象外（雑誌レベルID）。
- これにより 人 ↔ 論文(CiNii) ↔ KAKEN ↔ NDL著者 が同一性ハブ1枚で突合可能になる。

## 4. これで満たす要件

- ✅ Canonical/Derived分離・Canonical is Thin（確定原則）
- ✅ **KAKEN first-class / 使い切る**（リッチ属性は L2 に source 並列で全保持、raw は L0。劣化させない）
- ✅ Links Are the Core Asset（fingerprints＋alo_edges に集約、fp_type拡張で結線面積拡大）
- ✅ 繋ぎこみの器が一意に決定 → 人↔論文/人↔人/人↔文献/人↔判例 の設計に進める

## 5. 取込前ゲート（前回の発掘で判明した落とし穴を器側で防ぐ）

1. **NRID汚染**（1著者にNRID 10〜35個）: fingerprints へ昇格前に代表ID選別＋`resolution_log`＋confidence。`uq_fp_nrid_active` で active 衝突を物理防止。
2. **eradCode closed**: researchmap直結不可。KAKEN grant RDF の member 逆引きで eradCode を得てから fingerprints 登録。
3. **古い法律論文の著者ID欠落**: hard ID 無は氏名+収録誌(ISSN→serial)で候補、canonical 昇格はしない（LIT-5 名寄せ未到達<30% 監視）。

## 6. 未確定（Owner 判断が要る）

- **実DB(alo-connect, Supabase)が薄い版/リッチ版どちらで実装されているか未確認**（本番DB読取りが未承認のため）。
  - 薄い版で実装済なら本DDは「L2追加」だけで済む。リッチ版が既に入っていれば person_external_ids→fingerprints の寄せが必要。
  - → **本番DBの read-only 確認の許可**をもらえれば確定できる。
- fp_type 拡張（nrid/kaken_id/researchmap_id/ndl_auth_id）は DDL 変更＝SE(花岡さん)レーンの承認事項。

## 7. 次の一手

1. (要承認) 本番DB read-only で alo_persons / fingerprints / person_* の現状実装を照合。
2. 本DD ratify 後、`fingerprints.fp_type` 拡張を SE レーンに起票。
3. KAKEN_lean_plan §4.1 を本DDの層モデルに整合させて改訂。

---

## 8. 実DB照合結果（2026-06-23, read-only）

本番DBは **`asai-dot's Project`（ref nixfjmwxmgugiiuqfuym, Tokyo）**。`alo-connect` は空（誤認回避メモ）。
著者モデルは設計資料2版のどちらとも違い、**`authority` スキーマ（claim+evidence型）に進化**して既に稼働・大量投入済み。

### 8.1 実テーブルと規模（実測）
| テーブル | 行数 | 役割 |
|---|---|---|
| authority.person | **128,081** | 人物正本（**薄い**: person_id/type/canonical_name/status のみ） |
| authority.person_history | 270,160 | 識別子・履歴（下記） |
| authority.person_affiliation | 230,309 | 所属（source_system + evidence_strength 付き） |
| authority.person_alias | 30,810 | 別名 |
| authority.publication | **7,348** | 論文/刊行物（少ない＝下記ギャップ） |
| authority.publication_author_claim | 7,125 | **人↔論文リンク**（confidence/trust_tier/evidence） |
| authority.publication_author_evidence | 7,589 | 著者主張の証拠（raw/normalized/payload_json） |
| biblio.authors | 2,200 | 書籍著者（ndl_auth_id/viaf_id 保持。authority.person と**別系統**） |
| dynamic.cases | **0** | 判例未投入 |

person の内訳(source): 日弁連会員 92,969 / CiNii研究者 73,155 / 裁判官(yamanaka) 64,185 = **弁護士・研究者・裁判官を横断する人物authority**。

### 8.2 裁定の答え合わせ
- ✅ **薄い Canonical は実装で正解**。`authority.person` は identity のみ。リッチ属性は person_affiliation / person_history / person_alias に **source_system 並列**で分離済（＝本DDの L1薄/L2overlay と一致）。
- ✅ **人↔論文は claim+evidence で実装済**（publication_author_claim, trust_tier high4,110/low2,561/med454）。本DD §4.1 の「繋ぎこみ＝リンク層」が既に動いている。

### 8.3 裁定の訂正（実装に合わせる）
- ❌ §3 の「`fingerprints` に一本化／fp_type拡張」は**実DBに fingerprints が存在しないため不適用**。
  実態: 識別子は **`person_history`** に history_type として格納 — `scholar_nrid`(73,155) / `researchmap_profile`(17,618) / `orcid_id`(279) / `lawyer_registration_number`(48,690) 等。
  → 提言を変更: **識別子専用ハブ `authority.person_identifier`（id_system, id_value, source, confidence, active partial-unique）を新設**し、person_history散在分を移行。これが繋ぎこみの実装上の正しい一手。
- ⚠️ **eradCode(kaken_id) は実DBに存在しない**（person_history の type 一覧に無い）。KAKEN固有キーは未投入＝「KAKENを使い切る」はここから。CiNii NRID(73,155)経由の接続は可能。
- ⚠️ **biblio.authors(2,200) と authority.person(128,081) が別系統・未連結**（書籍著者 vs 論文著者）。統合 or リンクが必要（dup温床）。

### 8.4 ★繋ぎこみの本当のボトルネック（Owner の直感の数値的裏付け）
**人は厚い（128,081人, うち研究者73,155にNRID）が、繋ぐ相手の「論文」が薄い。**
`authority.publication` はわずか **7,348件**、しかも中身は **弁コム3,802 / NDL判事突合3,500 / bootstrap46** で、**CiNii法律論文 638,021件は未投入**。
→ つまり KAKEN/研究者が宙に浮いて見えるのは事実で、原因は **「論文側(CiNii 63.8万)が authority.publication に入っていない」**こと。
**KAKENをこれ以上集めるより、CiNii論文をpublicationに載せて claim で人と繋ぐのが最優先。** dynamic.cases=0 なので 人↔判例 はその次。

### 8.5 改訂後の次の一手（優先順）
1. **CiNii法律論文(638k)を authority.publication へ投入**（繋ぎこみの相手を用意）。NRIDで publication_author_claim を自動生成。
2. **`authority.person_identifier` ハブ新設**＋ person_history の識別子を移行。eradCode の受け皿もここに。
3. **biblio.authors ↔ authority.person の名寄せ統合**（resolution_log 経由）。
4. KAKEN eradCode を ハブへ（CiNii NRID 突合 → person_identifier）。
5. dynamic.cases 投入後に 人↔判例（評釈→判例）。
