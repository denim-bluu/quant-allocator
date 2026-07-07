"""E2 engagement-pack composition layer: registry + compose + lints.

E2 computes NO statistics. It projects certified source-card payloads into one
manager's pack, gates them against the X1 PowerGate registry, and enforces the
honesty invariants. Deliberately not a framework (spec §5, §6): a committed
table, a pure function, and a set of lint checks — no plugin system.
"""
