# DDJOIN v0.1 監査 (DDJOIN_MODIFY_REQUIRED) → v0.2 実装で対応

- 監査: `to_gpt/20260610_legallibjoin_v0.1_DDJOIN_REQUEST.md` (file 2277021246691)
  → GPT 判定 **`DDJOIN_MODIFY_REQUIRED`** (RESULT は
  `from_gpt/20260610_legallibjoin_v0.1_DDJOIN_RESULT.md` 想定)
- PR #5 / branch `claude/legallib-integration-design-Jgrtf`

## 裁定と対応

### F2 → 採用案 (A): `auto_accept ⇒ 有効ISBN必須` を契約化
- `validate_resolver.py`: auto_accept で **ISBN 空は hard error**（「対象なしは
  bucket=defer_new で表現せよ」と誘導）、不正形式も hard error。
- 接合本体は従来どおり空/不正 ISBN を `blocked_bad_isbn` で防御（多層）。

### F3 → 採用案 (B)+(A): simple-only ゲートに**構造ガード**を追加
- 現行は `toc_status=="simple"` 単独依存で、bencom の 104ノード・3階層・ページ付き
  (実態リッチ) が `simple` ラベルのため上書き対象に落ちていた (実データ確認)。
- `legallib_join_policy.py`: `is_structurally_rich()` 追加。`depth>1` / `parent_toc_node_id`
  あり / `toc_path_id` に階層区切り / `page_start|p` あり のいずれかなら、`simple`
  ラベルでも **保護** (`route_human_review`)。`protection_reason()` が
  `structurally_rich` を返す。(C) bencom 全保護は過剰なので不採用。
- 効果: 上書き候補が減りレビューが増えるが、**安全側に倒す** (GPT 容認のトレードオフ)。
  上流のラベル是正 (A) は供給側 (openbd/bencom 取り込み) の別タスクとして残す。

### 第3論点 → provenance 付与 + ambiguous の identity review
- `legallib_to_canonical.py`: `CONVERTER_VERSION="1.1.0"`。変換ノードに
  `legallib_book_id` / `converter_version` を刻む。
- `legallib_join_dryrun.py`: 各判定/バンドルに `provenance`
  (`legallib_book_id` / `resolver_confidence` / `converter_version` /
  `source_sha256` / old・new titles sha256) を付与 → 後段の監査・再現・old/new 追跡が可能に。
- `blocked_ambiguous_*` は「書かない」だけでなく **`identity_review.jsonl`** に流す
  (identity 解決キュー)。report.md に件数も表示。

## テスト
- 追加: `test_provenance_stamp` / `test_structural_guard` / `test_identity_review_queue`
  (legallib) / F2 hard-error & 重複warning (handoff)。
- 全 **34 + 96 + 45 = 175 checks 緑**。

## 残 (owner/別タスク)
- F3(A) 上流ラベル是正 (供給側 status 付与の修正)。
- 本適用前に **F1+v0.2 後の converter で全数ドライラン再実行** (overwrites_bundle 作り直し)。
- DDJOIN v0.2 を差分再監査に回すか owner ratify するかは要判断。
