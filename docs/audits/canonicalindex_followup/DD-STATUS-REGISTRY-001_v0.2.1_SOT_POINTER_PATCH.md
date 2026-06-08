# [DRAFT] DD-STATUS-REGISTRY-001 v0.2.1 — §5.3 SoT pointer patch

> 草案。承認後に **新規ファイル**として Box に作成し、浅井先生 ratify で accepted 化する。
> accepted 済 v0.2 本文（Box `2269071863810`）は **inline 改変しない**。本patchは §5.3 の SoT 参照先のみを差し替える narrow patch。

- patch_id: DD-STATUS-REGISTRY-001_v0.2.1_SOT_POINTER_PATCH
- supersedes_section: DD-STATUS-REGISTRY-001 v0.2 §5.3（の SoT 参照のみ）
- scope: §5.3 SoT pointer replacement only
- no lifecycle vocabulary changes
- no transition rule changes
- independent_audit: 20260607_canonicalindex_v0.1_DDINDEXDISPO_RESULT（Box 2270473891101, DDINDEXDISPO_PASS_WITH_NOTES）
- ratify: owner ratify after confirming exact diff
- status: draft（未 ratify）

---

## 置き換え後の §5.3（GPT verdict §2.2 指定文言）

### 5.3 単一の状態 source of truth（SoT） — v0.2.1 patch

per-artifact 状態の SoT は design_decisions.md の Generated Index
（primary: 2172365558197）および sync mirror 90_design_decisions.md
（2187272953323）とする。
ALO_CANONICAL_INDEX_20260605（2266253855296）は historical snapshot / superseded reference
であり、SoT ではない。
本DDは語彙と規約を定義し、Generated Index が各 artifact への適用を持つ。
二重の完全インベントリを作らない。

---

## 根拠（GPT verdict §3）

accepted artifact の §5.3 を **新 version / hotfix patch として参照先だけ補正**することは、
§6-7「certified を mid-trial で inline 改変しない」に抵触しない（変更履歴・version・owner ratify を伴う governance patch のため）。
本 DDINDEXDISPO 監査自体が GPT Pro T2 相当のため、v0.2.1 は大規模再監査ではなく diff 確認 + owner ratify で足りる。
