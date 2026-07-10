"""Typed SQLite graph for E3's authored manager-memory demo.

The graph is deliberately a collection of ordinary typed tables. Every factual
row carries the source document, exact source span, and as-of date used to admit
it. Graph expansion is limited to the one-hop manager/document and
manager/person/document paths approved for v1.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

NODE_TABLES = (
    "strategy",
    "manager",
    "person",
    "document",
    "view",
    "theme",
    "meeting",
)
EDGE_TABLES = (
    "authored_by",
    "attributed_to",
    "employed_by",
    "expresses",
    "about_theme",
    "discussed_at",
)

_TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "strategy": ("strategy_id", "label", "source_doc", "source_span", "as_of"),
    "manager": (
        "manager_id",
        "name",
        "tier",
        "strategy_id",
        "tier_grant_date",
        "source_doc",
        "source_span",
        "as_of",
    ),
    "person": ("person_id", "name", "role", "source_doc", "source_span", "as_of"),
    "document": (
        "doc_id",
        "doc_type",
        "text",
        "date",
        "file_path",
        "ingest_date",
        "source_doc",
        "source_span",
        "as_of",
    ),
    "view": (
        "view_id",
        "direction",
        "horizon",
        "conviction",
        "source_doc",
        "source_span",
        "as_of",
    ),
    "theme": ("theme_id", "label", "source_doc", "source_span", "as_of"),
    "meeting": (
        "meeting_id",
        "date",
        "attendees",
        "linked_doc_id",
        "source_doc",
        "source_span",
        "as_of",
    ),
    "authored_by": ("doc_id", "person_id", "source_doc", "source_span", "as_of"),
    "attributed_to": ("doc_id", "manager_id", "source_doc", "source_span", "as_of"),
    "employed_by": (
        "person_id",
        "manager_id",
        "from_date",
        "to_date",
        "source_doc",
        "source_span",
        "as_of",
    ),
    "expresses": ("doc_id", "view_id", "source_doc", "source_span", "as_of"),
    "about_theme": ("view_id", "theme_id", "source_doc", "source_span", "as_of"),
    "discussed_at": ("view_id", "meeting_id", "source_doc", "source_span", "as_of"),
}


@dataclass(frozen=True)
class GraphFixture:
    """Rows keyed by one of the fixed typed node or edge table names."""

    tables: Mapping[str, Sequence[Mapping[str, object]]]


def connect_graph(database: str | Path = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(str(database))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_schema(conn: sqlite3.Connection) -> None:
    """Create the complete typed E3 schema on an empty connection."""

    conn.executescript(
        """
        CREATE TABLE strategy (
            strategy_id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            source_doc TEXT NOT NULL,
            source_span TEXT NOT NULL,
            as_of TEXT NOT NULL
        );
        CREATE TABLE manager (
            manager_id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            tier TEXT NOT NULL CHECK (tier IN ('R', 'E', 'P')),
            strategy_id TEXT NOT NULL REFERENCES strategy(strategy_id),
            tier_grant_date TEXT NOT NULL,
            source_doc TEXT NOT NULL,
            source_span TEXT NOT NULL,
            as_of TEXT NOT NULL
        );
        CREATE TABLE person (
            person_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            source_doc TEXT NOT NULL,
            source_span TEXT NOT NULL,
            as_of TEXT NOT NULL
        );
        CREATE TABLE document (
            doc_id TEXT PRIMARY KEY,
            doc_type TEXT NOT NULL CHECK (doc_type IN ('letter', 'ddq', 'meeting_note')),
            text TEXT NOT NULL,
            date TEXT NOT NULL,
            file_path TEXT NOT NULL,
            ingest_date TEXT NOT NULL,
            source_doc TEXT NOT NULL,
            source_span TEXT NOT NULL,
            as_of TEXT NOT NULL
        );
        CREATE TABLE "view" (
            view_id TEXT PRIMARY KEY,
            direction TEXT NOT NULL CHECK (
                direction IN ('long/constructive', 'short/cautious', 'neutral-explicit')
            ),
            horizon TEXT NOT NULL,
            conviction INTEGER NOT NULL CHECK (conviction BETWEEN 1 AND 3),
            source_doc TEXT NOT NULL,
            source_span TEXT NOT NULL,
            as_of TEXT NOT NULL
        );
        CREATE TABLE theme (
            theme_id TEXT PRIMARY KEY,
            label TEXT NOT NULL UNIQUE,
            source_doc TEXT NOT NULL,
            source_span TEXT NOT NULL,
            as_of TEXT NOT NULL
        );
        CREATE TABLE meeting (
            meeting_id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            attendees TEXT NOT NULL,
            linked_doc_id TEXT NOT NULL REFERENCES document(doc_id),
            source_doc TEXT NOT NULL,
            source_span TEXT NOT NULL,
            as_of TEXT NOT NULL
        );
        CREATE TABLE authored_by (
            doc_id TEXT NOT NULL REFERENCES document(doc_id),
            person_id TEXT NOT NULL REFERENCES person(person_id),
            source_doc TEXT NOT NULL,
            source_span TEXT NOT NULL,
            as_of TEXT NOT NULL,
            PRIMARY KEY (doc_id, person_id)
        );
        CREATE TABLE attributed_to (
            doc_id TEXT NOT NULL REFERENCES document(doc_id),
            manager_id TEXT NOT NULL REFERENCES manager(manager_id),
            source_doc TEXT NOT NULL,
            source_span TEXT NOT NULL,
            as_of TEXT NOT NULL,
            PRIMARY KEY (doc_id, manager_id)
        );
        CREATE TABLE employed_by (
            person_id TEXT NOT NULL REFERENCES person(person_id),
            manager_id TEXT NOT NULL REFERENCES manager(manager_id),
            from_date TEXT NOT NULL,
            to_date TEXT,
            source_doc TEXT NOT NULL,
            source_span TEXT NOT NULL,
            as_of TEXT NOT NULL,
            PRIMARY KEY (person_id, manager_id, from_date)
        );
        CREATE TABLE expresses (
            doc_id TEXT NOT NULL REFERENCES document(doc_id),
            view_id TEXT NOT NULL REFERENCES "view"(view_id),
            source_doc TEXT NOT NULL,
            source_span TEXT NOT NULL,
            as_of TEXT NOT NULL,
            PRIMARY KEY (doc_id, view_id)
        );
        CREATE TABLE about_theme (
            view_id TEXT NOT NULL REFERENCES "view"(view_id),
            theme_id TEXT NOT NULL REFERENCES theme(theme_id),
            source_doc TEXT NOT NULL,
            source_span TEXT NOT NULL,
            as_of TEXT NOT NULL,
            PRIMARY KEY (view_id, theme_id)
        );
        CREATE TABLE discussed_at (
            view_id TEXT NOT NULL REFERENCES "view"(view_id),
            meeting_id TEXT NOT NULL REFERENCES meeting(meeting_id),
            source_doc TEXT NOT NULL,
            source_span TEXT NOT NULL,
            as_of TEXT NOT NULL,
            PRIMARY KEY (view_id, meeting_id)
        );
        CREATE INDEX idx_manager_name ON manager(name);
        CREATE INDEX idx_attributed_manager ON attributed_to(manager_id);
        CREATE INDEX idx_employed_manager ON employed_by(manager_id, person_id);
        CREATE INDEX idx_authored_person ON authored_by(person_id, doc_id);
        """
    )


def ingest_fixture(conn: sqlite3.Connection, fixture: GraphFixture) -> None:
    unknown = set(fixture.tables) - set(_TABLE_COLUMNS)
    if unknown:
        raise ValueError(f"unknown graph fixture tables: {sorted(unknown)}")

    try:
        with conn:
            for table in (*NODE_TABLES, *EDGE_TABLES):
                columns = _TABLE_COLUMNS[table]
                quoted_table = f'"{table}"' if table == "view" else table
                placeholders = ", ".join("?" for _ in columns)
                column_sql = ", ".join(columns)
                sql = f"INSERT INTO {quoted_table} ({column_sql}) VALUES ({placeholders})"
                for row in fixture.tables.get(table, ()):
                    conn.execute(sql, tuple(row.get(column) for column in columns))
    except sqlite3.IntegrityError:
        conn.rollback()
        raise


def _normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def entity_link_manager(conn: sqlite3.Connection, query: str) -> str | None:
    normalized_query = _normalize(query)
    matches = []
    for row in conn.execute("SELECT manager_id, name FROM manager"):
        normalized_name = _normalize(row["name"])
        name_tokens = normalized_name.split()
        # Authored manager names commonly end in a legal/industry suffix while the
        # decision-hook query uses the distinctive two-word name ("Corvid Lane").
        aliases = [" ".join(name_tokens[:size]) for size in range(2, len(name_tokens) + 1)]
        aliases = [alias for alias in aliases if alias in normalized_query]
        if aliases:
            longest = max(aliases, key=lambda alias: (len(alias), alias))
            matches.append((len(longest), normalized_name, row["manager_id"]))
    if not matches:
        return None
    return sorted(matches, key=lambda item: (-item[0], item[1], item[2]))[0][2]


def graph_candidates(conn: sqlite3.Connection, manager_id: str) -> list[str]:
    """Return only direct and manager-person-document candidates (one hop)."""

    rows = conn.execute(
        """
        SELECT doc_id FROM attributed_to WHERE manager_id = ?
        UNION
        SELECT authored_by.doc_id
        FROM authored_by
        JOIN employed_by USING (person_id)
        WHERE employed_by.manager_id = ?
        ORDER BY doc_id
        """,
        (manager_id, manager_id),
    )
    return [row["doc_id"] for row in rows]


def candidate_paths(
    conn: sqlite3.Connection, manager_id: str, doc_id: str
) -> tuple[str, ...]:
    paths: list[str] = []
    direct = conn.execute(
        "SELECT 1 FROM attributed_to WHERE manager_id = ? AND doc_id = ?",
        (manager_id, doc_id),
    ).fetchone()
    if direct:
        paths.append(f"attributed_to:{manager_id}")

    people = conn.execute(
        """
        SELECT authored_by.person_id
        FROM authored_by
        JOIN employed_by USING (person_id)
        WHERE authored_by.doc_id = ? AND employed_by.manager_id = ?
        ORDER BY authored_by.person_id
        """,
        (doc_id, manager_id),
    )
    paths.extend(
        f"authored_by:{row['person_id']}->employed_by:{manager_id}" for row in people
    )
    return tuple(sorted(paths))
