# pipeline/procedure_flow/ — 手続フロー（段取り本から抽出した構造）

⑥手続の本丸（→ `docs/dd_procedure_design.md` §8）。**手作りしない**。「会社法実務スケジュール」等の
段取り本（専門家が分岐つき段取りを構造化済み＝巨人の肩）の構造を抽出し、機械可読な有向グラフ
（局面 node ＋ 条件付き遷移 edge）として保持する。

- 1 ファイル = 1 手続（業務）。ファイル名は `<procedure_id>.json`。
- **各 node に `source` 必須**（どの本の何ページ／どの条文 由来か）。捏造防止・監査前提。
- 検証/描画: `python scripts/procedure_flow.py <flow.json> --render`。
- `status`: `scaffold_pre_audit`(枠のみ) → `extracted`(本から抽出) → `audited`(owner/GPT 監査済)。

## 育て方（巨人の肩）
1. 段取り本（会社法実務スケジュール 等）を特定（ISBN）。蔵書③にあれば詳細TOCで業務一覧を取得。
2. 各業務の日程表/分岐を本文（自炊PDF/書式本）から抽出 → node＋edge 化（source にページ）。
3. 条文(①/e-Gov)・実務書TOC(③)・裁判所HP と突合（三点測量）。
4. owner/GPT が順序・分岐を監査 → `status: audited`。

`*.example.json` は**構造の雛形（scaffold_pre_audit）**であり、内容は抽出・監査前の placeholder。
権威ある出力ではない。
