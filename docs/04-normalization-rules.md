# 04 — Normalization & Merge Policy

## Purpose

This document defines the **deterministic** business rules used to normalize candidate data, identify duplicate candidate records, merge information across sources, resolve conflicts, and calculate confidence.

These rules are the core business logic of the transformation engine and the specification the implementation is written against. Every transformation must be **deterministic, explainable, and reproducible** — the same inputs always yield the same output, with no implementation-dependent judgment calls.

---

## Normalization Policy

Before any records are merged, extracted values are converted into a common canonical format.

| Field | Normalization Rule | Canonical form |
|---|---|---|
| Email | Trim whitespace, lowercase | `dakshin@example.com` |
| Phone | Parse to E.164 | `+14155550123` |
| Country | Map to ISO-3166 alpha-2 | `US`, `IN` |
| Dates | Coerce to `YYYY-MM` | `2023-07` |
| Skill names | Canonical dictionary lookup + alias removal | `JavaScript` (not `JS`) |
| Company names | Trim + normalize casing | `Google` |
| Person names | Trim + collapse internal whitespace | `Dakshin R` |

**Unparseable values are stored as `null` and recorded in provenance.** Missing values are never fabricated.

---

## Candidate Matching Policy

Records are matched into a single candidate entity using this priority order:

| Priority | Match Key | Match Confidence |
|---|---|---|
| 1 | Exact email | Very High |
| 2 | LinkedIn URL | Very High |
| 3 | GitHub URL | Very High |
| 4 | Normalized phone | High |
| 5 | Normalized name + current employer | Medium |
| 6 | Normalized name + location | Low |

**Rules:**

- Matching uses the **highest available reliable key**; lower keys apply only when stronger identifiers are absent.
- **Phone alone never produces a high-confidence merge if names strongly disagree** (shared, office, or recycled numbers).
- A merge made on a low-priority key (5–6) is recorded in provenance as a *weak match* and lowers the affected fields' confidence.

---

## Merge Policy

Once records are identified as the same candidate, their information is merged. The merge **preserves every available value** from every source before conflict resolution begins — nothing is discarded during merging. Conflict resolution (below) then selects the canonical value from this preserved evidence.

---

## Conflict Resolution Policy

Conflict resolution is **field-specific**, because different sources are authoritative for different data. All precedence lists obey two global rules:

- **Null-skip:** if the highest-priority source's value is `null`/missing, fall through to the next source in the list.
- **Final tiebreak:** if two equally-ranked or non-listed sources still conflict, the winner is chosen by source-priority order; if still tied, by stable source ordering (first-seen wins). This guarantees a deterministic result in every case.

### Contact information (email, phone)

`1. Verified value → 2. Resume → 3. LinkedIn`

> **"Verified" defined:** under the assignment's available sources there is no live verification signal, so *verified* means **ATS-confirmed contact** (the ATS represents recruiter-entered, application-stage data). If no ATS-confirmed value exists, priority starts at Resume. *(Documented assumption — see doc 08.)*

### Employment / experience history

`1. ATS → 2. Resume → 3. LinkedIn`
Reason: the ATS typically holds recruiter-verified application data.

### Skills (accumulate, do not overwrite)

- **Union** skills across all sources.
- **Normalize** each name (canonical dictionary).
- **Deduplicate** by canonical name.
- **Preserve the contributing sources** on each skill.
- **Per-skill confidence:** each skill carries its own confidence, scaled by how many sources contributed it (a skill from 3 sources outranks a skill from 1). This matches the `skills[{name, confidence, sources[]}]` schema.

Example: Resume `Python` + GitHub `Python, Rust` + LinkedIn `Java` → `Python` (3 sources, high), `Rust` (1 source, lower), `Java` (1 source, lower).

### Education

`1. Resume → 2. LinkedIn`
Reason: the resume is usually the most detailed source for education history.

### Personal information (name, location)

Prefer the value with the **highest agreement across sources**; ties broken by the global final-tiebreak rule above.

---

## Confidence Policy

Confidence is calculated **after** conflict resolution and **consumes provenance** (which sources contributed, which won). It is rule-based and reproducible — **not** an ML model.

**Inputs:** source agreement, per-field source reliability, successful normalization, validation status, and number of supporting sources.

**Base scale (per resolved field):**

| Scenario | Confidence |
|---|---|
| Three or more reliable sources agree | 0.98 |
| Two reliable sources agree | 0.85 |
| Single reliable source | 0.70 |
| Single low-reliability source | 0.40 |
| Value derived via weak (priority 5–6) match | apply −0.15 penalty |

**Deterministic resolution rule (so the table always yields one number):**

1. Match the **most specific** scenario that applies (more agreeing sources beats fewer).
2. A disagreeing source does **not** raise confidence; agreement counts only sources sharing the *selected* value.
3. Apply penalties (weak match, failed validation) **after** selecting the base score.
4. Clamp to `[0.0, 1.0]`. If two scenarios tie, the **lower** confidence wins (honest-pessimistic).

`overall_confidence` is the mean of included per-field confidences (deterministic given the same fields).

---

## Provenance Policy

Every canonical field records:

- Source
- Original value
- Selected value
- Selection rule (which precedence / match rule fired)
- Transformation steps applied

This enables complete explainability and auditing — the "why" behind every value is reproducible, never reconstructed after the fact.

---

## Missing Data Policy

The engine never invents information. When data is unavailable:

- Return `null`.
- Record provenance (source absent / unparseable).
- Reduce confidence where appropriate.

**Missing data is always preferred over incorrect data.**

---

## Error Handling Policy

The engine continues processing whenever possible — a single malformed input never fails the run.

| Situation | Action |
|---|---|
| Malformed source | Skip source, continue, report |
| Unsupported field | Ignore field |
| Invalid phone | Store `null` + provenance note |
| Invalid date | Store `null` + provenance note |
| Unknown skill alias | Preserve original value, flag for review |

---

## Design Principles

- Deterministic processing — identical inputs, identical outputs.
- Explainable, rule-driven transformations.
- Single canonical representation.
- Field-specific conflict resolution.
- Extensible rule set (new source = new precedence entry, no redesign).
- No fabricated data.
