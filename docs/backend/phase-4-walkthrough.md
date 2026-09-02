# Phase 4 — Opportunity Publishing, Deterministic Matching & Applications: Teaching Walkthrough

---

## 1. What Are the Core Concepts of Rising Skills?

To understand how Phase 4 functions, it helps to distinguish the core building blocks:

```
┌─────────────┐     A standardized taxonomy of technical capabilities (e.g. Python, FastAPI, Docker).
│    Skill    │
└──────┬──────┘
       │
       ▼
┌─────────────┐     Demonstrated capability output from an Assessment or Practical Challenge.
│  Evidence   │
└──────┬──────┘
       │
       ▼
┌──────────────────┐ Proof verified by an authorized human verifier (never AI). Unverified evidence
│ Verified Evidence│ provides zero matching coverage.
└──────┬───────────┘
       │
       ▼
┌─────────────┐     A real job, internship, apprenticeship, or project created by an employer.
│ Opportunity │
└──────┬──────┘
       │
       ▼
┌─────────────┐     Deterministic mathematical comparison (60% Skill + 30% Evidence + 10% Exp).
│    Match    │
└──────┬──────┘
       │
       ▼
┌─────────────┐     Learner expresses interest, sending their verified skill profile to the employer.
│ Application │
└─────────────┘
```

---

## 2. Why Did We Use a Deterministic Matching Formula Instead of AI/Embeddings?

**Problem**: AI embeddings and LLMs are non-deterministic, opaque "black boxes." When a candidate asks "Why did I get 60% instead of 90%?", an LLM cannot provide a verifiable mathematical audit trail. Furthermore, LLMs can be tricked by prompt injection or fancy buzzword-stuffed CVs.  
**Solution**: Rising Skills Matching Engine v1 uses a transparent, explainable formula:

$$\text{overall\_score} = 0.60 \times \text{skill\_score} + 0.30 \times \text{evidence\_score} + 0.10 \times \text{experience\_score}$$

Every candidate and employer can inspect the exact breakdown of weights, verified coverage, and missing skills.

---

## 3. How Does the Opportunity Lifecycle Work?

```
DRAFT ────────► PUBLISHED ────────► CLOSED
  │                 │
  └─────────────────┴─────────────► ARCHIVED
```

- When an employer creates an opportunity, it starts as `draft`.
- Only `published` opportunities are visible to learners and open for applications.
- Once `closed`, no further applications can be submitted.

---

## 4. How Is Security Enforced?

1. **Identity Integrity**: `profile_id`, `created_by`, and `reviewed_by` are always extracted from the authenticated Supabase JWT.
2. **Organization Isolation**: An employer from Company A cannot publish or review applications for Company B.
3. **Score Tamper Resistance**: Match scores are computed exclusively on the backend; the client cannot supply a score.
4. **Duplicate Guard**: Unique database constraints guarantee that a learner can only apply once to an opportunity.
