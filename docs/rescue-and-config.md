# Phase 0 & 1 runbook — run these ON THE MAC STUDIO

These two phases are **machine-local to the Mac Studio M4 Max** (the launchd
runner). The cloud agent that built Phase 2 cannot perform them: `claude --resume`
only sees the sessions on the machine it runs on, and the Remote Control timeout
is a setting in the Mac's Claude Code install. Run the steps below at the Mac
console or over SSH, then paste results back into the return-leg.

---

## Phase 0 — rescue the stranded 学陽 session (time-sensitive)

The in-progress "学陽 Gemini index 3-source 照合" session went offline on mobile.
Its history is on the Mac's local disk. Recover it on the **same machine**:

```bash
claude --resume                 # session picker; choose the 学陽 index 照合 session
# or, if you know the id:
claude --resume <session-id>
```

### Decision

- **History returns, context intact** → do NOT keep working interactively. First
  **dump the progress to a state file** (below). The known UI behaviour is that
  re-sharing this session to mobile via Remote Control will *not* show history,
  so don't depend on UI continuity. Lock the progress in as an artifact, then run
  everything else through the Phase 2 headless job.
- **History does not return / context broken** → abandon recovery. Rebuild the
  state file from the known reached point (Gemini index acquired; Box Drive sync
  confirmed).

### 0-2 — progress dump (becomes the headless job's input)

Write the reached point as JSON. Minimum contents:

- completed page / heading ranges
- local paths of acquired inputs (Gemini index `.txt`, Paddle index `.txt`, json1 txt)
- unprocessed range

Save to `~/.alo_spool/gakuyo/state.json` **and** replicate to the Box canonical.
The Phase 2 job reads/writes this exact file, so producing it here means the
headless job picks up precisely where the rescued session stopped. A
state-compatible skeleton:

```bash
mkdir -p ~/.alo_spool/gakuyo
cat > ~/.alo_spool/gakuyo/state.json <<'JSON'
{
  "schema": "alo.gakuyo.state/v1",
  "source": "gakuyo",
  "created_at": "<iso>",
  "updated_at": "<iso>",
  "units_total": <N>,
  "done": ["unit-001", "unit-..."],
  "failed": [],
  "last_unit": "unit-..."
}
JSON
```

Then translate the completed page/heading ranges into the `units.txt` manifest +
`done[]` so the job skips them. (If granularity is still undecided, list whatever
the rescued session actually completed as `done` and leave the rest for the job.)

> **【未検証 → report this】** Whether `claude --resume` restores full context or
> only partial varies by environment. Record in the return-leg: did history come
> back, and how completely (full transcript vs. truncated)?

---

## Phase 1 — stop the 15-minute Remote Control timeout (stopgap, ~5s)

The proximate cause of the drop was an undocumented 15-minute timeout. Reduce its
blast radius until Phase 2 fully replaces interactive batches.

```bash
claude config list           # dump the key list first — find the right key
# then enable Remote Control for all sessions (exact key TBD — confirm from the list):
# claude config set <key> true
```

In Claude Code's interactive `/config`, the relevant toggle is
**"Enable Remote Control for all sessions" = true**.

> **【未検証 → report this】** The exact config key name was not fixed head-side.
> Run `claude config list`, identify the Remote-Control / keep-alive key, and
> record the key name plus its **before/after** values in the return-leg.

> This is a stopgap only. Do not return to driving long batches through
> interactive Remote Control — that is what Phase 2 exists to replace.
