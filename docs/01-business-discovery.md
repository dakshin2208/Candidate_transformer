# 01 — Business Discovery

## Project

**Multi-Source Candidate Data Transformer**

## Business Problem

Candidate information exists across multiple independent sources — Applicant Tracking Systems (ATS), recruiter CSV exports, resumes, LinkedIn profiles, GitHub profiles, and recruiter notes. Each source represents only a **partial view** of the candidate and frequently contains inconsistent, duplicated, incomplete, or directly conflicting information.

Downstream hiring systems require a single, reliable candidate profile. Without a standardized representation, every consuming application would have to implement its own parsing, cleaning, normalization, and conflict-resolution logic — leading to duplicated effort and, worse, inconsistent hiring decisions across products.

The deeper risk is silent corruption. A single wrong-but-confident value — a stale phone number, a mismatched current employer, a misattributed skill — flows unnoticed into candidate search, matching, and recruiter outreach. **Nobody knows it is wrong, and the bad value silently pollutes hiring decisions.** Wrong-but-confident is worse than honestly-empty.

The purpose of this project is to build a transformation engine that converts heterogeneous candidate data into **one canonical candidate profile** that is consistent, explainable, and ready for downstream consumption.

## Business Goal

Create a reusable transformation pipeline that:

- Accepts candidate information from multiple structured and unstructured sources.
- Cleans and normalizes inconsistent data into common formats.
- Identifies records belonging to the same candidate.
- Resolves conflicting values using deterministic, documented rules.
- Produces one canonical candidate profile.
- Records **provenance** for every generated field (which source, which method).
- Calculates **confidence** scores for transformed values.
- Supports configurable output formats **without modifying the transformation engine**.

## Target Users

**Primary users — engineering teams building hiring products.** They integrate the engine once and stop re-solving data cleanup in every product.

**Secondary users — internal services that consume the profile but never clean data themselves:**

- Candidate Search
- Matching Engine
- Recruiter Dashboard
- Analytics Platform
- AI-powered Hiring Features
- Reporting Systems

These systems trust the canonical profile as their source of truth, which is exactly why the cost of a bad value is high: one silent error fans out across every consumer simultaneously.

## Business Value

A centralized transformation engine provides:

- **Eliminates duplicate transformation logic** across multiple products — one engine, not N parsers.
- **Improves data consistency** across the entire hiring platform.
- **Produces explainable outputs** through provenance tracking — every value is traceable.
- **Supports auditability** — because outputs are deterministic and traceable, the question "why does this profile say X?" always has a reproducible answer. This matters when hiring decisions are reviewed, challenged, or audited.
- **Reduces incorrect hiring decisions** caused by inconsistent or silently corrupted data.
- **Standardizes consumption** — downstream systems read one fixed shape.
- **Eases future integration** — adding a new source does not require redesigning consumers.

## Core Responsibilities

The system is responsible for:

- Parsing multiple candidate data sources (structured and unstructured).
- Normalizing data into common formats.
- Merging records that belong to the same candidate.
- Resolving conflicting values.
- Calculating confidence scores.
- Tracking provenance.
- Generating configurable output schemas.
- Validating the final output before returning it.

## Out of Scope

The system does **not**:

- Rank candidates.
- Recommend jobs.
- Evaluate candidate quality.
- Generate interview feedback.
- Predict hiring success.
- Modify source data.
- **Invent missing information** — unknown values become `null`, never fabricated.
- Perform authentication or user management.

Its only responsibility is transforming candidate data into a trusted canonical representation.

## Success Criteria

The system is successful when it:

- Produces one canonical profile per candidate.
- Generates **deterministic** outputs for identical inputs.
- Correctly normalizes supported fields (dates, phones, country codes, skill names, …).
- Resolves conflicting information using documented rules.
- Preserves **provenance** for transformed values.
- Computes **confidence** scores consistently.
- Produces schema-valid, configurable outputs.
- Handles incomplete or malformed inputs **gracefully, without crashing**.

## Assumptions

- Input data may be incomplete, malformed, or inconsistent.
- Multiple sources may describe the same candidate.
- Different sources may disagree on field values.
- **Source reliability varies depending on the field** — e.g. GitHub is authoritative for repos/languages, an ATS may be authoritative for application metadata, a resume for self-reported experience. *(This assumption is load-bearing: it is the foundation of the merge and confidence policy defined in doc 04.)*
- The transformation engine is independent of any downstream application.
- Additional data sources can be added in the future without redesigning the entire system.
