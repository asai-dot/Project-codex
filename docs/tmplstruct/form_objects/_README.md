# form_objects/ — 完成した書式オブジェクト（form_object.v1）

DD-FORMOBJ-001 の **S0→S3 を実データで一気通貫**した成果物。各ファイル＝1書式の完成オブジェクト。
生成: `tools/complete_form_object.py`（S2 snapshot → S3 merge → form_uid発番 → form_object）。

## 完成2件（2026-06-11）
| form_object | 書式 | anchor(実toc_node_id) | source | conf | blocks/blanks |
|---|---|---|---|--:|---|
| keiyakukaisho_kaijo_tsuchi | 解除通知書(英文文例) | `…契約解消…_01:toc:029`(p60) | 自炊vision | 0.95 | 10/21 |
| gyomu_seizo_kihon_keiyaku | 製造委託基本契約書(サンプル) | `…業務委託…_01:toc:134`(p216) | 自炊vision | 0.95 | 9(5条)/2 |

両者とも:
- **anchor確定**（ライブ`biblio.toc_nodes`の実 sticky toc_node_id ＋ 印刷頁範囲）
- **canonical content**（自炊600dpi×vision OCR、発明なし）
- **confidence 分解**（source_authority 0.95 × merge 1.0 × quality 1.0 = 0.95。単一源）
- **provenance / content_sha1 / established_at** つき

## このオブジェクトが満たすもの（正着の確認）
- 住所(book+node)が先に確定 → 中身が後 → 安全合成、の順で出来ている。
- form_uid は現状 **暫定決定的ID**（`alo:form:prov:<hash>`、anchor由来でsticky・再現可能）。
  正式 sticky ULID は S5(DB persist)で発番し resolution_log で対応（DB書込み権限＝Mac側）。

## 注記
- 製造委託は第1〜5条をOCL（PDF217-220）。**全条はPDF235付近まで**継続→残条は後続バッチで追記（content_coverageに明記）。
- 会社法務書式集(発起人決定書)は scan旧版×toc第3版で**版不一致のため未完成**（anchor pending）。
- 単一源のため S3 の三点測量は未発火。LIONBOLT(次PJ)等の第2源が入れば agreement/裏取りが効く。
