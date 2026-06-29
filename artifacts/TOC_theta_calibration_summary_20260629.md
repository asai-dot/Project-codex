# TOC agreement θ calibration — pilot results (2026-06-29)

Full pilot: **177 pairs scored** (33 collision / 143 clean / 1 empty), 0 bencom_miss, 0 parse_err.
13 pairs unfetchable (no Box file_id). Source: 190-pair stratified sample (seed=42).

## Key finding: v1.0 metric was under-powered

The v1.0 dry-run computed Jaccard between **all** self TOC nodes (median 78 titles, all
depths) and bencom **depth=1** nodes (median 11 titles). This granularity mismatch
structurally caps Jaccard low — even true matches rarely exceed 0.2.

Restricting self to **depth==1** (v1.1) aligns granularity and makes the metric
strongly discriminative between clean and collision strata:

| metric | clean median | collision median | clean ≥0.5 | collision ≥0.5 |
|--------|-------------|------------------|-----------|----------------|
| v1.0 Jaccard(self_all, bencom_d1) | 0.074 | 0.022 | 9/143 | 2/33 |
| **v1.1 Jaccard(self_d1, bencom_d1)** | 0.500 | 0.109 | 72/143 | 7/32 |
| v1.2 Containment ∩/min | 0.750 | 0.357 | 104/143 | 13/33 |

## θ candidate thresholds (v1.1) — NOT FROZEN

Per design, θ freeze requires ≥2 human reviewers. These are candidates only:

- **θ_high ≈ 0.5**: clean 72/143 (50%) above vs collision 7/32 (22%). Strong-match band.
- **θ_low ≈ 0.1**: below this, agreement is near-noise; needs independent evidence.
- **0.1 ≤ x < 0.5**: adjudication band — route to human / second signal.

## Recommendation

1. Adopt **v1.1 (self depth==1 filter)** as the metric before any θ freeze. The depth
   filter is a one-line change and is the single biggest quality lever found here.
2. Re-run the dry-run TSV under v1.1, then convene ≥2 reviewers on the 0.1–0.5 band.
3. `TOC_metric_comparison_pilot_20260629.tsv` has all three metrics per pair for review.
4. No θ frozen, no DB write, no projection — observation artifact only.
