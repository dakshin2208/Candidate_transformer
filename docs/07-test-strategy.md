# 07 — Test Strategy

## Purpose

This document defines the testing strategy for the Multi-Source Candidate Data Transformer.

The objective is not only to verify that the system works, but to **prove** that it behaves deterministically, follows the documented business rules, and produces explainable outputs under both normal and edge-case conditions.

Testing runs throughout implementation; each milestone is validated independently before integration.

---

## Testing Principles

- **Deterministic Results** — identical inputs always produce identical outputs.
- **Business Rule Validation** — every rule in `04-normalization-rules.md` is verified.
- **Component Isolation** — every component is unit-tested independently.
- **Integration Confidence** — the complete pipeline is tested end-to-end.
- **Regression Protection** — previously verified behavior never breaks unnoticed.

---

## Test Levels

### 1. Unit Tests

Each component is tested in isolation.

| Component | Example Tests |
|---|---|
| Input Validator | Invalid JSON, missing metadata, unsupported file |
| ATS Parser | Valid field extraction, malformed fields, field remapping |
| Recruiter Notes Parser | Extraction against a fixed notes fixture (see below) |
| Normalization Engine | Email, phone (E.164), date (YYYY-MM), country (ISO-2), skill canonicalization |
| Candidate Matching Engine | Match priority order, weak-match flag, phone-name disagreement guard |
| Merge Engine | All values preserved before conflict resolution |
| Conflict Resolution Engine | Field precedence, null-skip fall-through, deterministic final tiebreak |
| Provenance Tracker | Correct source + method attribution per field |
| Confidence Engine | Agreement scoring, penalty application, tie → lower score |
| Output Projection Engine | Field selection, `from` remap, `normalize`, `on_missing` |
| Output Validator | Schema validation, required-field enforcement |

**Free-text extraction is tested honestly, not as an "accuracy %".** The Recruiter Notes parser is tested against a *fixed* fixture: given exactly `recruiter-notes.txt`, it must extract exactly the known expected values (e.g. this phone, these two skills, this employer). This makes a fuzzy task deterministic and checkable — the test asserts specific extractions, never a vague accuracy threshold.

---

### 2. Integration Tests

Verify interaction across components.

- ATS + Recruiter Notes → canonical profile
- Runtime projection with **default** config
- Runtime projection with **custom** config
- Malformed source alongside a valid secondary source (degrade gracefully)
- Missing optional fields
- Duplicate-candidate merge

Expected outcome: the pipeline produces the expected canonical profile without violating any documented business rule.

---

### 3. End-to-End Tests

The full pipeline runs on realistic sample data.

**Input:** ATS JSON + Recruiter Notes (+ optional GitHub skills source if the stretch is built).
**Output:** canonical profile, default projection, custom projection.

The generated output must match the approved **gold profile** exactly.

---

## Gold Profile Validation

The project uses a hand-written **gold profile** (from Milestone 0) as the reference output. Every end-to-end run compares the generated canonical profile against this approved reference.

Passing this comparison proves: deterministic processing, correct merge behavior, correct conflict resolution, and stable output structure.

Any difference from the gold profile is a **regression** until intentionally re-approved.

---

## Determinism Tests *(highest-signal — proves the core property)*

Asserting determinism is not enough; these tests *demonstrate* it:

1. **Repeat-run stability** — run the pipeline **N times** on identical input; assert **byte-identical** canonical profile, confidence scores, provenance, and projected output every time.
2. **Source-order independence** — feed the **same sources in shuffled order**; assert the output is **still identical**. This is the critical one: it directly proves the final-tiebreak rule (doc 04) works and that no dict/iteration ordering leaks into the result — the single most common determinism bug in merge systems.
3. **No randomness** — no unseeded randomness, no wall-clock, no hash-seed-dependent ordering anywhere in the output path.

If both (1) and (2) pass, determinism is proven, not claimed.

---

## Config Boundary Test *(proves the twist — "same engine, no code changes")*

A dedicated test for the canonical-vs-projection separation:

- Build the canonical profile **once**.
- Project that *same* profile object through **default-config** and **custom-config**.
- Assert both projections are correct **and different**, and that the **canonical profile object is unchanged** after each projection (projection is pure; it never mutates the canonical record).

This test *is* the runtime-config requirement, expressed as an assertion: one engine run, multiple output shapes, zero engine changes.

---

## Edge Case Tests

| Scenario | Expected Behavior |
|---|---|
| Malformed ATS JSON | Skip source, continue processing |
| Empty recruiter notes | Produce partial profile (no crash) |
| Invalid phone number | Store `null` with provenance note |
| Unknown skill alias | Preserve original value, flag for review |
| Duplicate candidates | Merge using documented priority keys |
| Conflicting employer | Resolve by precedence; losing value kept in provenance |
| Requested field missing — `null` | Return `null` |
| Requested field missing — `omit` | Omit the key |
| Requested field missing — `error` | Raise a validation error (configured behavior, not a crash) |

---

## Negative Tests

The system must behave correctly on invalid inputs:

- Corrupted JSON
- Missing required fields
- Unsupported / invalid configuration
- Invalid output schema
- Unknown source type

Expected: fail gracefully, report a meaningful error, and continue processing wherever possible. The only *intended* hard failure is `on_missing: "error"`, which is contract-honoring, not a crash.

---

## Regression Testing

Every completed milestone adds automated tests. Previously passing behavior must keep passing after each change. The gold profile is the primary regression benchmark.

---

## Success Criteria

Testing is complete when:

- Every component passes its unit tests.
- Integration tests validate component interactions.
- The end-to-end pipeline matches the gold profile.
- Determinism tests (repeat-run **and** shuffled-order) pass.
- The config-boundary test passes (same engine, two outputs, canonical untouched).
- Edge cases follow documented business rules.
- No regression is introduced by later changes.

---

## Test Artifacts

```
tests/
├── unit/
├── integration/
├── e2e/
├── determinism/        # repeat-run + shuffled-order tests
├── fixtures/
│   ├── ats.json
│   ├── recruiter-notes.txt
│   ├── gold-profile.json
│   ├── default-config.json
│   └── custom-config.json
└── expected/
```

These artifacts ensure every documented requirement can be verified repeatedly throughout development and demonstration.
