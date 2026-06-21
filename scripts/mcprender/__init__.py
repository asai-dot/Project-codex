"""mcprender — Phase 5 safe-output renderer for DD-LAWSUBTRANS-001 (§5).

Renders the assembler's resolved assertions + disputes for an MCP/LLM boundary
WITHOUT asserting. It never says, in its own voice, that the meaning did or did
not change; it reports what each source said, with tier and evidence, and
presents disputes as both-sides candidates.

Safe-output contract (DD §5, audited; Stanford RegLab 69-88% legal
hallucination => never a single confident answer):
- Formal facts (DD-LAWTIME) may be stated plainly ("amended in YYYY").
- Substantive claims are ALWAYS hedged candidates, with source + tier + evidence.
- disputed targets are rendered both-sides; no winner is implied.
- `unknown` stance / value is shown as "未確認", never as a basis.
- A claim is presented as relied-upon ONLY if claim_support_eligible is true
  (which the assembler never grants) — otherwise it is "参考（要確認）".
"""

RENDERER_VERSION = "mcprender/0.1.0"
