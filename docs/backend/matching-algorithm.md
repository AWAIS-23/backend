# Deterministic Matching Algorithm Specification

## 1. Objective

The Rising Skills Matching Engine v1 connects candidates to career opportunities based on verified capability rather than CV text parsing or opaque AI embeddings.

---

## 2. Core Formula

$$\text{overall\_score} = 0.60 \times \text{skill\_score} + 0.30 \times \text{evidence\_score} + 0.10 \times \text{experience\_score}$$

All component scores and the final score are normalized to a scale of $0.0 \dots 100.0$.

---

## 3. Component Details

### 3.1 Skill Score ($60\%$ Weight)

Measures weighted competency coverage across the opportunity's required skills:

$$\text{skill\_score} = \frac{\sum_{i=1}^{n} (w_i \times c_i)}{\sum_{i=1}^{n} w_i}$$

- $w_i$: Importance weight of skill $i$ ($0.0 \le w_i \le 1.0$).
- $c_i$: Learner's coverage on skill $i$:
  - If learner has **verified** evidence for skill $i$: $c_i = \max(\text{score})$.
  - If learner has **unverified** or **no** evidence: $c_i = 0.0$.

### 3.2 Evidence Score ($30\%$ Weight)

Measures the proportion of required skills for which the candidate has earned verified evidence:

$$\text{evidence\_score} = \frac{\text{Count of verified required skills}}{\text{Total required skills}} \times 100.0$$

### 3.3 Experience Score ($10\%$ Weight)

Measures hands-on practical track record from verified practical challenge submissions:

- $\ge 2$ verified practical challenge submissions: **$100.0$**
- $1$ verified practical challenge submission: **$70.0$**
- $0$ verified practical challenge submissions: **$0.0$**

---

## 4. Explainable Breakdown Schema

Each computed match produces an explainable breakdown stored in the `breakdown` JSON column:

```json
{
  "matched_skills": 3,
  "required_skills": 3,
  "verified_challenges_count": 2,
  "formula": "0.60*skill_score + 0.30*evidence_score + 0.10*experience_score",
  "skill_details": [
    {
      "skill_id": "11110000-1111-2222-3333-444455556666",
      "skill_name": "Python",
      "weight": 0.5,
      "coverage": 100.0,
      "has_verified_evidence": true,
      "evidence_score": 100.0
    },
    {
      "skill_id": "22220000-1111-2222-3333-444455556666",
      "skill_name": "FastAPI",
      "weight": 0.3,
      "coverage": 80.0,
      "has_verified_evidence": true,
      "evidence_score": 80.0
    },
    {
      "skill_id": "33330000-1111-2222-3333-444455556666",
      "skill_name": "PostgreSQL",
      "weight": 0.2,
      "coverage": 60.0,
      "has_verified_evidence": true,
      "evidence_score": 60.0
    }
  ]
}
```
