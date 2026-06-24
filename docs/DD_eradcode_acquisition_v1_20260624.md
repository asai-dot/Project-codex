# DD: eradCode 取得・投入の方針（科研費HOLDの解き方）v1 (2026-06-24)

- status: 設計（read-only実測に基づく）。**KAKEN fetch / DB書込は HOLD**、サンプル検証→Owner ratify 後。
- 親: `KAKEN_lean_plan_v1`(§2 取得戦略 / §5 HOLD) / `DD_author_model_resolution_v1`(§8.3 person_identifier) / `DD_cinii_publication_ingestion_v1`
- 目的: 「**科研費XML全件取得は意図的HOLD / eradCode未投入**」の2点を、全件クロールに戻らず前進させる。

---

## 1. read-only実測（authority.person_history, 2026-06-24）

| 指標 | 値 |
|---|---|
| scholar_nrid 保有 person | **73,155**（1人1NRID, 1:1:1） |
| └ `9000`系（CiNii内部採番＝e-Rad紐付け無し） | **69,501** |
| └ `1000`系（e-Rad研究者番号由来） | **3,654** |
| researchmap_profile 保有 | 17,618 |
| orcid_id 保有 | 279 |
| **eradCode(kaken_id)型** | **0（未投入）** |

NRID形は全て `X000` + `0` + 8桁（例 `1000000002957` / `9000000000269`）。

## 2. 読み取れること（方針の分岐点）

- **eradCode は大半が既存データから導けない。** `9000`系 69,501（=全scholarの95%）は CiNii内部採番で e-Rad 番号を内包しない。これらの eradCode を得るには外部取得が要る。
- **だが全件クロール(111.6万URL)は不要。** 既に **73,155 の研究者を名前・NRID付きで保持**している。これが理想的な **seed**。KAKEN を「人起点で逆引き」すれば、対象は最大73k件の研究者照会で済む（≒1/15以下、旧採番94万クロール不要）。
- **`1000`系 3,654 は eradCode 導出の可能性が高い**（NRID = `1000`+`0`+8桁 の 8桁が研究者番号＝e-Rad の候補）。**要確証**（KAKEN既知ペアか CiNii NRID仕様で1件突合）。当たれば**取得ゼロで3,654件**入る。

→ KAKEN_lean_plan の「科研費XML全件取得HOLD」は、**全件クロールという手段がHOLDなのであって、seed逆引きは別物・着手可能**。本DDで手段を差し替える。

## 3. 方針（3段、安い順）

**E-1. 導出（取得ゼロ・確証済）**: `1000`系3,654 の NRID下8桁 = 研究者番号 = eradCode。**全件導出可・取得ゼロ**。person_identifier に投入（source='nrid_derived', confidence=高）。
  - 規則確証(2026-06-24): NII公式「NII研究者ID = `1000` + 研究者番号(8桁ゼロ詰め)の13桁。例 研究者番号80802743 → `1000080802743`」。研究者番号＝e-Rad研究者番号。
  - read-only検証: 1000系 **3,654件すべて**下8桁が有効8桁・全件ユニーク・衝突0（範囲 00000034〜90975947）。
  - 導出SQL（staging, 非破壊）:
    ```sql
    SELECT person_id, right(history_value,8) AS erad_code
    FROM authority.person_history
    WHERE history_type='scholar_nrid' AND left(history_value,4)='1000';
    -- → authority.person_identifier (id_system='kaken_id', source='nrid_derived')
    ```
**E-2. seed逆引き（bounded fetch・実現性確認済 2026-06-24）**: 73,155 scholar を**人起点照会**。全件クロールしない。
  - **主経路**: KAKEN研究者検索 `nrid.nii.ac.jp/opensearch/?appid=...&qm={研究者番号}` → eradCode/科研費課題/所属/審査区分を取得。`eradCode` 属性 / `<researcherNumber type='erad'>` が正規経路（Phase B RESULTで確定）。
  - **認証/レート**: appid=`INrPet7AKLGaTza03Tqd`（CiNii/KAKEN/NRID共通）、**1 req/s・RETRY3**（プロジェクト既定）。
  - **スループット**: 73,155件 ≈ 逐次20時間 / 並列4で~5時間（全件クロール≒13日の1/60）。
  - **層別（実測 2026-06-24）**: 1000系3,654=研究者番号保有で確実逆引き（実質E-1と重複）。**9000系69,501=研究者番号なし** → 代替キーで繋げるのは **researchmap併持 16,450 = 23.7%**（orcid 263は誤差）。残り約76%(5.3万)は現状の代替キーで繋がらない。
  - **歩留まりのボトルネックは取込側**: CiNii detail生データの researchmap 供給率はほぼ100%（サンプル5件全creatorに1本）なのに、person_history への取込は 17,618 止まり。取込を増やせば9000系の繋がる率は上げられる。
  - 注: 23.7%は「研究者プロフィールに繋げる率」であって科研費保有率ではない。**eradCode が取れる9000系 ≤ 23.7%**（さらにKAKEN課題保有でフィルタ）。着手前に層別サンプルで実測。
**E-3. 残差は追わない**: 科研費を持たない著者（article-only）は eradCode が存在しない。**無理に埋めず欠落を記録**（編成指針：盲信しない・網羅の線をOwnerと合意）。

## 4. 受け皿（前提テーブル）

`authority.person_identifier` 新設（DD_author_model §8.3）。
- 列: `person_id` / `id_system`(nrid/kaken_id/researchmap/orcid/ndl_auth) / `id_value` / `source` / `confidence` / active partial-unique。
- 既存 person_history の scholar_nrid/researchmap/orcid をここへ移行 ＋ eradCode を追加。
- eradCode 投入時は `id_system='kaken_id'`, source='nrid_derived'(E-1) / 'kaken_lookup'(E-2)。

## 5. eradCode が入ると何が繋がるか（価値）

- KAKEN科研費の**研究分野・所属・共同研究者・grant履歴**を、既存 `authority.person`(128k) の正しい人へ overlay（person_affiliation/history に source='kaken'並列）。
- CiNii論文(投入後)↔KAKEN研究者 を eradCode/NRID で確実結線 → 「論文＋科研費＝オーサーの全体像」が立ち上がる。
- KAKEN固有のオーサー由来一次情報を**使い切る**（§0.5）。

## 6. ゲート & HOLD

1. (read-only) E-1 導出規則を1件確証 → 3,654件の導出妥当性を可視化。
2. E-2 サンプル500人で eradCode hit率・誤マッチ率を計測（**fetch は研究者照会のみ、project全件クロールしない**）。
3. person_identifier DDL（SE/花岡レーン）。
4. dry-run（staging）→ Owner ratify → 本投入。

**HOLD（ratifyまで）**: 科研費XML全件クロール / authority.* 本番書込 / person canonical昇格。
**廃止**: 旧採番94万件の7日全件クロール（seed逆引きで代替）。

## 7. 確証状況（2026-06-24）

- ✅ **`1000`系 NRID→eradCode 導出規則 = 確定**（下8桁。NII公式仕様＋実DB 3,654件全件検証）。E-1 は着手可（DDL＋ratify後に投入）。
- ✅ **KAKEN研究者API 逆引き = 確認済**（ワーカー調査 2026-06-24）。`nrid.nii.ac.jp/opensearch` で研究者番号→eradCode/grant/所属/区分。appid・1req/s・並列4で~5h。E-2は技術的に成立。
- ⚠️ **9000系の科研費保有率（=逆引き歩留まり）は未測定** → 層別サンプル500件で実測（数%〜十数%の当て）。研究者番号がない9000系は氏名/researchmap/ORCIDで課題側マッチが要る。
- ⚠️ researchmap公開APIの「研究者番号→permalink」直接逆引きは未確認（CiNii detailの既存researchmap IDで回避可）。
- ⚠️ 一個人に複数研究者番号のケース有り（NII注記）→ E-1/E-2とも `resolution_log` で名寄せ管理。
- ⚠️ nrid/KAKEN opensearch のレート上限・規約原文は一次未確認（support.nii.ac.jp が403）。1req/sは安全側。researchmap V2(更新系)はIP登録申請必須化(2025-07)、公開JSON参照のみなら申請不要見込み。

---

## 8. 小残課題 実測（2026-06-24, ローカルワーカー, read-only）

- **person_identifier 移行サイジング**: scholar_nrid 73,155(1:1) + researchmap_profile 17,618 + orcid_id 279 ≈ 移行 9.1万行規模。orcid は誤差。
- **9000系の代替キー歩留まり = 23.7%**（researchmap併持 16,450 / 69,501）。orcid併持 263(0.4%)。残76%(約5.3万)は現状キーで未連結。
  - detail側 researchmap 供給率はほぼ100% → ボトルネックは person_history 取込率（17,618止まり）。取込増で改善可。
- **biblio↔authority 統合**: biblio.authors 2,200件、**ndl_auth_id=0 / viaf_id=0**（外部権威ID未投入＝未連結）。供給源は CiNii detail creator の CINII_AUTHOR_ID / VIAF が候補。
- CiNii detail の personIdentifier: RESEARCHMAP は各creatorにほぼ必ず1本、ORCID はほぼ無し、CINII_AUTHOR_ID/KAKEN_RESEARCHERS/VIAF は研究者番号(1000系)保有creatorに付随。NRID は1creatorに複数（名寄せ候補束）。

### 含意（実装の優先度）
1. E-1（1000系3,654, 取得ゼロ）は即効。
2. 9000系は **researchmap取込を増やす**ほど繋がる率が上がる（detail側に在庫あり）。eradCode直取りは保有層に限られる。
3. biblio↔authority は CiNii detailの著者IDを供給源に連結する余地（別タスク）。
