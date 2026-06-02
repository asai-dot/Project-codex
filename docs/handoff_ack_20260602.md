# 辞書パイプライン Handoff: 浅井(ack) → Windows CC

> **From**: 浅井 悠太（head） / 経由: claude-code-cloud（Project-codex セッション）
> **To**: claude-code-windows（dict_pipeline owner）
> **Date**: 2026-06-02
> **In response to**: `HANDOFF_TO_MAC_20260513_response.md`（file_id 2228148438556）§7「ack 待ち」
> **Status**: v0.1（承認 + 決定事項 + 実行可能ツール同梱）

---

## 0. 30秒サマリ

- 学陽書房『法令用語辞典 第11次改訂版』(`scheme_id: hourei_yougo_jiten_11`) の **Phase 1.5 以降に着手することを承認する**。
- §7 の手順をそのまま実行してよい。下記 §2 の決定事項を織り込むこと。
- **再現可能な実装を同梱した**（このフォルダに同時アップロード、§3）。自前の有斐閣スクリプトと
  突き合わせ、採用 or 検証に使うこと。二重実装（別方式で別の all_entries.jsonl）は避ける。
- 完了基準は rc=0 ではない。件数・空定義率・重複率を**実数**で報告すること（同梱ツールが出力する）。

---

## 1. 承認（ack）

`HANDOFF_TO_MAC_20260513_response.md` の Phase 1.5 追加方針・索引重複対処・進捗正本（§6 Wave 0 行）を
**承認する**。`term_dict/inventory/dict_inventory.jsonl` への Wave 0 行起票に進んでよい。

---

## 2. 決定事項（指示に織り込め）

1. **メイン入力は `final_hourei_jiten.md`**。raw JSONL からのやり直しはしない（handoff §A3）。
2. **`##` と `###` を見出し語候補**とし、non-entry heading（あ／カナ1字／「1．用語の選定」等の
   番号付き節／凡例・索引等の構造見出し）は正規表現で除外。
3. **本文 p.815-838 由来セクションと index_gemini_pages は staging に流さない**（handoff §4）。
   索引を使うなら別 `scheme_id`（`hourei_yougo_jiten_11_index`）で独立取込。要否は
   **DD-DICT-IMPORT-002** として別途起票（head 判断）。
4. **Phase 2.4（末尾エントリ回収）**は `definition_continues` フラグ不在のため、
   「短い定義 + 次見出しが記号始まりでない」ヒューリスティックで代替（handoff §A2）。
5. **staging** は有斐閣の `generate_staging_v4.py` 相当を流用、`scheme=hourei_yougo_jiten_11`、
   `authority_rank=102`、`scheme_role=jp_legislative_dictionary`。

---

## 3. 同梱ツール（このフォルダに同時アップロード／cloud 製・テスト済）

| ファイル | 役割 | 状態 |
|---|---|---|
| `phase1_5_parse_md.py` | `final_hourei_jiten.md` → `all_entries.jsonl`（決定的・LLM非依存） | 合成 md で 13/13 テスト通過 |
| `cross_reference_web.py` | all_entries × 権威WEBデータ（引用リンク抽出 + 収縮疑い4桁 + 見出し語権威照合・**自動修正なし**） | 同上テストに含む |
| `tests/test_phase1_5.py` | 上記2本のオフライン回帰テスト | 13/13 PASS |

`phase1_5_parse_md.py` は §2 の決定事項1〜4を実装済み。出力は

```
{scheme_id, entry_id, headword, reading, raw_heading, heading_level,
 source_page, definition, flags[]}   # flags: empty_definition / definition_maybe_truncated
```

で、実行末尾に **entries / dropped(index) / empty率 / dup率 / truncated率 / source_page解決率** を出す。
想定 2,603 件に対し ±10% 外なら rc=2（サボり検出）。

実行例:
```bash
python3 phase1_5_parse_md.py final_hourei_jiten.md all_entries.jsonl \
        --scheme hourei_yougo_jiten_11 --expected 2603 --index-from-page 815
python3 cross_reference_web.py all_entries.jsonl xref_layer.jsonl   # 既定オフライン
python3 cross_reference_web.py all_entries.jsonl xref_layer.jsonl --verify-egov  # e-Gov v2 到達確認
```

### ⚠ 実 md で要確認（Windows CC が実ファイルで調整する2定数）

cloud 側は 4.3MB の実 md を手元に展開できないため、以下は**実ファイルで確認・微調整**すること:

- `PAGE_MARKER_RE`: 既定 `<!-- page:NNN -->`。実 md のページ境界マーカ形式に合わせる
  （無い場合 source_page=null → index 除外が効かないため、pages.jsonl 突合で page 付与する経路に切替）。
- `HEADING_RE`: `##`/`###` を見出しとみなす。実 md の heading level（handoff §A3「途中から ## に変わる」）を確認。

→ この2点を直して実 md で走らせ、**実数**（件数・空定義率・重複率）を報告。abstract で完了マークしないこと。

---

## 4. 権威WEBデータ照合（新規レイヤ / cloud 担当）

> **訂正（2026-06-02）**: 本節の初版は `review_queue.json` の P2_era_concat_digits 129件を
> 「令+3桁のOCR連結エラー、129件を修正候補化」と誤って性格づけしていた。**誤り。**
> 129件の大半（>9割）は正規の引用（施行令167 / 政令227号 / 勅令189号 / 組織令127 …）で、
> 検出器が「令」を令和の元号略と誤認して発火しているだけ。本物の誤りは 4桁以上に潰れた
> 少数（令9921=会計令99の2の1 / 令2210=組織令22の10 / 令5710=会計令57の10 / 令991 …）のみ。
> canonical 再評価は **REVIEW_QUEUE_REASSESSMENT_20260602.md**（同フォルダ）を正とする。
> `cross_reference_web.py` はこの訂正に合わせて改修済み（自動修正なし／3桁はフラグしない）。

handoff 計画は md↔pages.jsonl の内部突合まで。これに加え、浅井指示
「2つのOCR辞書 + 権威あるWEBデジタルデータを突き合わせてきれいな法律用語データに」を実装する layer。
**役割は「129件を直す」ではなく以下の3つ**：

- **① 引用リンク候補**: 定義文中の全引用（施行令167条 等）を e-Gov ノードへの【リンク候補】として
  抽出（誤り扱いせず、修正もしない／将来 alo_edges へ）。
- **② 収縮疑い（advisory）**: 令+【4桁以上】のみ「枝番の/中黒の脱落候補」として flag。3桁は
  regex で真偽判定不能のためフラグせず、必要時に e-Gov 照合で確定。自動修正は禁止。
- **③ 見出し語の権威照合**: 法務省 JLT **v19.0**（正典は Box 着地待ち）と見出し語を突合。
  `--jlt-terms` で権威用語リストを渡す。旧 jlt_standard_dict.csv は非権威のため使わない。

権威ソース:
- **e-Gov 法令API Version 2**（JSON, base `https://laws.e-gov.go.jp/api/2`／**事務所標準=v2**）。
  初版が v1 にグラウンドしたのは逸脱、v2 に修正済み。
- **法務省 JLT v19.0**（日本法令外国語訳DB）。取得は hand agent（Windows）経由、Box 着地後に接続。

生データ非改変。照合結果は `xref_layer.jsonl` 別レイヤに出す（全行 advisory）。

---

## 5. 浅井（人間）側のボタン

1. **ack** = 本書（§1）。Phase 1.5 を動かしてよい。※本ファイルは記録。実際の運用承認は浅井の操作。
2. **元PDF共有**（Phase 2.3 ターゲット再OCR用）: `01_全体_法令用語辞典第11次改訂版.pdf`(838p) を
   Box に置くか、問題ページのみ画像化して投函するか。**再OCR不要品質なら 2.3 を飛ばす判断も可**。
   → Windows CC は **Phase 2.3 着手の直前で停止し、PDF 共有可否を要求**すること。
3. **正本の一本化**: 学陽 Phase 1.5+ の正本は本 handoff 計画（有斐閣資産流用＝最短）。
   cloud 側 PR（headless 3ソース照合）は学陽の all_entries.jsonl 生成には使わない。

---

## 6. 次アクション（Windows CC）

1. `dict_inventory.jsonl` に Wave 0 行起票（handoff §6 の JSON）。
2. 同梱 `phase1_5_parse_md.py` の2定数を実 md で確認・調整（§3⚠）。
3. Phase 1.5 実行 → `all_entries.jsonl` 生成（期待 ~2,603）。**件数と review_queue 突合を実数で報告**。
4. `cross_reference_web.py` でOCR引用エラーを flag（§4）。
5. Phase 2.1〜2.8 順次。**2.3 直前で停止し PDF 共有要求**。

## 7. changelog
- v0.1 (2026-06-02): 承認 + 決定事項5点 + 再現可能ツール3本同梱 + 権威WEB照合レイヤ追加。
