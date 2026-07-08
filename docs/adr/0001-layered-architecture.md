# ADR 0001: Layered Architecture for the Backend

- **Status**: Accepted
- **Date**: 2026-07-08
- **Context**: Initial refactor of the MVP into production-grade code

## Context

The original MVP placed all logic directly inside FastAPI route handlers. Routes reached
into SQLAlchemy ORM models, performed aggregations inline, returned Pydantic models, and
handled errors — all in 100-300 line functions. This made the code impossible to test
without spinning up a full HTTP server, and impossible to reuse the business logic
from, say, a CLI or a background worker.

## Decision

We adopt a strict 4-layer architecture for `backend/app/`:

```
api/routes/      →   services/      →   repositories/  →   models/
(thin HTTP)          (business logic)   (data access)     (ORM + schemas)
```

- **`api/routes/`** — only: parse request → call service → serialize response.
  No SQLAlchemy. No business rules. No `if partner == ...` logic.
- **`services/`** — pure Python business logic. Takes a SQLAlchemy `Session`
  and primitive types. Returns Pydantic models.
- **`repositories/`** — all SQLAlchemy queries. Functions take `db: Session`
  and filter args, return rows or scalars.
- **`models/`** — SQLAlchemy ORM + Pydantic request/response schemas.

## Consequences

### Positive

- **Testability**: services can be unit-tested with an in-memory SQLite session.
  Repositories can be tested independently. No HTTP machinery needed.
- **Reusability**: services can be invoked from a background job, a CLI, or a
  future microservice without modification.
- **Readability**: route files drop to <100 lines each; business rules are
  concentrated in one place per concern.

### Negative

- **More files**: each domain now has at minimum 3 files (route + service +
  repository). Small features may feel over-engineered.
- **Layered tax**: every value crosses 3-4 module boundaries. If a refactor
  changes the data model, the schema needs to change in 2-3 places.

### Mitigations

- The cost of an extra file is low; copy-paste of a complex query into a route
  is much more expensive over time.
- The "layered tax" is offset by Pydantic providing a single source of truth
  for the schema, which is then shared by the service, route, and frontend
  TypeScript type.

## Alternatives considered

1. **Flat routes** (status quo) — rejected: untestable, unmaintainable.
2. **Service layer only, no repository** — rejected: routes still depend on
   SQLAlchemy, making service unit tests require a real DB.
3. **Domain-Driven Design with aggregates** — rejected: overkill for the current
   data model; we have 5 tables, not 50.
