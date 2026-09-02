# Rising Skills — Backend Architecture Specification

## 1. System Vision & Core Product Loop

Rising Skills is a **skills-to-opportunity platform**. Its core premise is converting demonstrated capability into credible evidence and matching that evidence directly to real opportunities.

```
       ┌──────────┐      ┌─────────┐      ┌────────────┐      ┌──────────┐
       │  ASSESS  │ ───► │  PROVE  │ ───► │ EXPERIENCE │ ───► │  VERIFY  │
       └──────────┘      └─────────┘      └────────────┘      └──────────┘
                                                                    │
       ┌──────────┐      ┌─────────┐      ┌────────────┐            │
       │   GROW   │ ◄─── │FEEDBACK │ ◄─── │OPPORTUNITY │ ◄──────────┘
       └──────────┘      └─────────┘      └────────────┘
```

The system is strictly designed as a **Modular Monolith** to maximize developer productivity, operational simplicity, data consistency, and clear domain separation.

---

## 2. Conceptual Layering & Data Flow

```
                      Client Layer (Next.js / HTTPS + Bearer JWT)
                                          │
                                          ▼
                      FastAPI Gateway & Security Middleware
                      ├── Global RFC-7807 Exception Handlers
                      ├── Structured Contextual Logging (Correlation IDs)
                      └── CORS & Security Headers
                                          │
                                          ▼
                         Authentication & Authorization
                      ├── Supabase JWT Claim Verification
                      ├── AuthenticatedUser Identity Resolution
                      └── Role & Organization Access Guards (RBAC)
                                          │
                                          ▼
                              API Layer (/api/v1/...)
                      ├── Request Validation (Pydantic v2 DTOs)
                      ├── Service Invocation
                      └── Response Serialization (Pydantic v2 Schemas)
                                          │
                                          ▼
                                 Domain Service Layer
                      ├── Pure Business Logic & Domain Rules
                      ├── Evaluation & Scoring Engines
                      ├── Deterministic Matching Algorithms
                      └── Orchestration of Integrations (e.g. AI)
                                ┌─────────┴─────────┐
                                │                   │
                                ▼                   ▼
                        Repository Layer     AI Integration Layer
                      ├── Data Access       ├── AIProvider Interface
                      ├── Query Scoping     ├── Groq Client
                      └── Transaction Mgmt  └── Strict Pydantic Parser
                                │
                                ▼
                       SQLAlchemy 2.x (Asyncpg)
                                │
                                ▼
                      Supabase PostgreSQL DB (RLS Enabled)
```

---

## 3. Strict Layering Invariants

1. **Routers never execute business logic or SQL queries.** Routers only validate input, verify permissions, call a service method, and format the output.
2. **Services never construct direct SQL strings.** All data access occurs via typed Repository interfaces.
3. **Identity is never trusted from request bodies.** The user ID is strictly extracted from the validated Supabase JWT (`sub` claim).
4. **AI never directly mutates verified state.** AI can assist, suggest, or draft, but verification and scoring are governed by deterministic domain rules and authorized human/evaluator workflows.
