"""Services package.

Business logic layer. Services orchestrate repositories and apply
domain rules. They are the only layer that should contain business
logic; routes are thin adapters that call services and serialize
the result.
"""
