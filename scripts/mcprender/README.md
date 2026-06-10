# mcprender — MCP 安全出力レンダラ（DD-LAWSUBTRANS-001 Phase 5 / §5）

assembler の `resolved_assertions_*.jsonl` / `disputes_*.jsonl` を、MCP/LLM 出口向けに
**断言せず・出典付き・両論併記**でレンダリングする。新たな判断は一切加えない純粋な整形器。

```
python -m scripts.mcprender \
    --resolved out/resolved_assertions_RUN.jsonl \
    --disputes out/disputes_RUN.jsonl \
    [--formal-notes notes.json] --run-id RUN --out out/
```

出力: `mcp_provision_views_<run>.jsonl`（MCP/JSON消費者向け構造化）＋ `.md`（人/LLM表示）
＋ gate 結果付き summary。**DB書込みゼロ。**

## 安全出力契約（DD §5・監査反映）

実証根拠: Stanford RegLab — 汎用LLMの法令幻覚 69–88%、RAG付き商用ツールでも 1/6〜1/3。
→ **単一の確信ある答えを返さない。**

| 区分 | 扱い |
|---|---|
| **形式事実（DD-LAWTIME）** | 平叙でよい（「2020-04-01 改正で条文変更（lawtime: superseded）」）。`--formal-notes` で注入 |
| **実質主張** | 常に**出典＋tier＋確度＋証拠**付きの**候補**。レンダラ自身の声で意味変化を断じない |
| **disputed** | **両論併記**必須。勝者を示唆しない |
| **unknown** | 「未確認」と表示し、根拠には使わない |
| **利用ラベル** | `claim_support_eligible=true` のときのみ「参考提示可」。assembler は付与しないので常に「参考（要確認・断定不可）」 |

これは GPT 議論 §8 の「OK 出力」の実体化:

```
NG: 旧法理は現在も有効です。
OK: 形式的には〇年改正で当該条文が変更されています（lawtime: superseded）。
    立案担当者解説(T2)は「実質変更なし」、裁判例(T3)は「旧解釈は不継続」、
    学説(T4)は「解釈の修正」と述べています。実質的存続については評価が分かれており、
    断定はできません（出典付き候補・要確認）。
```

## gates（DD §5）

| gate | 検証 |
|---|---|
| `gate_no_assertive_output_flag` | 全 view が `assertive_output_allowed=false` |
| `gate_disputed_renders_both_sides` | disputed target は継続側∧変化側の両 stance を ≥2 claim で描画 |
| `gate_no_relied_upon_without_claim_support` | `claim_support_eligible` でない限り「参考提示可」表記を出さない |
| `gate_summary_not_assertive` | safe_summary に断定的禁止フレーズ（「旧法理は現在も有効です」等）を含まない |
| `gate_every_claim_attributed` | 各 claim 行に出典 source ＋ stance がある |

## パイプライン位置

```
lawdelta(条文差分) ┐
drafterintent(T2) ─┤→ assembler(dispute形成) → mcprender(両論併記・断言禁止) → MCP/LLM 出口
casetreatment(T3/4)┘
```

mcprender は assembler が既に安全化した構造（disputed・claim_support false・counter）を
**表示するだけ**。判断の安全性は上流の gate で担保され、本層は「断言しない形」を保証する最後の関所。

## 制約

- 表示ラベルは日本語固定（MCP/UI 用）。多言語化は別。
- 形式注記（formal_note）は呼び出し側が lawtime resolved view から与える前提（本層は lawtime を引かない）。
- production の MCP サーバ統合（実 view 接続・claim_support 導出）は DD §7 の通り HOLD。
