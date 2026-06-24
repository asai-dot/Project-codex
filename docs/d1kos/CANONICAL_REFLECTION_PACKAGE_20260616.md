# DD-D1TAXO 精度検収 — 正本反映パッケージ（番頭独立検証）2026-06-16

> 監査 DDTAXOAUDIT（PASS_WITH_NOTES）論点#5「正本反映経路」対応。
> 規律: PR #22 = **evidence**、Box/DD/_AUDIT_LEDGER = **SoT**。Box正本(90_design_decisions /
> _AUDIT_LEDGER / acceptance package)への append は **single-writer（owner / GPTお目付け経由）**。
> 本ファイルは番頭が用意する**貼り付け用ブロック**。SoTへの実マージは established writer が行う。

## 参照（GitHub evidence）

- repo: `asai-dot/Project-codex`  /  PR **#22**  /  branch `claude/d1-case-law-taxonomy-8pf3d4`
- head commit: `df4d88c092796cb0980ff9ff2ed7f0a762735a43`
- 監査結果(SoT): Box from_gpt `20260615_d1taxo_accuracy_thread_DDTAXOAUDIT_RESULT.md`（file_id 2287180763230）= `DDTAXOAUDIT_PASS_WITH_NOTES`

### ファイル一覧（sha256 先頭16）

| file | sha256[:16] | role |
|---|---|---|
| BASELINE_d1kos_20260525.md | 401f9790456b0bfd | 検収基準点（①判例側） |
| ACCURACY_CHECK_DD-D1TAXO-001_A_internal.md | 2b586bea20c59120 | A 内部整合(全件green) |
| ACCURACY_SAMPLE_CHECK_DD-D1TAXO-001_105.md | 87f9ebeecb5a0813 | B 105件(spot_check_no_obvious_anomaly) |
| ACCURACY_SAMPLE_CHECK_DD-D1TAXO-001_B_expansion_20260616.md | 160d90b1cea6d794 | B補強(巨大枝/深層/709/改名候補) |
| REMOVED929_triage_20260616.md | 195818b055ab6978 | removed-929仕分け(P-8 RESOLVED) |
| DDTAXOAUDIT_RESULT_reflection_20260616.md | 361689706ca8f5d8 | 監査反映メモ |
| 20260615_d1taxo_accuracy_thread_DDTAXOAUDIT_REQUEST.md | b133df9775ed0b89 | 監査依頼 |
| WO_d1taxo_jsonl_integrity_verify_20260615_2030.md | bbd263820fe62dd1 | C WO(7項目) |
| WO_..._ADDENDUM_20260616.md | d7e2851fc126d96c | C WO追加(8-14項目) |

## ブロック1: acceptance package へ追記する `independent_verification_ref`

```yaml
independent_verification_ref:
  by: 番頭（Claude Head / Project-codex）
  date_jst: 2026-06-16
  audit: DDTAXOAUDIT_PASS_WITH_NOTES (from_gpt 2287180763230)
  github: { repo: asai-dot/Project-codex, pr: 22, commit: df4d88c092796cb0980ff9ff2ed7f0a762735a43 }
  layers:
    A_internal_integrity: all_green (55,074件, key重複0/orphan0/level0/cycle0/NFC0, 変換件数再計算一致)
    B_visual: spot_check_no_obvious_anomaly (105件 + 補強47件)  # sanity であり全件精度保証ではない
    removed_929:
      status: closed
      # 内訳は2軸（クラス×法編）。単純加算ではない:
      by_class: { absent_from_live: 916, present_in_live(改名移動候補): 13 }   # 合計929
      by_root_top: { 経済法: 781, 商法: 69, 債権法Ⅱ: 36, 他: 43 }              # 合計929(別軸)
      closure_logic: >
        929 = absent916 + present13。経済法781は法編軸の内数で、その776がabsent916に含まれる(5はpresent13側)。
        recall残差の説明 = absent群=box_prior(判例trunk)点描ノイズ ＋ 経済法はD1民事法セレクションの掲載スコープ仕様(P-8 RESOLVED)。
        民事コア法編のremovedはほぼ0。よってlive取りこぼしではない。
  pending:
    - C_jsonl_byte_integrity: WO-D1TAXO-002(+addendum) ワーカー返り待ち
  apply_gate: HOLD  # apply/canonical化は別ゲート・owner ratify後
```

## ブロック2: _AUDIT_LEDGER エントリ（追記用）

```json
{
  "request_id": "20260615_d1taxo_accuracy_thread_DDTAXOAUDIT",
  "result_filename": "20260615_d1taxo_accuracy_thread_DDTAXOAUDIT_RESULT.md",
  "result_file_id": "2287180763230",
  "result_canonical_note": "参照先は file_id 2287180763230 を正本に一本化（補正版があれば file_id で差し替え）",
  "result_label": "DDTAXOAUDIT_PASS_WITH_NOTES",
  "next_action_type": "strengthen_sampling_and_reflection_flow",
  "loop_state": "returned_reflected",
  "reflected": true,
  "pr_number": 22,
  "commit_hash": "df4d88c092796cb0980ff9ff2ed7f0a762735a43",
  "role": "independent_verification_evidence",
  "blocking_before_ratify": ["C_jsonl_byte_integrity_pending", "owner_ratify_for_apply"],
  "owner_digest_5line": "A全件green/B spot-check弱め記録/removed929=box_prior点描+経済法スコープでクローズ(P-8)/C WO返り待ち/apply HOLD"
}
```

## ブロック3: 90_design_decisions へ append（**owner ratify 後のみ**）

```
> DD-20260616-DDT-A1: D1-Law民事法セレクション体系目次(55,074)の精度検収 = A内部整合all-green +
>   B目視no-obvious-anomaly + removed929クローズ。methodology PASS_WITH_NOTES(DDTAXOAUDIT)。
>   apply/canonical化はC byte検査返り＋owner ratify後の別ゲート。evidence=PR#22@df4d88c。
> DD-20260616-DDT-A2: 経済法removed781はD1民事法セレクションの掲載スコープ仕様（個別法令非展開）。
>   契約変更しないため対応不要(P-8 RESOLVED)。recall97.29%残差はこれで完全説明。
```

## 残ゲート

1. C: WO-D1TAXO-002(+addendum) のワーカー VERIFY 返り → from_worker / 検収メモ統合
2. 上記ブロック1-3 を established writer が SoT へマージ（owner / GPT経由）
3. apply/canonical化 は owner ratify 後の別ゲート（現 HOLD）
