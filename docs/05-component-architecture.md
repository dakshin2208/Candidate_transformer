# 05 — Component Architecture

## Purpose

This document defines the software architecture of the Multi-Source Candidate Data Transformer.

The business workflow and transformation rules are defined in the earlier docs. This document maps those business responsibilities onto **independent software components** with clear ownership, well-defined interfaces, and minimal coupling.

The objective: every component has a single responsibility, can be developed and tested independently, and can evolve without affecting unrelated parts of the system.

---

## Architectural Style

The system follows a **pipeline architecture** with a small amount of fan-in. Each stage performs one well-defined transformation and passes its output downstream; provenance and confidence read from the same resolved state and feed the builder.

```
                Candidate Data Sources
                        │
                        ▼
               Input Validation
                        │
                        ▼
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
                 ┌────────┴────────┐
                 ▼                 ▼
        Provenance Tracker   Confidence Engine
                 └────────┬────────┘
                          ▼
          Canonical Profile Builder
                          │
                          ▼
             Output Projection Engine
                          │
                          ▼
                Output Validator
                          │
                          ▼
              Canonical Candidate Profile
```

This structure ensures deterministic processing while keeping each transformation stage independent.

---

## Component Responsibilities

| Component | Responsibility | Never Does |
|---|---|---|
| Input Validator | Validate incoming files, payloads, and configuration | Parse or transform data |
| Source Parsers | Extract structured candidate info from each source | Normalize or merge values |
| Normalization Engine | Convert extracted values into canonical formats | Identify duplicate candidates |
| Candidate Matching Engine | Determine which records belong to the same candidate | Resolve conflicting values |
| Merge Engine | Combine all information belonging to the same candidate | Decide which value wins |
| Conflict Resolution Engine | Select canonical values using deterministic rules | Calculate confidence scores |
| Provenance Tracker | Record source history, selection rules, selected values | Modify canonical data |
| Confidence Engine | Calculate confidence for every resolved field | Change selected values |
| Canonical Profile Builder | Assemble the final internal candidate representation | Apply consumer-specific formatting |
| Output Projection Engine | Project consumer-specific output schemas from the canonical profile | Modify canonical data |
| Output Validator | Validate projected output against the requested schema | Perform transformations |

The **"Never Does"** column is the enforcement mechanism for separation of concerns — it defines each component by its boundaries, not just its job.

---

## Component Interactions & Dependencies

Data flows downstream. The dependency graph is a **strict one-directional DAG** — there are no cycles — but it is **not a pure linear chain**: provenance, confidence, and the profile builder each have legitimate fan-in from multiple upstream stages.

| Component | Depends On |
|---|---|
| Input Validator | None |
| Source Parsers | Input Validator |
| Normalization Engine | Source Parsers |
| Candidate Matching Engine | Normalization Engine |
| Merge Engine | Candidate Matching Engine |
| Conflict Resolution Engine | Merge Engine |
| Provenance Tracker | Conflict Resolution Engine |
| Confidence Engine | Conflict Resolution Engine, Provenance Tracker |
| Canonical Profile Builder | Conflict Resolution Engine, Provenance Tracker, Confidence Engine |
| Output Projection Engine | Canonical Profile Builder |
| Output Validator | Output Projection Engine |

No component mutates the internal state of another; communication is one-directional through defined interfaces only. This prevents circular dependencies and keeps each stage independently testable.

---

## Failure Boundaries

Each component handles failures within its own scope. A failure in one stage does **not** terminate the pipeline — **with one deliberate exception** noted below.

| Component | Failure Handling |
|---|---|
| Input Validator | Reject structurally invalid input with a descriptive error |
| Source Parsers | Skip malformed sources, continue, report |
| Normalization Engine | Store `null` for invalid values, record provenance |
| Candidate Matching Engine | Fall to lower-priority match keys when strong IDs are absent |
| Merge Engine | Preserve all values for later conflict resolution |
| Conflict Resolution Engine | Apply deterministic precedence + tiebreak rules |
| Provenance Tracker | Record partial/weak provenance where necessary |
| Confidence Engine | Lower confidence when evidence is weak |
| Output Projection Engine | Validate config before projecting; honor `on_missing` |
| Output Validator | Reject schema-invalid output with clear errors |

**The one place a deliberate error may surface:** the Projection / Validator boundary. When the runtime config sets `on_missing: "error"`, a missing requested field is *meant* to raise — that is the engine **honoring its contract**, not a crash. Garbage *inputs* never crash the run; a configured `error` on *output* is an explicit, requested behavior. Robustness and contract-honoring are not in conflict here.

---

## Design Principles

- **Single Responsibility** — every component owns one business capability.
- **Loose Coupling** — components interact only through defined interfaces.
- **High Cohesion** — related logic stays within one component.
- **Deterministic Processing** — identical inputs, identical outputs.
- **Canonical Data Model** — all internal processing operates on one authoritative representation.
- **Extensibility** — adding a source requires a new parser **plus** a precedence/reliability entry in the conflict and confidence rules (so matching and merging know how to rank it). No core redesign.
- **Testability** — every component is unit-testable in isolation.

---

## Mapping Business Rules to Components

| Business Rule (from doc 04) | Owning Component |
|---|---|
| Input validation | Input Validator |
| Data extraction | Source Parsers |
| Field normalization | Normalization Engine |
| Candidate identification | Candidate Matching Engine |
| Record merging | Merge Engine |
| Conflict resolution | Conflict Resolution Engine |
| Provenance tracking | Provenance Tracker |
| Confidence calculation | Confidence Engine |
| Canonical profile creation | Canonical Profile Builder |
| Runtime output configuration | Output Projection Engine |
| Final schema validation | Output Validator |

This mapping gives every business rule from doc 04 exactly one owning component, and serves as the implementation blueprint for the engineering phase.
