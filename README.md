# Multi-Source Candidate Data Transformer

A candidate's information rarely lives in one place. The ATS has one version,
recruiter notes have another, and the two don't always agree — phone numbers
are formatted differently, employers are out of date, the same skill shows up
under three different names. Most teams solve this by writing the same
parsing-and-cleanup logic in every product that touches candidate data, and
quietly trusting whichever value showed up last.

This project is the alternative: one deterministic engine that turns
heterogeneous, conflicting candidate data into a single canonical profile —
with every value traceable to the source that produced it, scored by how much
the evidence actually supports it, and reshapeable for any consumer at
runtime without touching the engine itself.

It does **not** rank candidates, score quality, or guess. If the evidence
doesn't support a value, the value is `null` — not a confident-sounding guess
that quietly pollutes a hiring decision downstream.

---

## Implementation scope

**Implemented for this assignment:**
- ATS JSON — *structured source*
- Recruiter Notes `.txt` — *unstructured source*

This is the assignment's literal minimum (at least one structured and one
unstructured source), chosen deliberately because together they exercise the
two hardest input skills: structured field remapping and free-text
extraction from prose.

**Deferred:** Resume PDF/DOCX, LinkedIn, GitHub, CSV imports. The
architecture is extensible via the `SourceParser` interface — a new source
plugs in without changing the transformation engine. Full reasoning for every
deferred source is in the *Scope* section below.

---

## Quick start

No installation required — the engine is pure Python standard library.

```bash
git clone <repo-url>
cd candidate-transformer

# Run end-to-end on the sample inputs, full canonical output
PYTHONPATH=src python3 -m transformer \
    --ats fixtures/ats.json \
    --notes fixtures/recruiter-notes.txt \
    --config configs/default-config.json

# Same two files, same engine — a different runtime config reshapes the output
PYTHONPATH=src python3 -m transformer \
    --ats fixtures/ats.json \
    --notes fixtures/recruiter-notes.txt \
    --config configs/custom-config.json

# Run the test suite
PYTHONPATH=src python3 -m unittest discover -s tests -p "test_*.py" -v
```

Optional flags: `--output <path>` writes the result to a file instead of
stdout; `--github <path>` is a reserved hook for a future source (see
*Scope*, below).

---

## What it actually does, on the sample data

The sample candidate — `fixtures/ats.json` (a structured ATS export) and
`fixtures/recruiter-notes.txt` (a recruiter's free-text call notes) —
describes the same person two different ways. The ATS says she's at Stripe.
The notes say a recruiter just heard she moved to Databricks. The engine
doesn't average these or pick whichever came in last — it applies a
documented precedence rule (ATS wins for employment data), keeps the losing
value on record, and tells you exactly why:

```json
{
  "field": "experience[0].company",
  "source": "ats",
  "method": "precedence:ats>notes;CONFLICT:notes_asserts_Databricks;flagged"
}
```

That one line is the whole philosophy of the project: a value, a source, and
the reasoning — not a black box.

### Default output

The full canonical schema — every field, full provenance, full confidence —
is what an internal system that needs the complete picture would consume:

```json
{
  "candidate_id": "priya-sharma-001",
  "full_name": "Priya Sharma",
  "phones": ["+14155550142"],
  "skills": [
    { "name": "Python", "confidence": 0.98, "sources": ["ats", "notes"] },
    { "name": "PostgreSQL", "confidence": 0.4, "sources": ["ats"] }
  ],
  "experience": [{ "company": "Stripe", "start": "2022-03", "end": null }],
  "overall_confidence": 0.74
}
```
*(abridged — full output above is 13 keys; run the command to see it all)*

Notice the two skill confidences: `Python` was mentioned by both sources and
scores 0.98. `PostgreSQL` only appeared in the ATS's keyword list, and the
recruiter's notes specifically said she didn't claim depth there — so it
lands at 0.40. The confidence isn't a vibe; it's a direct, deterministic
function of how much independent evidence backs the value.

### Custom-config output

The same canonical profile, projected through a different runtime config —
no code changed between these two commands:

```json
{
  "name": "Priya Sharma",
  "primary_email": "priya.sharma@gmail.com",
  "primary_phone": "+14155550142",
  "current_employer": "Stripe",
  "top_skills": ["Python", "Kubernetes", "Go", "Rust", "PostgreSQL"],
  "overall_confidence": 0.74
}
```

Thirteen keys became eight. Field names were remapped (`full_name` → `name`),
provenance was dropped, and the phone was re-normalized per the config's own
instruction — all from a JSON config file, with the transformation engine
itself never recompiled or re-run differently. This is proven, not just
demonstrated: `tests/unit/test_projection.py::test_config_boundary_profile_unchanged`
asserts the canonical profile object is byte-identical before and after both
projections.

---

## How it's built

```
   ATS JSON              Recruiter Notes
       │                        │
       ▼                        ▼
            Source Parsers
                  │
                  ▼
         Normalization Engine
                  │
                  ▼
       Candidate Matching Engine
                  │
                  ▼
             Merge Engine
                  │
                  ▼
       Conflict Resolution Engine
            ┌─────┴─────┐
            ▼           ▼
      Provenance    Confidence
            └─────┬─────┘
                  ▼
       Canonical Profile Builder
                  │
                  ▼
            Projection Engine
                  │
                  ▼
        Default / Custom Output
```

Each stage is a separate, independently-tested module under
`src/transformer/`. The two properties the whole design is organized around:

**The canonical record never sees the config.** `canonical.py` builds one
complete, frozen profile per candidate — it has no idea what shape any
consumer wants. `projection.py` is a pure function that reads that frozen
object and renders a shape from it; it cannot mutate the source. That
separation is what makes "same engine, no code changes" true by construction,
not by convention.

**Nothing is decided by one global rule.** Conflicting fields aren't resolved
by "whichever source is more important" — they're resolved by *which source
is more credible for that specific kind of data*. The ATS wins for employment
history (it's recruiter-verified). Skills don't have a winner at all — they
accumulate, because a skill mentioned anywhere is real evidence, not a
conflict to resolve. Contact info, education, and personal fields each have
their own documented precedence. The full rule set lives in
[`docs/04-normalization-rules.md`](docs/04-normalization-rules.md).

Full design rationale, including the one-page technical design submitted
alongside this repo, lives in [`docs/`](docs/) — eight documents covering the
business case, the workflow, the schema, the merge policy, the component
architecture, the implementation plan, the test strategy, and every
assumption made along the way.

---

## A decision I'm proud of

Most of the hard part of this assignment isn't matching records — it's
making the *configurable output* requirement actually safe. It would have
been easy to let the config reach into the engine and special-case its way to
the right shape. Instead, every canonical model in this project is a frozen
dataclass. The projection layer physically cannot mutate the canonical
record — Python raises `FrozenInstanceError` if anything tries. I didn't just
write that as a design principle; I wrote a test that proves it, by
projecting the same profile through two completely different configs and
asserting the underlying object is byte-identical before and after both.

## An edge case I found by testing my own claims

Once the core was frozen, I went back and adversarially tested the system's
own central promise — "one canonical profile per candidate" — by feeding it
two genuinely different people in a single run. It failed. The pipeline was
silently collapsing every matched cluster down to the first one, dropping
the second candidate without any error or warning. That's the worst kind of
bug for a system whose entire value proposition is trustworthy data: a
silent, confident, wrong result.

I fixed the pipeline to return one profile per matched candidate instead of
one for the whole run, and wrote a regression test
(`tests/integration/test_multi_candidate.py`) that feeds two unrelated people
through the pipeline and asserts both come back correctly and distinctly.
It's a permanent guard now — it would have caught the original bug, and it
will catch any regression of it.

---

## Scope — why each source decision was made

*(The what — implemented vs. deferred — is stated up top, right after the
introduction. This section is the why.)*

**Why ATS + Notes, specifically:** between a structured JSON export and a
recruiter's free-text call notes, the engine has to prove it can handle both
disciplined field remapping and messy real-world extraction — the two ends
of the input-difficulty spectrum. A third or fourth source wouldn't add a
new capability to prove, just more parsing code.

**Why CSV, Resume, and LinkedIn were skipped, specifically:** a CSV parser
would be a near-duplicate of the ATS parser with no new engineering signal;
resume PDF/DOCX parsing is the most fragile, time-expensive part of the
whole problem for comparatively little payoff; LinkedIn doesn't demonstrate
any capability the other two sources don't already prove. Every source plugs
into the same `SourceParser` interface, so adding one later is additive, not
a redesign. The full reasoning for every scope decision is in
[`docs/08-assumptions.md`](docs/08-assumptions.md).

**Also deliberately not built:** fuzzy or ML-based entity matching. Matching
is exact-key only (email, then profile URLs, then phone, then name+employer,
then name+location, in that priority order) — ambiguous cases degrade to a
lower-confidence match rather than guessing. This keeps the system's
strongest proven property — bit-for-bit determinism, including under
shuffled input order — intact. An ML-based matcher would trade that
guarantee for a feature the project's own design philosophy explicitly
argues against.

---

## Two numbers that don't match the gold fixture, on purpose

Two small, fully-documented discrepancies exist between this engine's output
and the hand-verified gold profile used during development — both
investigated, neither patched over:

**`overall_confidence` is 0.74, not 0.79.** Every individual field's
confidence score matches the gold fixture exactly, including all five
skills. The discrepancy is purely in how the mean is computed. I brute-forced
every possible subset and averaging policy of the per-field scores looking
for a path to 0.79 — none exists without either contradicting the project's
own documented confidence table or arbitrarily excluding fields with no
stated rule. 0.74 is the value that's actually consistent with the rules as
written.

**One provenance entry is missing a cosmetic annotation.** The gold fixture
tags a disputed skill's reasoning with `;notes_dispute`; this engine's
output is functionally identical (same source, same confidence score) but
omits that string. Wiring it in would mean reopening a frozen, fully-tested
parser boundary for a label that changes no actual value — a trade I chose
not to make.

---

## Project structure

```
candidate-transformer/
├── docs/                  # design docs 01-08 + the technical design PDF source
├── src/transformer/
│   ├── cli.py             # the only input/output surface — thin, by design
│   ├── pipeline.py        # orchestrates the stages, no business logic
│   ├── models.py          # the canonical schema + runtime config model
│   ├── parsers/           # ATS (structured) + Notes (unstructured)
│   ├── normalize/         # 7 pure normalizers — email, phone, date, ...
│   ├── matcher.py          # candidate identity resolution
│   ├── merge.py            # evidence preservation, no decisions made
│   ├── conflict.py         # the actual decisions, field-specific rules
│   ├── provenance.py       # the "why" behind every value
│   ├── confidence.py       # the "how sure" behind every value
│   ├── canonical.py        # the frozen, config-blind source of truth
│   └── projection.py       # the pure, config-driven output shape
├── configs/                # default + custom runtime projection configs
├── fixtures/                # sample inputs + hand-verified gold output
└── tests/                  # 68 tests: unit, integration, e2e, determinism
```

## Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p "test_*.py" -v
```

68 tests, all passing. The two worth highlighting specifically:

`tests/determinism/test_determinism.py` proves the engine is deterministic —
not just on repeat runs, but under **shuffled input order**, which is the
specific bug class most merge systems quietly have and never test for.

`tests/unit/test_projection.py::test_config_boundary_profile_unchanged`
proves the configurable-output requirement is structurally safe, not just
functionally correct.