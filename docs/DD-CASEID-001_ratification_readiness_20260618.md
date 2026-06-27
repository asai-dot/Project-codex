# DD-CASEID-001 昇格判断パッケージ (Ratification Readiness)

- date: 2026-06-18 JST
- author: Claude (Project-codex セッション)
- status: **read-only 判断補助文書**。本書は DD-CASEID-001 を `_accepted_v1.0` に昇格させるための**オーナー判断材料の集約**であり、それ自体は承認でも実装GOでもない。
- 対象DD: `DD-CASEID-001 — 判例ID確定システム candidate v0.1`（Box 2266457039407、起票 2026-06-04）
- 下位実装仕様: `31b_case_id_resolution_flow.md`（Box 2264249368602）/ `31c_case_number_norm_spec` / `31d_forum_code_registry_spec`
- 親: `31_case_layer.md`(SPEC-02 v1.4) / `35_link_layer.md`

> なぜ今これか: DD-CASEID-001 は「2つのメタ（NII-TTL / D1KOS）× 個別データ（D1 / LIC）」を1 case_keyに噛み合わせる**中核設計**でありながら、6/4以降 `owner_approval=pending` のまま凍結されている。これが判例オブジェクトのクリティカルパス最上流（G1）。最小の労力（オーナー1判断）で下流（L-SR/L-RV/canonical昇格）を解放する。

---

## 1. このDDが確定させること（要旨）

| 論点 | DD-CASEID-001の決定 |
|---|---|
| ID anchor | firm **`case_key`(ULID, 採番後不変)**。事務所IDの真のanchor |
| 自然キー vs ID確定 | 「判例の**特定**(自然キー forum_code+判決日+case_number_norm)」と「事務所の**ID確定**(名寄せ・採番)」は**別レイヤ**（2026-06-04 オーナー確定の前提） |
| canonical_uri | confirmed時のみ自然キー値、不能時は provisional `alo:case:jp:_prov:{case_key}` |
| 機関コード | court_code → **forum_code**(裁判所＋審判/審査会/ADR/仲裁/行政庁) へ一般化 |
| 着地層 | 全入力は **`case_observation`**(源別生レコード, content_grade付)へ。名寄せは 決定的自然キー→強外部ID→fuzzy→人手 の固定順、全決定を`resolution_log`へ |
| 連鎖 | 審級・答申↔判決は **merge禁止**、`alo_edges`(relative_resolved / origin_decision)でlink |

→ これが確定すると、L-SR(source-record候補)・L-RV(人手レビュー)・NII/D1/LIC名寄せの成果が **canonical case へ着地する受け皿の体系**が決まる。

---

## 2. 検証ステータス（昇格3条件のうち何が済んで何が残るか）

DD-CASEID-001 §4 は self-accept を禁じ、昇格に3条件を課している。現状：

| 条件 | 状態 | 根拠 |
|---|---|---|
| deterministic_self_verification | ✅ **done** | case_number_norm解析率 NII 100.00%(65,853/65,855) / D1 99.94%(68,099/68,141)、**NII∩D1 norm一致 12,661**(dedup収束を実証)、forum未マップ0で123コード、fixture pass |
| independent_meaning_audit (GPT Pro) | ✅ **PASS_WITH_NOTES**（2026-06-19） | gate=DDCASEID。blocking must_fix無し→design accept可。accept-notes 5点付き。詳細: `audit/DDCASEID_audit_result_reflect_20260618.md` / `audit/...DDCASEID_RESULT.md`(Box 2294753110991) |
| owner_approval (浅井 ratify) | ⏳ **ratify待ち** | ← 監査通過。残るはオーナーの ratify のみ |

→ 机上検証＋意味監査は**通った**。残るは**オーナーの ratify 1点**（accept-notes 5点 ＋ reconcile枠組み込み）。

---

## 3. 昇格前に片付けるべき reconcile / 未決（DD §5）

ratify を「条件付き」にできるよう、未決を分類した：

| 項目 | 種別 | 推奨処理 |
|---|---|---|
| `DD-CASE-001`(cases母型)との関係整理 | **昇格ブロッカー候補** | 確定フローが母型の上に乗る／重複排除を1メモで確定（シーケンス S2）。**accept条件に含める** |
| accepted DD正本の所在を登録簿(DESIGN-01)と整合 | 軽微 | accept時に登録簿へ1行追加で解消 |
| 事件符号→display romaji表 / forum支部162種 | **下位DD送り**(別DD-CASEID-002) | 本DDのacceptをブロックしない |
| 受任案件(jufu)judgment取込境界 / 明治期旧法機関 | 下位DD送り | 同上 |

→ **唯一の実質ブロッカーは DD-CASE-001 reconcile** のみ。他は下位DD or 事務処理。

---

## 4. オーナー判断チェックリスト（1枚）

浅井さんが以下を確認できれば accept 可能：

```
[x] A. 前提同意: 「特定(自然キー)」と「ID確定(名寄せ・採番)」を別レイヤにする思想で良い  ← 2026-06-18 OK
[x] B. case_key(ULID不変)を事務所IDのanchorにすることに同意                          ← 2026-06-18 OK
[x] C. court_code → forum_code 一般化（準司法・ADR・行政庁を収容）に同意              ← 2026-06-18 OK
[x] D. DD-CASE-001(cases母型)との重複排除メモ(S2)を accept条件に含めることに同意       ← 2026-06-18 OK
[x] E. independent_meaning_audit(GPT Pro) → **accept前に監査を回す**を指定           ← 2026-06-18 決定
[ ] F. 昇格の意味の確認:
        accept = 「設計確定(_accepted_v1.0)」であって、
        DDL/backfill/canonical mint の実装GOではない（実装は別gate G2）
```

### オーナー決定記録（2026-06-18）
- **A–D: 同意済み。**
- **E: accept前に GPT Pro 独立意味監査を回す**（条件付きacceptではなく、監査通過を accept の前提にする）。
- → よって昇格シーケンスは: **GPT Pro意味監査(S1.5) → 通過 → DD-CASE-001 reconcile(S2) → `_accepted_v1.0` 昇格**。
- 監査依頼: `docs/audit/20260618_DD-CASEID-001_meaning_audit_REQUEST.md`（Box `to_gpt` へ投函済／投函予定）。

---

## 5. ratify した場合に解放されるもの / されないもの

**解放される（design確定として）:**
- L-SR/L-RV の source-record成果を将来 canonical case へ落とす**体系の確定**（case_key/forum_code/identity_status/case_observation）
- 品質ゲート9種（orphan 0 / 自然キー重複 0 / fingerprint衝突 0 等）を**実装時の合格基準**として固定
- 下位DD（CASEID-002 符号正規化等）の着手根拠

**解放されない（HOLD継続）:**
- production/staging DB write、DDL、`alo_forum_registry`/`case_observation`の実テーブル作成
- canonical case 行の mint、`alo_edges` write、`reviewed=true`、claim_support
- → これらは **G2 production-readiness gate** で別途審査（シーケンス S7）

---

## 6. 推奨アクション

1. 本パッケージ §4 チェックリストをオーナーが確認。
2. A–D 同意 + E 指定で **条件付き accept**（条件 = DD-CASE-001 reconcile(S2) と GPT意味監査）。
3. accept後、DD-CASEID-001 を `_accepted_v1.0_with_notes` として Box DD正本へ昇格（正式経路）＋ 登録簿(DESIGN-01)へ登録。
4. 並行して S3(SILVER) / S6(L-DL残57k) を進め、canonical mint は G2 まで HOLD維持。

> 注: 本書は repo内read-only判断材料。実際の `_accepted_v1.0` 昇格（Box DD正本の改版）と GPT監査依頼の to_gpt 投入は、オーナー判断のもとで正式経路に載せる。本セッションからは一方的に Box を改変しない。
