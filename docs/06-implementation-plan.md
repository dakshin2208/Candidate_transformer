# 06 — Implementation Plan

## Purpose

This document translates the design, business rules, and component architecture into an executable engineering plan.

The implementation is organized into small, independent milestones. Each is developed, tested, and validated before the next begins. Milestone order follows **component dependencies**, not perceived complexity.

---

## Scope decision (locked)

The PDF requires **at least one structured and one unstructured source**. The built core is exactly two, chosen to maximize demonstrated capability:

- **ATS JSON** *(structured)* — exercises **field remapping** (the ATS's field names do not match ours; this is the config's `from` key in action).
- **Recruiter Notes `.txt`** *(unstructured)* — exercises **extraction from free text** (no structure; values are found in prose).

This pair is deliberate: ATS proves structured remap, Notes proves free-text extraction — the widest capability contrast for the least code.

**Optional third source (Tier 2, if time permits): GitHub API** — added **not** for breadth but to make the **skills-union merge rule and confidence-from-agreement demonstrable**. With GitHub contributing `Python, Rust, Go` against Notes' `Python`, the demo can show the union rule combining skills *and* confidence rising on `Python` because two independent sources agree. This is a single high-signal demo moment that proves the merge engine, confidence policy, and provenance simultaneously. It is built only after the two-source core is solid (see Milestone 6.5).

**CSV, Resume, and LinkedIn remain deferred** — the parser interface supports them, but they are not built under time pressure. CSV is a near-clone of ATS (proves nothing new); Resume PDF/DOCX parsing is a fragile time sink that risks the demo; LinkedIn adds no capability not already shown. This is the scope discipline the rubric rewards (see doc 08).

---

## Milestone 0 — Gold Profile Fixture *(test-first)*

**Goal:** define the expected canonical output for the sample inputs **before** building, so determinism is measurable from day one.

**Deliverables:** sample ATS JSON + recruiter notes inputs; a hand-written `gold_profile.json` (the correct canonical output); a default config and one custom config with their expected outputs.

**Done when:** the gold profile exists and is reviewed for correctness. Every later milestone is validated against it.

---

## Milestone 1 — Project Foundation

**Goal:** project structure and shared data models.

**Deliverables:** folder structure; dev environment; the **canonical schema** as a typed model; the **config model**; logging utilities; a structured **error model**.

**Done when:** project builds, models compile, a config file loads and validates.

---

## Milestone 2 — Input Layer

**Goal:** accept candidate data from the two core sources behind a pluggable interface.

**Components:** Input Validator, Source Parsers.

**Deliverables:**

- A `SourceParser` **interface** (so new sources plug in without touching the engine — this is what makes deferred sources architecturally real).
- **ATS JSON parser** (structured).
- **Recruiter Notes parser** (free-text extraction).
- Input validation that **reports malformed sources and continues**.

**Done when:** both core sources parse into the common internal model; a garbage/empty source is reported and skipped without crashing the run.

---

## Milestone 3 — Normalization Layer

**Goal:** standardize extracted values into canonical formats.

**Component:** Normalization Engine.

**Deliverables:** email, phone (E.164), date (YYYY-MM), country (ISO-3166 alpha-2), skill (canonical dictionary), name, company normalization.

**Done when:** equivalent values from different sources normalize identically; invalid values become `null` with a provenance note.

---

## Milestone 4 — Candidate Resolution

**Goal:** determine which records belong to the same candidate and combine them.

**Components:** Candidate Matching Engine, Merge Engine.

**Deliverables:** matching by the documented priority keys; merge that **preserves all values** before conflict resolution; duplicate detection.

**Done when:** records merge per the priority rules; every source value survives into the merge for later resolution.

---

## Milestone 5 — Conflict Resolution

**Goal:** one authoritative value per field, with provenance and confidence.

**Components:** Conflict Resolution Engine, Provenance Tracker, Confidence Engine.

**Deliverables:** field-specific precedence (incl. skills-union); provenance generation; deterministic confidence calculation.

**Done when:** every resolved field carries a canonical value **+ provenance + confidence**, matching doc 04's rules.

---

## Milestone 6 — Output Layer *(the twist — build the boundary explicitly)*

**Goal:** produce consumer-specific output **without any engine code change**.

**Components:** Canonical Profile Builder, Output Projection Engine, Output Validator.

**The boundary is a code artifact, not a principle:**

- The engine **always** builds a complete `CanonicalProfile` (every field, full provenance + confidence). It never sees the config.
- A **separate, pure function** `project(canonical_profile, config) → output` is the **only** code the config touches. It selects fields, applies `from` remaps, runs per-field `normalize`, toggles provenance/confidence, and applies `on_missing` ∈ `{null, omit, error}`.
- The projected output is then validated against the requested schema.

**Done when:** the default schema and at least one custom config both produce correct output from the *same* canonical profile with no engine changes; projection honors `on_missing`; output passes validation.

---

## Milestone 6.5 — GitHub Source *(optional stretch)*

This is an optional stretch milestone, defined in full under **Stretch Goals** at the end of this document. It is non-blocking: the core engine is complete without it, and it is cut cleanly if time runs short.

---

## Milestone 7 — End-to-End Pipeline

**Goal:** integrate all stages into one orchestrated pipeline.

**Deliverables:** pipeline orchestration; end-to-end run on sample inputs; structured logging; error reporting; a thin CLI (point at input files + config, print/write JSON).

**Done when:** a complete profile is produced from multiple sources; the run is **deterministic** (output equals the gold profile, byte-stable) for identical inputs.

---

## Milestone 8 — Testing & Validation

**Goal:** verify correctness and robustness (full detail in doc 07).

**Unit:** validation, parsing, normalization, matching, merge, conflict resolution, confidence, projection.
**Integration:** multi-source transform, runtime config (default + custom), malformed input, missing-value handling.
**Edge cases:** duplicate candidates, conflicting employment, invalid phone, unknown skill alias, requested-field-missing under each `on_missing` mode.

**Done when:** all critical business rules are verified and the gold-profile comparison passes.

---

## Development Order

```
M0 Gold Fixture → M1 Foundation → M2 Input → M3 Normalize
→ M4 Resolution → M5 Conflict → M6 Output → M7 Pipeline → M8 Tests

                                   M6 Output ┄┄(if time)┄┄> M6.5 GitHub (optional)
```

Each milestone depends only on the previous one completing. M6.5 is a non-blocking stretch — it hangs off the core and is cut cleanly if time runs short.

### Parallelization (what can actually overlap)

The chain above is the *safe* order, but not everything is strictly sequential. After **M1 (Foundation)** establishes the shared models, three things can proceed in parallel because they have no real dependency on each other:

- **Normalization functions (M3)** are pure (`phone → E.164`, `date → YYYY-MM`, `country → ISO-2`). They take raw strings and can be built and unit-tested with no parser present — so M3 can run alongside M2.
- **The gold fixture (M0)** is hand-written and independent of all code.
- **The config model and schema (M1)** can be finalized while parsers are being written.

What *cannot* be parallelized: matching → merge → conflict → confidence is a true sequential chain (each consumes the previous stage's output), and projection (M6) requires a finished canonical profile. Honest takeaway: the *value transforms* parallelize; the *decision pipeline* does not.

---

## Implementation Principles

- Build one component at a time; test before integration.
- Keep business rules in **one** place (doc 04 → one module), referenced everywhere.
- The config touches **only** the projection function — never the engine.
- Avoid premature optimization.
- Preserve deterministic behavior throughout (validate against the gold profile continuously).
- Every implementation maps directly to a documented component (doc 05).

---

## Completion Criteria

The implementation is complete when:

- Both core sources are processed; deferred sources are cleanly pluggable but unbuilt.
- Candidate records merge correctly.
- Canonical profiles are generated **deterministically** (== gold profile).
- Provenance and confidence are present for every resolved field.
- Runtime projection behaves per config, with no engine changes.
- All documented business rules pass automated tests.
- The system runs end-to-end on the sample inputs and is demo-ready.

---

## Stretch Goals (optional — only if the core is complete)

These are reached **only** if all core milestones (M0–M8) are done. None of them may delay or risk the core engine. If time runs out, each is cut cleanly and listed in the README as *pluggable but unbuilt*.

### Stretch 1 — Lightweight GitHub source

Implement a minimal `GitHubParser` (on the existing `SourceParser` interface — no engine changes) that contributes **only languages and skills**.

**Purpose — not to raise the parser count, but to make three engine behaviors visible:**

- **Skills union** across three sources.
- **Multi-source provenance** on a single field.
- **Confidence increase through source agreement.**

Concretely, the demo can show Notes `Python` + GitHub `Python, Rust, Go` → unioned skills, with `Python` at higher confidence because two independent sources agree, and provenance listing both contributors. One demo moment that exercises the merge engine, confidence policy, and provenance at once.

The core engine is fully complete without this. It demonstrates ambition without the core plan depending on it.

### Stretch 2 — (reserved)

Any further source (CSV, LinkedIn) would follow the same pattern: a new parser on the existing interface plus a precedence/reliability entry. Deliberately **not** planned — they add no capability the core does not already demonstrate.
