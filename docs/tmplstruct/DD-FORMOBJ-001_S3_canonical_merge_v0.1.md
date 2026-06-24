# DD-FORMOBJ-001 S3: canonical合成 仕様 v0.1

> gate: 設計＋参照実装のみ。DB非書込み。実装: `tools/form_canonical_merge.py`（自己テスト9/9 PASS）。
> 役割: 同一 `form_uid` の複数源 snapshot（S2出力）→ 1つの canonical form_object。

## 1. 入出力
- 入力: `Snapshot[]`（源別。各 `source_system + blocks[]`）
- 出力: `Canonical{ canonical_source, blocks, blanks_total, sources_used, agreement, discrepancies, ocr_error_classes, corrections, confidence }`

## 2. 基底選択（源優先 ＋ 粒度ガード）
1. **粒度ガード**: 最富源のblock数の **20%未満**しか持たない源は基底になれない（スタブ源が詳細源を潰すのを防止。DD-TOCATTACH §5準用）。
2. 残った源から **源優先(D-F1)** が最高のものを基底に。
   優先: `native_docx(1.0) > jisui_vision_ocr(0.95) > lionbolt(0.85) > bencom(0.80) > legallib(0.75) > codex_ocr(0.60)`
   - 例(テスト4): native_docxが1blockのスタブ → ガード落ち → 基底=自炊vision(10block)。

## 3. crosswalk（block単位の三点測量）
- block key = `type + no + (title or norm_title(text先頭))`。
- 基底の各blockに対し他源の同keyを探し **agreement**（裏取り源リスト）を記録。
- **合成で発明しない**: canonicalのblockは**基底のものだけ**。他源は (a)裏取り (b)誤字訂正 (c)頁補完 のみ寄与。
- 他源にあって基底に無いblockは **discrepancies(review)** に出すだけ（自動追加しない＝`gate_no_node_invention_in_merge`）。
  - 例(テスト5): 他源の「第4条」は discrepancies へ。canonicalには入れない。

## 4. 品質オーバーレイ（確定誤謬クラス）
- 基底block textを `ERROR_CLASSES`（廷→延 等・語単位）で走査。
  - 検出 → `text_corrected` を併置（生textは不変）、`quality_verdict=error_confirmed`、`ocr_error_classes` に記録。
  - 他源の対応blockが正綴りなら `corroborated_by_source=true`（裏取り訂正）。
- 正しい源が基底なら誤字0（例: lionbolt基底はテスト3で error 0）。

## 5. confidence 分解
```
final = source_authority(基底) × merge × quality_adjustment
  merge: 単一源=1.0 / 多源で裏取り有&discrepancy無=1.0 / discrepancy有=0.8 / 裏取り無=0.9
  quality_adjustment: 未訂正のerror_confirmedあり=0.7 / それ以外=1.0
```
- 例: 自炊vision単独 = 0.95×1.0×1.0 = **0.95**。誤字基底のみ = ×0.7。

## 6. 出力の使われ方
- `agreement` 多 → 高信頼（D-6の三点測量と同型）。
- `discrepancies` / `error_confirmed(未裏取り)` → review/corrected snapshotキューへ。
- canonicalは `confidence.final` 付きで永続化（S5）。源追加時は再合成で安全に更新（基底が変われば crosswalk再計算）。

## 7. S0→S3 通し（閉じた設計）
| S | 成果物 |
|---|---|
| S0 | DD-FORMOBJ-001（定義・form_uid・anchor・gate） |
| S1 | `form_address_resolver.py`（式→toc_node・自己テスト7/7） |
| S2 | `form_snapshot.v1`（源別出力標準・参照3本） |
| S3 | `form_canonical_merge.py`（合成・自己テスト9/9） |

→ 「源が増えても、発明せず・誤りは層で持ち・信頼度つきで安全に合成」できる状態。
残りは S4(三点測量検証=実装は本ロジックのagreementで充足) / S5(永続化=apply権限・Mac側)。
