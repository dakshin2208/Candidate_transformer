# 08 — Assumptions & Descope

## Purpose

This document records, in one place, every **assumption** the system relies on and every capability **deliberately left out** of scope. The assignment explicitly asks submitters to "note assumptions and anything descoped," and honest scope reasoning is part of the evaluation. Nothing here is hidden in code — if the system assumes something or chooses not to do something, it is stated below with the reason.

---

## Input Assumptions

- **Input data may be incomplete, malformed, or inconsistent.** The engine is built to degrade gracefully rather than expect clean input.
- **The same candidate may appear across multiple sources** under slightly different representations (name spelling, formatting, partial fields).
- **Different sources may disagree** on the value of the same field; conflict is the normal case, not the exception.
- **Source reliability varies by field** — no single source is authoritative for everything. This drives the field-specific precedence in doc 04.
- **Sample inputs are representative** of the shape of real data, but real production data would be noisier; the design accounts for this via null-on-unparseable and graceful skip.

---

## Identity & Matching Assumptions

- **Exact-key matching only.** Candidate identity is resolved by exact/normalized keys (email, profile URLs, normalized phone, name+employer, name+location) in priority order. We assume these keys are sufficient for the sample data.
- **No fuzzy or probabilistic entity resolution.** We do not attempt to match "Jon Smith" to "Jonathan Smith" via similarity scoring. Ambiguous cases degrade to a lower-confidence match rather than guessing. *(Descoped — see below.)*
- **Phone is not a sole high-confidence key.** We assume phone numbers can be shared, recycled, or institutional, so a phone match alone never produces a high-confidence merge when names strongly disagree.

---

## Normalization Assumptions

- **Canonical formats are fixed:** phones → E.164, dates → `YYYY-MM`, country → ISO-3166 alpha-2, skills → canonical dictionary names, emails → lowercased/trimmed.
- **A finite skill dictionary** is assumed for skill canonicalization. Unknown skill aliases are preserved as-is and flagged, not dropped or guessed.
- **Unparseable values become `null`** with a provenance note — never a best-guess substitute. Honestly-empty beats wrong-but-confident.

---

## Conflict, Provenance & Confidence Assumptions

- **"Verified" means ATS-confirmed.** The assignment's sources carry no live verification signal (no real-time email/phone verification). We therefore define a "verified" contact value as one supplied by the ATS, treated as recruiter-entered application data. If no ATS value exists, contact precedence starts at Resume. *(This is the definition from doc 04, stated here explicitly as an assumption.)*
- **Confidence is rule-based, not ML.** Scores are derived deterministically from source agreement, per-field reliability, and validation — not from a trained model. We assume a transparent, explainable score is more valuable here than a tuned-but-opaque one.
- **Confidence values are illustrative and tunable.** The specific numbers (0.98 / 0.85 / 0.70 / 0.40) are a documented, deterministic starting policy, not empirically calibrated thresholds. They are consistent and reproducible, which is what the assignment requires.
- **Provenance is captured at resolution time**, as a by-product of conflict resolution, so the "why" is never reconstructed after the fact.

---

## Output & Config Assumptions

- **The canonical record is the single source of truth;** all output shapes are projections of it. The config never alters the canonical record.
- **The runtime config is trusted input.** We validate its structure, but we assume the caller is an internal system, not an adversary — config is not a security boundary in this exercise.
- **`on_missing: "error"` is an intended hard failure** — a contract-honoring behavior the caller explicitly requested, not a crash. All other failures degrade gracefully.

---

## Deliberately Descoped (under time pressure)

These are **conscious cuts**, not oversights. Each is architected to be addable later without redesign.

| Descoped capability | Why it's safe to cut | How it would be added |
|---|---|---|
| **Fuzzy / ML entity resolution** | Exact-key matching is deterministic and sufficient for the sample data; fuzzy matching adds non-determinism and tuning risk. | A similarity-scoring matcher behind the existing matching interface, gated to low-confidence cases only. |
| **Resume PDF/DOCX deep parsing** | The most fragile, time-consuming source; risks breaking the demo for little added signal. | A new `ResumeParser` on the `SourceParser` interface — no engine change. |
| **CSV & LinkedIn sources** | CSV is a near-clone of the ATS parser (no new capability); LinkedIn shows nothing the core doesn't already demonstrate. | New parsers on the existing interface + a precedence/reliability entry. |
| **Persistence / database** | The assignment is a transformation engine, not a storage service; in-memory processing is sufficient and keeps the run deterministic. | A storage adapter at the output boundary. |
| **Authentication / user management** | Explicitly out of scope per doc 01; this is an internal engine, not a user-facing service. | An API gateway / auth layer in front of the transform endpoint. |
| **Scale beyond thousands of candidates** | The PDF asks for "reasonable on thousands"; the stage-independent pipeline parallelizes per source, which meets that bar. | Batch/stream orchestration around the same pure engine. |

---

## Core Source Scope (built vs. pluggable)

- **Built:** ATS JSON (structured) + Recruiter Notes `.txt` (unstructured) — the minimum the PDF requires, chosen for maximum capability contrast (structured remap vs. free-text extraction).
- **Optional stretch:** GitHub (skills/languages only) — built only if the core is complete, to make skills-union and confidence-from-agreement demonstrable.
- **Pluggable but unbuilt:** CSV, Resume, LinkedIn — supported by the `SourceParser` interface, deliberately not implemented.

This scope is the floor the assignment sets, met deliberately, with the engine (not parser count) carrying the quality.

---

## What "done" assumes

The system is considered complete and demo-ready when the two-source core runs end-to-end, produces a deterministic canonical profile matching the gold fixture, populates provenance and confidence on every field, and reshapes output via at least one custom config with no engine changes. Everything beyond that is explicitly a stretch or a documented descope.
