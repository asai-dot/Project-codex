---
request_id: 20260619_spinebottomup_v0.1_DDPROGRESS
topic: spinebottomup
gate: DDPROGRESS
version: v0.1
source_hash: sha256:a237db55ec8f6f3a5607076f13e9031675f6d7f62ca89e1524471ba4c9bc165c   # procedure_spine.json + procedure_inventory.json + spine_reconcile.py + test_spine_reconcile.py + dd_procedure_design.md
git_commit: d1009037b2dd901dcfc51f244cd249a28e7336f2
git_branch: claude/pipeline-collect-validation-EnNJM
git_pr: https://github.com/asai-dot/Project-codex/pull/15
result_expected_filename: 20260619_spinebottomup_v0.1_DDPROGRESS_RESULT.md
status: dispatched
dispatched_at: 2026-06-19T01:31-07:00   # Box gpt_ometsuke/to_gpt/ へ投函済 (owner 指示「監査回して」)
box_file_id: 2294941156684
box_path: 浅井/claude/handoffs/gpt_ometsuke/to_gpt/20260619_spinebottomup_v0.1_DDPROGRESS_REQUEST.md
---

# 20260619 spinebottomup v0.1 — GPT Pro **方向性確認** REQUEST（spine の bottom-up 化）

- gate: **DDPROGRESS** / topic: spinebottomup / version: v0.1 / 起票: 2026-06-19 / 番頭: web CC
- RESULT 先頭行: `DDPROGRESS_PASS` / `DDPROGRESS_PASS_WITH_NOTES` / `DDPROGRESS_MODIFY_REQUIRED` /
  `DDPROGRESS_FAIL` / `DDPROGRESS_NEED_MORE`
- 種別: **T1 方向性確認**。実装の正否でなく「**この設計の向きで進めてよいか**」を owner/GPT に確認したい。
  spine 本体の改訂は **owner 監査の領分**として未着手。本 REQUEST はその判断材料。

## 0. これは何（一言）
⑥手続の背骨 `procedure_spine.json`（**a-priori に立てた 24 類型**）を、**実データ（bencom 手続本の章構造,
Supabase `biblio.bib_toc`）から bottom-up に組み直した経験的手続インベントリ**で検算した。
結果、**a-priori 24 類型は粗すぎる**ことが実証された。**この発見の受け止め方と次の一手の向き**を確認したい。

## 1. 作った仕組み（GitHub で直接読めます・PR #15 / commit d1009037）
- `pipeline/procedure_inventory.json` — 手続本の章を bottom-up 抽出した**経験的手続インベントリ**。
  各手続に出典（`source_bib_id` / 章）と **`kind`**（`procedure`=手続 / `flow_steps`=局面 / `dimension`=軸）を付与。
- `scripts/spine_reconcile.py`（＋ `tests/test_spine_reconcile.py`, 6 checks green）—
  spine × inventory を**機械照合**し、**過少解像（分割候補）／未マップ実手続／裏付け無し類型**を炙り出す。
- `docs/dd_procedure_design.md` §9 — 発見を記録。

## 2. 実データが出した発見（証拠つき・`spine_reconcile.py` の出力そのまま）
```
spine 24類型 / 実手続 10件
■ 過少解像(分割候補) 1件:
    商事・会社非訟 に 6手続: 合併, 会社分割, 株式交換, 株式移転, 組織変更, 株式交付
■ spine 対応無し(未マップ実手続) 2件: 通常清算, 清算(法人類型別: 医療/社福/NPO/宗教/学校/持分会社/士業法人)
■ 裏付け無し spine 類型 22件 (本がまだ無い)
```
- **F1 過少解像（最大）**: spine「商事・会社非訟」**1 類型に、実データでは 6 手続**（合併/会社分割/
  株式交換/株式移転/組織変更/株式交付）がぶら下がる。a-priori の括りが実務の手続単位より粗い。
- **F2 欠落**: spine は特別清算のみ。**通常清算**が無い。
- **F3 欠けた軸（直交次元）**: 清算は**法人類型別**（株式会社/医療/社福/NPO/宗教/学校/持分会社/士業）で
  枝分かれ。spine は「事件類型」軸しか持たず、**entity-type という直交軸**を欠く。
- **F4 粒度 caveat**: level-1 章 ＝ 手続 とは限らない。組織再編＝章は**手続群**、略式手続＝章は**局面(steps)**。
  **経験的な手続単位は TOC の level に固定できない**（だから `kind` で明示し owner 監査に回す設計にした）。

## 3. 確認してほしい点（方向性）
1. **spine の位置づけ**: a-priori 24 類型は**骨（索引の入口）として残し**、その下に実手続インベントリ（肉）を
   ぶら下げる二層でよいか。それとも **inventory を正本にして spine を派生（roll-up ビュー）に降格**すべきか。
2. **F1 の分割**: 「商事・会社非訟」を実手続（組織再編の各手続）に**分割すべきか**。分割するとして、
   spine の粒度を全類型で「**procedure（手続）単位**」に揃えるべきか（24 → より細かい N へ）。
3. **F3 の軸追加**: 「法人類型」を spine に**直交軸として足す**設計は妥当か。
   （手続 × 法人類型 のマトリクスになる。過剰設計か、必要な構造か。）
4. **F4 の扱い**: 「経験的手続単位は TOC level に固定できない」を `kind`（procedure/flow_steps/dimension）で
   人手前提に裁く現方針でよいか。手続単位の**操作的定義**を置くべきか（置くなら指針を）。
5. **次の一手の向き**: 別途保留中の **`requirement_floor`（記載事項の床, §5）を実点灯**させるには
   「条文各号データの調達（e-Gov から会社法 199 条等の各号を機械取得）」が要る。
   **この調達に進むのが正しい次手か**、それとも先に **spine 分割（F1/F2）を owner 監査で確定**させるべきか、優先順位を。

## 4. 範囲・禁止
- 設計の**向き**のレビュー。spine 本体の改訂・正本化は owner の領分（本 REQUEST では未着手）。
- 実案件・依頼者データ・実シークレットなし。法の authoring（手続・解釈の創作）はしていない（出典＝実書の TOC のみ）。

---
# 添付（読む順）
1. `pipeline/procedure_inventory.json` ← bottom-up の実データ（出典つき）
2. `scripts/spine_reconcile.py` ← 照合ロジック（発見の生成器）
3. `pipeline/procedure_spine.json` ← a-priori の 24 類型（検算の対象）
4. `docs/dd_procedure_design.md` §9 ← 発見の記録
5. `docs/dd_doctrine.md`（巨人の肩 / 三点測量）← 思想の照合アンカー
