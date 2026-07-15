from __future__ import annotations

from dataclasses import dataclass
from typing import Any, NoReturn


@dataclass(eq=False)
class EvidenceRefusal(ValueError):
    code: str
    context: dict[str, Any]

    def __init__(self, code: str, **context: Any) -> None:
        self.code = code
        self.context = dict(sorted(context.items()))
        super().__init__(code)


def refuse(code: str, **context: Any) -> NoReturn:
    raise EvidenceRefusal(code, **context)


def require(condition: bool, code: str, **context: Any) -> None:
    if not condition:
        refuse(code, **context)


def require_foreign_keys(conn: Any) -> None:
    if conn.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        refuse("foreign-keys-disabled")


def audit_receipt(conn: Any, receipt_id: str) -> dict[str, int]:
    if (
        conn.execute(
            "SELECT 1 FROM reconstruction_receipt WHERE receipt_id=?", (receipt_id,)
        ).fetchone()
        is None
    ):
        refuse("receipt-incomplete")
    counts = {"included": 0, "excluded": 0, "refused": 0}
    rows = conn.execute(
        "SELECT disposition,reason_code FROM receipt_reference WHERE receipt_id=?", (receipt_id,)
    ).fetchall()
    if not rows:
        refuse("receipt-incomplete")
    for disposition, reason in rows:
        if disposition not in counts or (disposition != "included" and not reason):
            refuse("receipt-reference-invalid")
        counts[disposition] += 1
    return counts
