# 03 — Technical Design

**Multi-Source Candidate Data Transformer** · One-page design

## Objective

A **deterministic, explainable** engine that ingests candidate data from heterogeneous sources, normalizes it, resolves conflicts by documented rules, and emits **one canonical profile** — with provenance and confidence on every field. The same engine reshapes its output at runtime via config, with **no code changes**. Wrong-but-confident is treated as worse than honestly-empty: unknowns become `null`, never invented.

## Pipeline

```
sources → validate → parse → normalize → identify → merge
       → resolve conflicts → provenance + confidence
       → canonical profile → project (config) → validate output → return
```

Each stage is independent (parsing parallelizable per source). A missing or garbage source is reported and skipped — it never crashes the run.

## Canonical schema & chosen normalized formats

Internal record is the single source of truth. Fixed fields: `candidate_id, full_name, emails[], phones[], location{city,region,country}, links{linkedin,github,portfolio,other[]}, headline, years_experience, skills[{name,confidence,sources[]}], experience[{company,title,start,end,summary}], education[{institution,degree,field,end_year}], provenance[{field,source,method}], overall_confidence`.

| Field | Normalized form |
|---|---|
| phones | **E.164** (`+14155550123`) |
| dates (experience start/end) | **YYYY-MM** |
| country | **ISO-3166 alpha-2** (`US`, `IN`) |
| skills | **canonical skill names** (de-aliased, deduped) |
| emails | lowercased, trimmed |

Unparseable values → `null` + a provenance note, never a guessed value.

## Merge & conflict-resolution policy

**Match keys (in priority order)** to decide records that are the same candidate: `1) exact email · 2) LinkedIn URL · 3) GitHub URL · 4) normalized phone · 5) normalized name + current employer · 6) normalized name + location`. Higher keys are globally unique; lower keys are ambiguous fallbacks. Phone alone is never the sole key for a high-confidence merge when names strongly disagree (shared/recycled numbers).

**Winner selection is field-specific, not one global priority** — because different sources are authoritative for different data:

- **Skills** → **union, then normalize, then dedupe** (accumulate, never overwrite). Resume `Python` + GitHub `Python, Rust` + LinkedIn `Java` → `Python, Rust, Java`.
- **Employment / experience** → ATS > Resume > LinkedIn (ATS is recruiter-verified).
- **Contact (email/phone)** → verified/validated value > Resume > LinkedIn.
- **Education** → Resume > LinkedIn (resume is most detailed).

**Confidence** is rule-based, not ML, and consumes provenance: more agreeing reliable sources → higher score. Three sources agree on `Python` → `0.98`; a single recruiter-note mention of `Rust` → `0.42`. Deterministic and explainable by construction. *(Full tables in doc 04.)*

## Runtime configurable output (the twist)

The canonical record is built once; a **projection layer** then renders the requested shape — no engine changes. Config can: select a field subset, **remap** via a `from` path (`primary_email ← emails[0]`), set per-field `normalize` (e.g. `E164`, `canonical`), toggle `provenance`/`confidence`, and choose `on_missing` ∈ `{null, omit, error}`. The projected output is then validated against the requested schema before return. Clean separation of **canonical record** vs **projection** is what makes this safe.

## Edge cases (handled)

1. **Garbage / malformed source** — caught at validate/parse, reported, skipped; other sources still produce a profile.
2. **Same person, no shared unique ID** — fall to name+employer / name+location keys at lower confidence; provenance records the weak match.
3. **Conflicting current employer** — field precedence (ATS wins) resolves it; losing value retained in provenance, confidence lowered.
4. **Requested field absent under config** — honor `on_missing`: emit `null`, omit the key, or raise — never fabricate.

## Deliberately descoped under time pressure

- **Fuzzy/ML entity resolution** — matching stays exact-key and deterministic; ambiguous matches degrade to lower confidence rather than guessing.
- **Deep resume PDF/DOCX layout parsing** — handle structured + text sources first; rich document parsing is a later add. (System is built so a new source plugs in without redesign.)

## What this buys

Consistent, deterministic, explainable profiles — every value traceable to a source and method, every conflict resolved by a rule we can defend, and output reshaped per consumer without touching the engine.
