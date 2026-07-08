# ADR 0002: SQLite for Production (For Now)

- **Status**: Accepted (with planned revisit)
- **Date**: 2026-07-08

## Context

The MVP ships SQLite as the database. The user's refactor mandate is to
make the system production-grade, but explicitly chose to "keep SQLite for
now" in the architectural decisions.

## Decision

We retain SQLite as the primary store but:

1. Move the database file out of the source tree into `DATA_DIR`
2. Mount a Docker volume at the new path so the data persists across
   container restarts
3. Make the connection string configurable via `DATABASE_URL`
4. Document in the runbook how to migrate to Postgres later
5. Add a constraint to the layered architecture: `repositories/` is the
   only layer that knows about the specific database, so swapping to
   Postgres affects at most those files

## Consequences

### Positive

- Zero ops overhead (no separate DB container)
- Backups are a single `cp` (see `docs/OPERATIONS.md` § 6)
- Migration to Postgres is a contained change

### Negative

- Single-writer: high-concurrency writes will serialize at the file level
- No network access: the backend must be co-located with the DB
- No managed backups / replication / point-in-time recovery

### When to revisit

If the platform exceeds **~50 writes/sec sustained** or **~10 GB of data**,
migrate to PostgreSQL. The repository layer is designed to make this a
day-1-effort change.
