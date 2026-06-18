# DD-LITID-PLAN — 4ルート書籍 版同定パイプライン 計画 v0.1

- 作成日: 2026-06-18
- 起案: Claude (Project-codex セッション)
- 親設計: DD-LITID-001 v0.2-draft（biblio_identity_noisbn / DESIGN_PASS_WITH_NOTES）、
  DD-LITID-FP（4信号 fingerprint 強化）、DD-LITID-001-ATTR（属性観測層+projection）
- gate: DESIGN（DDL適用・backfill・本番突合・canonical promotion・serving確定は対象外）
- status: draft（GPT Pro お目付け役 監査へ）

---

## 0. ゴール（owner 定義・変更不可の枠）

実データで、自所が **物理本/裁断本** で持つデータと、**LION BOLT 由来 / 弁コム由来 /
リーガルライブラリー(legallib)由来** の大きく4ルートの書籍データについて、

1. 各ルートの書誌を **版ごとに区分管理** でき、
2. それが **NDL 等の書誌DBと突合** でき、
3. **別の本は別の本、同じ本は同じ本** とカウントできる状態を実現する。

今後本を購入した時の処理（定常運用）まで含めて、最短・最正確・最小手戻り・高拡張で到達する。

---

## 1. 計画の核（最善手の原理）

> **不可逆で安価なこと（出所・権利・ソース同一性の"捕捉"判断 ＋ raw 投入）は今すぐ全部やる。
> 可逆なこと（閾値・重み）はデータで較正する。不可逆で高価なこと（promote / canonical /
> serving 確定）は shadow で実証してからゲートを開ける。**

「設計を厚くする」と「生データを進める」は対立しない。対立しているのは
**「不可逆な判断」と「やり直せる判断」を混ぜていること**。これを分離すれば並行で進む。

---

## 2. データモデル（背骨・最初に1回だけ確定）

```
holding             … 自所が物理/裁断で「所有」している実体（冊・PDF）。所有の SoT。
   ↓ owns
edition (manifestation) … 版・刷レベルの同一性。NDL bibid を錨にする。
   ↓ groups
work                … 著作レベル（版違いを束ねる上位クラスタ）。
   ↑ provides evidence
source_biblio_item  … 4ルート各々の生書誌レコード。ソース固有 ID を破壊しない。
                      複数 item が同一 edition を指してよい（版を束ねない）。
authority           … NDL（＋CiNii/KAKEN）。edition/work 解決の権威ハブ。
```

- `DDL-20260428-01「版を束ねない」`、`fingerprints = identity SoT`、`title-only 一致禁止`、
  `独立証拠2つで confirm`、`raw 保全`、append-only 観測 という既存正本と整合。

### カウント定義（ゴール3の操作的定義）
- **work 数** = 重複排除した著作数。
- **edition 数** = 版・刷の数（「版ごと区分管理」の本体）。
- **holding 数** = 自所が現に所有する実体数（物理＋裁断）。
- **access 数**（区別する）= オンライン購読（弁コム/legallib）で閲覧可能だが所有ではない数。

「別の本は別の本／同じ本は同じ本」＝ **edition 粒度の entity resolution ＋ work 粒度の上位クラスタ**。

---

## 3. 可逆性で工程を分ける（計画の肝）

| 区分 | 例 | 扱い |
|---|---|---|
| 🔴 不可逆・安価 → 今すぐ確定/捕捉 | `source_provenance_chain` / TOC `origin_publisher`・`redistributor_chain` / `rights_profile` / `medium_origin`(digital/paper_scan) / 取得時刻・主張時刻 | 取得時に取り損ねたら復元不能。raw 投入と同時に必ず捕捉（監査 must_fix M1〜M4 の本質） |
| 🟢 可逆 → 実データで較正 | pub_date 配点(年0.3/月0.6/日1.0) / page_count 許容差 / TOC 類似閾値(章80%/±2章/Levenshtein) / single_authority 確度 / disputed 自動解消 TTL | proxy で決め打ちしない。本番分布が出てから当てる。再実行で変更可 |
| 🟠 不可逆・高価 → shadow 実証後にゲート開放 | candidate→confirm promote / canonical 採用値の serving 反映 / DDL / backfill | dry-run/shadow で誤分割・誤統合の実件数を見てから |

raw 投入は実質ノーリスク（append-only・ソース忠実＝raw 保全原則で手戻りゼロ）。止める理由がない。

---

## 4. フェーズ手順

- **Phase 0｜背骨確定（文書のみ）**: エンティティモデル＋🔴捕捉必須メタの列を確定。
  🟢閾値は「後で較正」と明記し空欄で凍結。スキーマ手戻りの主因を先に消す。
- **Phase 1｜4ルート＋NDL の raw 投入（並行・ノーリスク）**: 未投入の **legallib・LION BOLT** を投入
  （現状 biblio は asai 蔵書 NDC5,503/NDLC5,020 ＋弁コム3,802 のみ）。各行に🔴メタを刻む。
  NDL（＋CiNii）を権威ハブとして取り込み。
- **Phase 2｜正規化＋fingerprint 生成（決定的・再実行可）**: 出版社 NFC・(株)/(有)表記揺れ・
  page_count 正規化・pub_date 刷判定を **disputed 判定の前段** に強制。E3/E4 を全観測に付与。
- **Phase 3｜NDL ハブ突合を shadow 実行**: §5 waterfall で source→NDL 解決を確定書込せず候補リンクのみ生成。
  誤分割/誤統合/disputed/edition_suspected の実件数を初計測。
- **Phase 4｜実分布で較正＋人手レビューはバケツ単位**: 🟢閾値を確定。disputed は全件でなく
  腑分けバケツ（刷違い/別版/同名異本/表記揺れ）で人手へ＝レビュー詰まり回避。
- **Phase 5｜promote → canonical projection → count**: shadow で誤統合率が許容内のものだけ confirm。
  属性観測層で「1属性＝1採用値（出所付き）」projection、scalar は cache。work/edition/holding/access の4カウント出力。
- **Phase 6｜定常運用（今後の購入）**: 新刊 → バーコード/奥付OCR → raw1行 → fingerprint →
  **既存 index への増分マッチ**（全再構築しない）→ 既存 edition リンク or 新規作成 → holding 所有登録。

---

## 5. マッチング戦略

1. **NDL を"ハブ"にする（最重要判断）**: 4ルート×4ルート総当り（O(n²)・誤統合の温床）をやめ、
   各ソース→NDL 解決（O(n)）に変換。同一 NDL bibid 着地 = 同一 edition。NDL に着地しない
   純オンライン無 ISBN 本のみ、ブロック内で直接 fingerprint 突合に落とす。
2. **Waterfall（強い証拠から）**: (a) ISBN 完全一致 → NDL bibid、(b) 強書誌→NDL クロスウォーク
   (title 正規化+author+publisher+pub_date+page_count)、(c) 無 ISBN 層は TOC fingerprint 主証拠＋独立証拠2本。
3. **ブロッキング**: 正規化タイトル前方一致＋著者で比較対象を絞る（速度）。
4. **独立性ガード**: 同一出版社 TOC 再配信（弁コム×legallib×honto）を `origin_publisher` で判定。
   同 origin = 0.5 証拠 / 異 origin = 1.0 証拠。これが無いと「独立証拠2本」が名目倒れ＝Phase 0 で必ず埋める。

---

## 6. 4ルート個別

| ルート | 鍵 | 戦略 | 注意 |
|---|---|---|---|
| 自所 物理/裁断 | ISBN(バーコード)／古書は奥付OCR | ISBN→NDL 直結。holding 所有 SoT も兼ねる | 裁断は `medium_origin=paper_scan` / `fulltext_access=local_pdf` |
| LION BOLT | 構造化書誌（ISBN 期待） | ISBN/強書誌→NDL | メタ形状を実サンプルで確認 |
| 弁コム | 無 ISBN・TOC100% | TOC fingerprint 主証拠 | legallib と TOC 再配信重複の可能性大 |
| legallib | 無 ISBN・TOC あり | TOC fingerprint 主証拠 | 弁コムとの `origin_publisher` 独立性判定が必須 |

---

## 7. 今すぐ潰す設計バグ（Phase 0/2 チェックリスト・不可逆分のみ）

- [ ] 全観測に `source_provenance_chain`
- [ ] TOC 観測に `origin_publisher` / `redistributor_chain` ＋ `independence_flag`
- [ ] 全観測に `rights_profile`（購読由来メタが serving まで漏れない経路）
- [ ] `medium_origin`(digital/paper_scan) を全観測共通の出所事実に
- [ ] 正規化を disputed 判定の前段に強制
- [ ] 分類の work-rollup は `work_id=confirmed` 後の明示 migration のみ
- [ ] single_authority(NDL 単独)採用はフラグ付き暫定、後続 corroboration で再評価

可逆分（配点・閾値・TTL）はここで決めない。Phase 4 でデータに語らせる。

---

## 8. なぜ4基準で最善か
- **早い**: raw 投入を設計完了を待たず即開始＋NDL ハブで O(n)。
- **正確**: 閾値を proxy でなく本番分布で較正＋独立性ガードで誤統合を構造的に抑止。
- **手戻り少**: 不可逆メタを取得時に捕捉、promote は shadow 実証後＝巻き戻し回避。
- **拡張可**: source_biblio_item にルート追加するだけ、増分マッチで購入処理も同一パイプライン。

---

## 9. 既知の未確定（次工程で解消）
- 親 DD-LITID-001 v0.2 の正確な列名・ゲート名（E1〜E4, fingerprints, gate_*）への厳密マッピングは未実施。
- LION BOLT / legallib の実メタ形状（ISBN 有無・TOC 構造）は実サンプル未確認。
- 上記2点は本計画の前提に影響しうるため、監査所見と合わせて Phase 0 で確定する。
