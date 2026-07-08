"""Repositories package.

Data access layer. Each repository encapsulates SQLAlchemy queries
for a specific domain entity. Repositories are pure data access:
- No business logic
- No HTTP concerns
- All queries return ORM rows, scalars, or simple types
"""
