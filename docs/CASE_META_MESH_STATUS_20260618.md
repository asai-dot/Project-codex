# 判例オブジェクト メタ×個別データ 噛み合わせ現況 (CASE META MESH STATUS)

- date: 2026-06-18 JST
- status: **read-only reality check / analysis only**（DDL・DB write・canonical promotion・alo_edges write・Box mutation を一切含まない）
- scope: 2つのメタ（NII-TTL / D1KOS）× 個別データ（D1-Law / LIC）の噛み合わせが、設計・データ・昇格のどこまで進み、どこで止まっているか
- sources: Box `20260615_DD-CASE判例オブジェクト` ほか reality check / DD / worklog 群、D1-Law判例DLフォルダ実ファイル、D1-LICクロスウォークCSV、OPAC/CiNii worklog（2026-06-17）

> 注: 本書は既存レポートの "no mutation" 規律に従う派生サマリです。canonical 反映や production load の指示ではありません。

---

## 0. 一行結論

材料（個別データ）も、噛み合わせ方（ID確定システム設計）も揃っている。**詰まっているのは「設計の具体化」ではなく、(1) canonicalへの昇格ゲートの意図的HOLD と (2) 設計が要求する人手レビューの未消化（accepted = 0）**である。

---

## 1. 4系統の素材（出所と整理状況）

> **D1取得数の訂正（重要）**: DD-CASE reality check（2026-06-11作成）は「取得67,966 / 27.2% / 残り182k」と記すが、これは **2026-06-01スナップショットで stale**。その後 **2026-06-05 に大規模ingest（NEW +124,805）** が走り、実態は **取得≈192,885（≈77.2%）/ 残り≈57,000（≈22.8%）**。二経路で検証済: (a) ingest積上げ 68,080+124,805=192,885、(b) `acquired_hanrei_ids_20260605.txt` 1,928,850byte ÷10 ≈192,885。reality check / Phase0計画の「残り182k」は要更新。

| # | 種別 | 名称 | 出所 | 実数（実ファイル確認） | 整理状況 |
|---|---|---|---|---|---|
| ① | 個別 | D1-Law 判例DL | D1ロー | **2026-06-05時点 distinct判例ID ≈192,885 / 249,863（≈77.2%）**、残り≈57,000 | 取得・正規化済。**母数249,863は"契約済の総件数(民事セレクション)"であり取得数ではない**。下記注記参照 |
| ② | 個別 | LIC（4誌解説本文） | LIC（≒ユーザ表記「LYC」） | resolved links **5,475**、D1 source works 3,035、LIC targets 3,631 | scratch DBロード＋検証pass。現在値最強。**production未昇格** |
| ③ | メタA | NII 判例 RDF/TTL | NII（国立情報学研究所）= ユーザ表記「TTL/国立情報センター」 | **65,855件**、自然キー解析率≈100%、`saikosai_id`(courts.go.jp 6桁) 保持 | 自然キー＋最高裁IDの正準ソース。`caselawp:court`/`foaf:primaryTopic` 等RDF語彙 |
| ④ | メタB | D1KOS 体系目次 | D1（= ユーザ表記「D1コス/D1コース＝ナレッジ・オブ・システム」） | D1KOSノード **9,449**、OPAC/CiNii staging 32テーブル | 分類タクソノミー。論点・分野軸 |

---

## 2. 噛み合わせ設計（実装粒度まで具体化済み）

中核 = **`DD-CASEID-001`（判例ID確定システム, candidate v0.1）** + 下位 `31b_case_id_resolution_flow.md`。
思想（2026-06-04 オーナー確定）: **「判例の特定（自然キー）」と「事務所のID確定（名寄せ・採番）」は別レイヤ。**

```
                 メタA: NII-TTL                     メタB: D1KOS(体系目次)
              自然キー + saikosai_id                 論点/分野タクソノミー(9,449)
                      |                                      |
   個別:D1 ──┐        |  (fingerprint: saikosai_id × d1law_id)|
            ├──▶  case_observation  ──[名寄せ]──▶  case_key(ULID,不変)
   個別:LIC ─┘     (源別 生同一性レコード)          │   = 事務所の真ID anchor
                                                    │
            名寄せ順序固定:                          ├─ confirmed: canonical_uri = fn_v2(forum,date,docket)
            決定的自然キー → 強外部ID → fuzzy → 人手   ├─ provisional: alo:case:jp:_prov:{case_key}
            (全決定を resolution_log に記録)          │
                                                    └─ D1KOS論点 ↔ 判例: alo_edges(support edge)
   Tier: A=機械可 / B=初回人手 / C=auto禁止review     審級・答申↔判決 = merge禁止, edgeで連鎖
```

- 着地層 `case_observation`（content_grade: full/summary/stats_only）に全入力が集約。
- メタA×個別の噛み合わせ実証: **NII∩D1 自然キー一致 12,661件（dry-runで確認）**。
- 品質ゲート9種（orphan 0 / 自然キー重複 0 / fingerprint衝突 0 ほか）定義済み。
- 検証状態: deterministic_self_verification = **done** / independent_meaning_audit = **pending** / owner_approval = **pending** → `accepted_v1.0` 未昇格。

→ **設計は抽象ではなく実装粒度。candidate のまま止まっているのは昇格ゲートのため。**

---

## 3. レーン別 進捗 vs 停止地点（ボトルネック可視化）

| レーン | 出来ていること | 止まっている地点（実数） |
|---|---|---|
| D1判例DL | 取得・正規化・canonical CSV append | **取得≈192,885 / 249,863（≈77%）、残り≈57k**（reality checkの27%/182kは6/1のstale値） |
| D1-LIC | scratch DBロード＋検証pass(15/15)、stable v0 export(7.5MB) | **production昇格=未許可 / canonical case=0** |
| OPAC-CiNii(判例引用) | 32テーブルstaging、reviewワークシート1,648行(9 batch) | **decision overlay=0 / accepted edge=0** |
| OPAC-CiNii(法令参照) | snapshot 23,280、strong 281をreviewキュー化 | **全件 pending_review / confirmed match=0** |
| 判例ID確定(DD-CASEID-001) | 実装粒度設計＋机上検証done(一致12,661) | **独立監査=pending / オーナー承認=pending** |
| CaseBundle | 設計 v1.5 確定（cases/case_annotations分離, guards） | **runtime実装状況=未確認** |
| 直近 worklog(2026-06-17) | guarded worker稼働、候補生成は自動で回る | human-input **pending 115 / ready 0**、gate=`planned_hold` |

### ボトルネックの正体（2つ）
1. **意図的なガバナンスHOLD** — no DDL / no canonical promotion / no `alo_edges` write / production not authorized が全レポートに明記。オーナーratify＋GPT Pro独立監査を通すまで canonical を作らない自己規律。
2. **人手レビューの未消化** — 設計上 Tier B/C は人手判断が必須だが、decision は **全レーンで実質0件**。機械の候補生成だけが空回りしている。

→ **素材不足でも設計不足でもない。「噛み合わせを確定（canonical化）する最後の一押し」がゲートと人手で止まっている。**

---

## 4. 体制（誰が・どこで・何を）

| 主体 | 役割 |
|---|---|
| 浅井（オーナー） | 設計思想の確定者。**accepted昇格のratifyゲートそのもの**（owner_approval pending はここ待ち） |
| Mac Claude Code（番頭） | DD起票・probe・クロスウォーク生成・reality check作成 |
| GPT Pro（目付け役/ometsuke） | 独立意味監査。D1-LIC=`DESIGN_PASS_WITH_NOTES`、6/17 SILVER-RESOLUTION-KICKOFF=`ADOPT_AS_PLAN` |
| 花岡さん | CiNii/雑誌レイヤー取り込み（`insert_article_meta_CiNii.sql` 等）、NII/CiNiiメタ実務 |
| OPAC/CiNii guarded worker lane | 5.3ワーカー＋15分監督ハートビート＋read-onlyサイドカー。候補生成は自動、human-input待ちで停滞 |

---

## 5. 推奨アクション（ゲートを開ける一手）

1. **DD-CASEID-001 を `accepted_v1.0` に昇格（オーナーratify）** — 噛み合わせ設計の candidate 固定を解除する起点。
2. **人手レビューを少量・層化で実際に流す** — OPAC P1 1,648行/法令参照 281件の全件ではなく、stratified sample 数十件を accept/reject し、decision overlay を 0→1 に動かす。Tier B 機械化の gold が貯まり始める。
3. **D1残り≈57k件の取得と名寄せ確定を並走** — 母数取得と確定は独立に進められる。なお Phase0計画（WO-D1LAW-DL-001）の「残り182k」は6/5 ingest前のstale値で、実際の残量は約1/3（≈57k）。工数見積りを引き直す。6/5の+124,805件が承認済canonical昇格かは要確認。
4. **canonical昇格は別 production-readiness gate で小さく開ける** — まず D1-LIC を `case_observation` candidate として受ける所から。一括 `alo_edges` 書き込みはしない現行規律は妥当。

---

## 付録: 主要参照（Box file id）

- DD-CASEID-001 判例ID確定システム: `2266457039407`
- 31b_case_id_resolution_flow.md: `2264249368602`
- DD-CASE reality check (D1/LIC/OPAC/CaseBundle): `2279870463624`
- D1-LIC crosswalk stable v0 (csv 7.5MB): `2278663252764`
- D1KOS/OPAC-CiNii 法令参照レーン報告: `2256674974977`
- SILVER-RESOLUTION-KICKOFF 監査依頼(6/17): `2290154531785`
- OPAC/CiNii worklog(6/17, live counts): `2290066958381`
- D1判例DLフォルダ: `360757479930` / 判例一覧.csv: `2154997033206`
