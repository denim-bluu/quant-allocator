"""Typed E3 graph bound to canonical entities, evidence spans, and relationships."""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from quant_allocator.evidence.schema import connect as connect_evidence
from quant_allocator.evidence.schema import initialize as initialize_evidence

NODE_TABLES = ("strategy", "manager", "person", "document", "view", "theme", "meeting")
_INGEST_NODE_TABLES = NODE_TABLES
EDGE_TABLES = (
    "authored_by",
    "attributed_to",
    "employed_by",
    "expresses",
    "about_theme",
    "discussed_at",
)

_TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "strategy": ("strategy_id", "label", "canonical_entity_id", "evidence_span_id"),
    "manager": (
        "manager_id",
        "name",
        "tier",
        "strategy_id",
        "tier_grant_date",
        "canonical_entity_id",
        "evidence_span_id",
    ),
    "person": ("person_id", "name", "role", "canonical_entity_id", "evidence_span_id"),
    "document": (
        "doc_id",
        "doc_type",
        "date",
        "file_path",
        "ingest_date",
        "canonical_entity_id",
        "evidence_item_id",
        "evidence_span_id",
    ),
    "view": (
        "view_id",
        "direction",
        "horizon",
        "conviction",
        "canonical_entity_id",
        "evidence_span_id",
    ),
    "theme": ("theme_id", "label", "canonical_entity_id", "evidence_span_id"),
    "meeting": (
        "meeting_id",
        "date",
        "attendees",
        "linked_doc_id",
        "canonical_entity_id",
        "evidence_span_id",
    ),
    "authored_by": ("doc_id", "person_id", "entity_relationship_id", "evidence_span_id"),
    "attributed_to": ("doc_id", "manager_id", "entity_relationship_id", "evidence_span_id"),
    "employed_by": ("person_id", "manager_id", "entity_relationship_id", "evidence_span_id"),
    "expresses": ("doc_id", "view_id", "entity_relationship_id", "evidence_span_id"),
    "about_theme": ("view_id", "theme_id", "entity_relationship_id", "evidence_span_id"),
    "discussed_at": ("view_id", "meeting_id", "entity_relationship_id", "evidence_span_id"),
}
_EDGE_PROJECTIONS = {
    "authored_by": ("document", "doc_id", "person", "person_id"),
    "attributed_to": ("document", "doc_id", "manager", "manager_id"),
    "employed_by": ("person", "person_id", "manager", "manager_id"),
    "expresses": ("document", "doc_id", "view", "view_id"),
    "about_theme": ("view", "view_id", "theme", "theme_id"),
    "discussed_at": ("view", "view_id", "meeting", "meeting_id"),
}


@dataclass(frozen=True)
class GraphFixture:
    tables: Mapping[str, Sequence[Mapping[str, object]]]


def connect_graph(database: str | Path = ":memory:") -> sqlite3.Connection:
    if str(database) == ":memory:":
        # Compatibility constructor for the standalone retrieval tests. Production E3
        # passes the bridge-owned connection directly and therefore still binds once.
        from quant_allocator.flagships.knowledge.evidence_bridge import build_e3_evidence
        from quant_allocator.flagships.saydo.corpus import build_corpus

        return build_e3_evidence(build_corpus(include_ddq_and_notes=True)).conn
    conn = connect_evidence(database)
    initialize_evidence(conn)
    return conn


def initialize_schema(conn: sqlite3.Connection) -> None:
    """Create graph tables on the already-initialized evidence connection."""

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS strategy(strategy_id TEXT PRIMARY KEY,label TEXT NOT NULL,canonical_entity_id TEXT NOT NULL REFERENCES canonical_entity,evidence_span_id TEXT NOT NULL REFERENCES evidence_span);
        CREATE TABLE IF NOT EXISTS manager(manager_id TEXT PRIMARY KEY,name TEXT NOT NULL UNIQUE,tier TEXT NOT NULL CHECK(tier IN ('R','E','P')),strategy_id TEXT NOT NULL REFERENCES strategy,tier_grant_date TEXT NOT NULL,canonical_entity_id TEXT NOT NULL REFERENCES canonical_entity,evidence_span_id TEXT NOT NULL REFERENCES evidence_span);
        CREATE TABLE IF NOT EXISTS person(person_id TEXT PRIMARY KEY,name TEXT NOT NULL,role TEXT NOT NULL,canonical_entity_id TEXT NOT NULL REFERENCES canonical_entity,evidence_span_id TEXT NOT NULL REFERENCES evidence_span);
        CREATE TABLE IF NOT EXISTS document(doc_id TEXT PRIMARY KEY,doc_type TEXT NOT NULL CHECK(doc_type IN ('letter','ddq','meeting_note','relationship_record')),date TEXT NOT NULL,file_path TEXT NOT NULL,ingest_date TEXT NOT NULL,canonical_entity_id TEXT NOT NULL REFERENCES canonical_entity,evidence_item_id TEXT NOT NULL REFERENCES evidence_item,evidence_span_id TEXT NOT NULL REFERENCES evidence_span);
        CREATE TABLE IF NOT EXISTS "view"(view_id TEXT PRIMARY KEY,direction TEXT NOT NULL CHECK(direction IN ('long/constructive','short/cautious','neutral-explicit')),horizon TEXT NOT NULL,conviction INTEGER NOT NULL CHECK(conviction BETWEEN 1 AND 3),canonical_entity_id TEXT NOT NULL REFERENCES canonical_entity,evidence_span_id TEXT NOT NULL REFERENCES evidence_span);
        CREATE TABLE IF NOT EXISTS theme(theme_id TEXT PRIMARY KEY,label TEXT NOT NULL UNIQUE,canonical_entity_id TEXT NOT NULL REFERENCES canonical_entity,evidence_span_id TEXT NOT NULL REFERENCES evidence_span);
        CREATE TABLE IF NOT EXISTS meeting(meeting_id TEXT PRIMARY KEY,date TEXT NOT NULL,attendees TEXT NOT NULL,linked_doc_id TEXT NOT NULL REFERENCES document,canonical_entity_id TEXT NOT NULL REFERENCES canonical_entity,evidence_span_id TEXT NOT NULL REFERENCES evidence_span);
        CREATE TABLE IF NOT EXISTS authored_by(doc_id TEXT NOT NULL REFERENCES document,person_id TEXT NOT NULL REFERENCES person,entity_relationship_id TEXT NOT NULL REFERENCES entity_relationship,evidence_span_id TEXT NOT NULL REFERENCES evidence_span,PRIMARY KEY(doc_id,person_id));
        CREATE TABLE IF NOT EXISTS attributed_to(doc_id TEXT NOT NULL REFERENCES document,manager_id TEXT NOT NULL REFERENCES manager,entity_relationship_id TEXT NOT NULL REFERENCES entity_relationship,evidence_span_id TEXT NOT NULL REFERENCES evidence_span,PRIMARY KEY(doc_id,manager_id));
        CREATE TABLE IF NOT EXISTS employed_by(person_id TEXT NOT NULL REFERENCES person,manager_id TEXT NOT NULL REFERENCES manager,entity_relationship_id TEXT NOT NULL REFERENCES entity_relationship,evidence_span_id TEXT NOT NULL REFERENCES evidence_span,PRIMARY KEY(person_id,manager_id,entity_relationship_id));
        CREATE TABLE IF NOT EXISTS expresses(doc_id TEXT NOT NULL REFERENCES document,view_id TEXT NOT NULL REFERENCES "view",entity_relationship_id TEXT NOT NULL REFERENCES entity_relationship,evidence_span_id TEXT NOT NULL REFERENCES evidence_span,PRIMARY KEY(doc_id,view_id));
        CREATE TABLE IF NOT EXISTS about_theme(view_id TEXT NOT NULL REFERENCES "view",theme_id TEXT NOT NULL REFERENCES theme,entity_relationship_id TEXT NOT NULL REFERENCES entity_relationship,evidence_span_id TEXT NOT NULL REFERENCES evidence_span,PRIMARY KEY(view_id,theme_id));
        CREATE TABLE IF NOT EXISTS discussed_at(view_id TEXT NOT NULL REFERENCES "view",meeting_id TEXT NOT NULL REFERENCES meeting,entity_relationship_id TEXT NOT NULL REFERENCES entity_relationship,evidence_span_id TEXT NOT NULL REFERENCES evidence_span,PRIMARY KEY(view_id,meeting_id));
        CREATE INDEX IF NOT EXISTS idx_manager_name ON manager(name);
        CREATE INDEX IF NOT EXISTS idx_attributed_manager ON attributed_to(manager_id);
        CREATE INDEX IF NOT EXISTS idx_employed_manager ON employed_by(manager_id,person_id);
        CREATE INDEX IF NOT EXISTS idx_authored_person ON authored_by(person_id,doc_id);
        """
    )


def ingest_fixture(conn: sqlite3.Connection, fixture: GraphFixture) -> None:
    unknown = set(fixture.tables) - set(_TABLE_COLUMNS)
    if unknown:
        raise ValueError(f"unknown graph fixture tables: {sorted(unknown)}")
    with conn:
        for table in (*_INGEST_NODE_TABLES, *EDGE_TABLES):
            columns = _TABLE_COLUMNS[table]
            quoted = f'"{table}"' if table == "view" else table
            sql = f"INSERT INTO {quoted} ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})"
            for row in fixture.tables.get(table, ()):
                if table in _EDGE_PROJECTIONS:
                    _validate_edge_projection(conn, table, row)
                conn.execute(sql, tuple(row.get(column) for column in columns))


def _validate_edge_projection(
    conn: sqlite3.Connection, table: str, row: Mapping[str, object]
) -> None:
    source_table, source_key, target_table, target_key = _EDGE_PROJECTIONS[table]
    quoted_source = f'"{source_table}"' if source_table == "view" else source_table
    quoted_target = f'"{target_table}"' if target_table == "view" else target_table
    source = conn.execute(
        f"SELECT canonical_entity_id FROM {quoted_source} WHERE {source_key}=?",
        (row.get(source_key),),
    ).fetchone()
    target = conn.execute(
        f"SELECT canonical_entity_id FROM {quoted_target} WHERE {target_key}=?",
        (row.get(target_key),),
    ).fetchone()
    relationship = conn.execute(
        "SELECT relation_type,source_entity_id,target_entity_id,evidence_span_id "
        "FROM entity_relationship WHERE entity_relationship_id=?",
        (row.get("entity_relationship_id"),),
    ).fetchone()
    if (
        source is None
        or target is None
        or relationship is None
        or relationship["relation_type"] != table
        or relationship["source_entity_id"] != source["canonical_entity_id"]
        or relationship["target_entity_id"] != target["canonical_entity_id"]
        or relationship["evidence_span_id"] != row.get("evidence_span_id")
    ):
        raise sqlite3.IntegrityError("graph edge is not a canonical relationship projection")


def _normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def entity_link_manager(conn: sqlite3.Connection, query: str) -> str | None:
    normalized_query = _normalize(query)
    matches = []
    for row in conn.execute("SELECT manager_id,name FROM manager"):
        normalized_name = _normalize(row["name"])
        tokens = normalized_name.split()
        aliases = [" ".join(tokens[:size]) for size in range(2, len(tokens) + 1)]
        aliases = [alias for alias in aliases if alias in normalized_query]
        if aliases:
            longest = max(aliases, key=lambda alias: (len(alias), alias))
            matches.append((len(longest), normalized_name, row["manager_id"]))
    return (
        None
        if not matches
        else sorted(matches, key=lambda item: (-item[0], item[1], item[2]))[0][2]
    )


def graph_candidates(conn: sqlite3.Connection, manager_id: str) -> list[str]:
    rows = conn.execute(
        """
        SELECT doc_id FROM attributed_to WHERE manager_id=?
        UNION
        SELECT authored_by.doc_id FROM authored_by
        JOIN employed_by USING(person_id)
        JOIN entity_relationship ON entity_relationship.entity_relationship_id=employed_by.entity_relationship_id
        JOIN document ON document.doc_id=authored_by.doc_id
        WHERE employed_by.manager_id=?
          AND document.date>=substr(entity_relationship.effective_from,1,7)
          AND (entity_relationship.effective_to IS NULL OR document.date<substr(entity_relationship.effective_to,1,7))
        ORDER BY doc_id
        """,
        (manager_id, manager_id),
    )
    return [row["doc_id"] for row in rows]


def candidate_paths(conn: sqlite3.Connection, manager_id: str, doc_id: str) -> tuple[str, ...]:
    paths = []
    if conn.execute(
        "SELECT 1 FROM attributed_to WHERE manager_id=? AND doc_id=?", (manager_id, doc_id)
    ).fetchone():
        paths.append(f"attributed_to:{manager_id}")
    people = conn.execute(
        """
        SELECT authored_by.person_id FROM authored_by
        JOIN employed_by USING(person_id)
        JOIN entity_relationship ON entity_relationship.entity_relationship_id=employed_by.entity_relationship_id
        JOIN document ON document.doc_id=authored_by.doc_id
        WHERE authored_by.doc_id=? AND employed_by.manager_id=?
          AND document.date>=substr(entity_relationship.effective_from,1,7)
          AND (entity_relationship.effective_to IS NULL OR document.date<substr(entity_relationship.effective_to,1,7))
        ORDER BY authored_by.person_id
        """,
        (doc_id, manager_id),
    )
    paths.extend(f"authored_by:{row['person_id']}->employed_by:{manager_id}" for row in people)
    return tuple(sorted(paths))
