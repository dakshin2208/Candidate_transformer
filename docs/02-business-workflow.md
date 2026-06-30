# 02 — Business Workflow

## Purpose

This document describes the end-to-end business workflow of transforming fragmented candidate information into a single canonical candidate profile. It focuses on **what happens** during the transformation process, not **how** the system is implemented.

The workflow establishes the sequence of business operations that every candidate record follows before becoming available for downstream hiring systems.

---

## End-to-End Workflow

```
Candidate Data Sources
        │
        ▼
Collect Candidate Data
        │
        ▼
Validate Input
        │
        ▼
Parse Source Data
        │
        ▼
Normalize Data
        │
        ▼
Identify Candidate Records
        │
        ▼
Merge Candidate Information
        │
        ▼
Resolve Conflicts
        │
        ▼
Record Provenance
        │
        ▼
Calculate Confidence
        │
        ▼
Generate Canonical Profile
        │
        ▼
Apply Output Configuration
        │
        ▼
Validate Final Output
        │
        ▼
Return Canonical Candidate Profile
```

---

## Workflow Description

### Step 1 — Collect Candidate Data

The transformation process begins when candidate information is received from one or more data sources. These sources may include Applicant Tracking Systems (ATS), recruiter CSV exports, resumes, LinkedIn profiles, GitHub profiles, or recruiter notes.

Each source represents only a partial view of the candidate and may contain overlapping or conflicting information.

---

### Step 2 — Validate Input

Before processing begins, the incoming data is validated to ensure it can be processed safely.

Validation checks include:

- Supported file or payload format.
- Required metadata.
- Basic structural integrity.
- Detection of malformed or unreadable inputs.

Invalid inputs are reported without interrupting the processing of other valid sources. A single missing or garbage source must never crash the run.

---

### Step 3 — Parse Source Data

Each source is parsed into a common internal representation.

The objective of this step is only to extract available information from each source. No normalization or conflict resolution occurs here.

---

### Step 4 — Normalize Data

Extracted values are converted into standardized formats.

Examples include:

- Phone numbers
- Email addresses
- Dates
- Country codes
- Skill names
- Company names

Normalization ensures equivalent values share a single representation regardless of the original source format.

---

### Step 5 — Identify Candidate Records

The system determines which incoming records belong to the same candidate, since the same person may appear across several sources under slightly different representations.

Candidate identification associates information from different sources into a single candidate entity using available identifying attributes — for example a shared email, a normalized name combined with current employer, or matching profile URLs (LinkedIn / GitHub). *(The exact match keys and their priority are defined in doc 05.)*

---

### Step 6 — Merge Candidate Information

Once records are associated with the same candidate, their information is combined into a unified candidate representation.

The merge process preserves all available evidence before conflicts are evaluated — nothing is discarded prematurely.

---

### Step 7 — Resolve Conflicts

When multiple sources provide different values for the same field, the system applies deterministic business rules to select the canonical value.

Conflict resolution follows documented policies so that identical inputs always produce identical outputs.

---

### Step 8 — Record Provenance

For every field included in the canonical profile, the system records its origin: which source supplied the value and which method selected it.

Provenance enables downstream users to understand:

- Which source supplied the value.
- Which transformation/selection rule was applied.
- Why the value was chosen over the alternatives.

This supports explainability and auditability, and it is captured as a direct by-product of conflict resolution (Step 7), so the "why" is never reconstructed after the fact.

---

### Step 9 — Calculate Confidence

Every transformed value receives a confidence score representing how confident the system is in the selected value.

Confidence **consumes provenance signals** and is derived from factors such as source agreement, per-field source reliability, data quality, and validation results. A value corroborated by multiple reliable sources scores higher than a single uncorroborated value from a low-reliability source.

---

### Step 10 — Generate Canonical Profile

After normalization, merging, conflict resolution, provenance tracking, and confidence calculation are complete, the system assembles a single canonical candidate profile.

This profile is the authoritative, internal version of the candidate — the source of truth from which all output shapes are projected.

---

### Step 11 — Apply Output Configuration

The canonical profile is projected into the requested output schema.

Different consumers may require different subsets or structures of candidate information. A runtime configuration can:

- Select a subset of fields to include.
- Rename / remap fields from a canonical path.
- Apply per-field normalization.
- Toggle provenance and confidence on or off.
- Decide what to do when a value is missing (`null`, `omit`, or `error`).

Output customization changes only the **representation** of the data and never modifies the canonical profile itself.

---

### Step 12 — Validate Final Output

Before returning the result, the generated output is validated against the requested schema to ensure structural correctness and completeness.

Any validation issues are reported before delivery.

---

### Step 13 — Return Canonical Candidate Profile

The validated profile is returned to the requesting application.

Downstream systems consume this profile as their trusted representation of the candidate without performing additional transformation or conflict resolution.

---

## Expected Outcome

At the end of the workflow:

- All supported input sources have been processed (valid ones used, invalid ones reported, never crashing the run).
- Candidate information has been normalized.
- Duplicate records have been merged into one entity.
- Conflicting values have been resolved deterministically.
- Provenance has been preserved for every field.
- Confidence scores have been assigned.
- A deterministic canonical candidate profile has been produced.
- The output conforms to the requested schema.
