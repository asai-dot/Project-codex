# DD: 著者(オーサー)モデルの統一 — 設計資料2版の食い違い裁定 v1 (2026-06-23)

- status: proposal（Owner ratify 待ち / 実DB照合は別途要承認）
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
