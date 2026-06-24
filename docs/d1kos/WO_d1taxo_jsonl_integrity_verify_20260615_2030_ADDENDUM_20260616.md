# WO-D1TAXO-002 アデンダム（追加不変条件）— 2026-06-16

- 元WO: `WO_d1taxo_jsonl_integrity_verify_20260615_2030.md`（Box to_worker, file_id 2286536857897）
- 根拠: DDTAXOAUDIT 監査（PASS_WITH_NOTES, GPT-5.5 Pro 2026-06-16）論点4の追加推奨
- 種別: 検証のみ（read-only / DB未投入 / ファイル非改変）。元WOの7項目に**上乗せ**。

## 追加検査項目（8〜14）

8. **source_version 閉鎖性**: labels / relations が `source_version` 単位で閉じている
   （混在バージョン参照が無い）。
9. **relation の scheme/version 一致**: 各 relation の `src` と `dst` が**同一 scheme・同一 source_version**に属する。
10. **parentless term の理由記録**: 親リンクを持たない term（= level3 の 10,823件相当）に
    `reason = parent_is_statute_layer`（L3=statutes 層が親）等の理由が記録されている。
11. **ラベル区別**: `raw_label` と `clean_label` / `search_norm` が区別保持されている
    （正規化で原表記が失われていない）。
12. **enumerator の扱い**: 連番・記号(L4-L11 のナンバリング記号)が除去または分離されているかを検査
    （name へ統合した場合はその旨フラグ）。
13. **term→statute context edge**: term と statute 層を結ぶ context edge/table の有無を検査
    （L4→L3 を skos_broader で張らない代わりの接続が設計どおりか）。
14. **識別子の重複混在**: `scheme_id` / `source_item_key` / `source_version` の重複・混在が無い。

## 完了基準

- 元WO 7項目＋本 8〜14 を加えた全項目で PASS/NG を `VERIFY_..._result.json` に記録。
- NG は該当キー最大50件を添付。read-only 厳守（apply は HOLD 継続）。

## 備考

- removed 929 は番頭側で仕分け済み（`REMOVED929_triage_20260616.md`）。経済法 781 が主因＝box_prior 点描ノイズ。
  本WOは live→terms 変換の実体整合に限定。
