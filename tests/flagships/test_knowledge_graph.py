import sqlite3

import pytest

from quant_allocator.flagships.knowledge.graph import (
    EDGE_TABLES,
    NODE_TABLES,
    GraphFixture,
    candidate_paths,
    connect_graph,
    entity_link_manager,
    graph_candidates,
    ingest_fixture,
    initialize_schema,
)


SPAN = "The portfolio manager described redemption gates and cash buffers."


def _row(**values):
    return {
        **values,
        "source_doc": values.get("source_doc", "MTG-2024-05"),
        "source_span": values.get("source_span", SPAN),
        "as_of": values.get("as_of", "2024-05"),
    }


def graph_fixture() -> GraphFixture:
    return GraphFixture(
        tables={
            "strategy": [_row(strategy_id="ELS", label="Equity long/short")],
            "manager": [
                _row(
                    manager_id="CLC",
                    name="Corvid Lane Capital",
                    tier="R",
                    strategy_id="ELS",
                    tier_grant_date="2024-01",
                ),
                _row(
                    manager_id="SPA",
                    name="Selby Point Advisors",
                    tier="R",
                    strategy_id="ELS",
                    tier_grant_date="2023-01",
                ),
                _row(
                    manager_id="WGC",
                    name="Wexford Green Capital",
                    tier="R",
                    strategy_id="ELS",
                    tier_grant_date="2024-01",
                ),
            ],
            "person": [
                _row(person_id="EV", name="Elena Voss", role="Portfolio manager"),
                _row(person_id="PA", name="Priya Anand", role="Portfolio manager"),
            ],
            "document": [
                _row(
                    doc_id="L-2024Q1",
                    doc_type="letter",
                    text="Corvid Lane remained comfortable with portfolio liquidity.",
                    date="2024-03",
                    file_path="authored/L-2024Q1.txt",
                    ingest_date="2024-06",
                ),
                _row(
                    doc_id="MTG-2024-05",
                    doc_type="meeting_note",
                    text=SPAN,
                    date="2024-05",
                    file_path="authored/MTG-2024-05.txt",
                    ingest_date="2024-06",
                ),
                _row(
                    doc_id="DDQ-WEX",
                    doc_type="ddq",
                    text="Wexford Green described liquidity terms.",
                    date="2024-02",
                    file_path="authored/DDQ-WEX.txt",
                    ingest_date="2024-06",
                ),
            ],
            "view": [
                _row(
                    view_id="V-LIQ",
                    direction="neutral-explicit",
                    horizon="quarterly",
                    conviction=2,
                )
            ],
            "theme": [_row(theme_id="LIQ", label="Liquidity")],
            "meeting": [
                _row(
                    meeting_id="M-2024-05",
                    date="2024-05",
                    attendees="Elena Voss",
                    linked_doc_id="MTG-2024-05",
                )
            ],
            "authored_by": [
                _row(doc_id="L-2024Q1", person_id="EV"),
                _row(doc_id="MTG-2024-05", person_id="EV"),
                _row(doc_id="DDQ-WEX", person_id="PA"),
            ],
            "attributed_to": [
                _row(doc_id="L-2024Q1", manager_id="CLC"),
                _row(doc_id="DDQ-WEX", manager_id="WGC"),
            ],
            "employed_by": [
                _row(
                    person_id="EV",
                    manager_id="CLC",
                    from_date="2024-01",
                    to_date=None,
                ),
                _row(
                    person_id="EV",
                    manager_id="SPA",
                    from_date="2020-01",
                    to_date="2023-12",
                ),
                _row(
                    person_id="PA",
                    manager_id="WGC",
                    from_date="2020-01",
                    to_date=None,
                ),
            ],
            "expresses": [_row(doc_id="MTG-2024-05", view_id="V-LIQ")],
            "about_theme": [_row(view_id="V-LIQ", theme_id="LIQ")],
            "discussed_at": [_row(view_id="V-LIQ", meeting_id="M-2024-05")],
        }
    )


def _loaded_graph():
    conn = connect_graph()
    initialize_schema(conn)
    ingest_fixture(conn, graph_fixture())
    return conn


def test_schema_has_all_typed_node_and_edge_tables():
    conn = connect_graph()
    initialize_schema(conn)
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert set(NODE_TABLES) <= tables
    assert set(EDGE_TABLES) <= tables
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    for table in (*NODE_TABLES, *EDGE_TABLES):
        foreign_keys = conn.execute(f'PRAGMA foreign_key_list("{table}")').fetchall()
        assert any(row["from"] == "source_doc" and row["table"] == "document" for row in foreign_keys)


def test_missing_or_blank_provenance_and_dangling_edge_fail():
    fixture = graph_fixture()
    for field, value in (("source_span", None), ("source_span", "  "), ("as_of", "")):
        bad_view = {**fixture.tables["view"][0], field: value}
        bad_tables = {**fixture.tables, "view": [bad_view]}
        conn = connect_graph()
        initialize_schema(conn)
        with pytest.raises(sqlite3.IntegrityError):
            ingest_fixture(conn, GraphFixture(bad_tables))

    bad_strategy = {**fixture.tables["strategy"][0], "source_doc": "MISSING"}
    conn = connect_graph()
    initialize_schema(conn)
    with pytest.raises(sqlite3.IntegrityError):
        ingest_fixture(conn, GraphFixture({**fixture.tables, "strategy": [bad_strategy]}))

    conn = connect_graph()
    initialize_schema(conn)
    dangling = _row(doc_id="MISSING", person_id="EV")
    bad_tables = {**fixture.tables, "authored_by": [dangling]}
    with pytest.raises(sqlite3.IntegrityError):
        ingest_fixture(conn, GraphFixture(bad_tables))


def test_entity_linking_is_longest_normalized_manager_match():
    conn = _loaded_graph()
    conn.execute(
        """INSERT INTO manager VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "CL",
            "Corvid Lane",
            "R",
            "ELS",
            "2024-01",
            "L-2024Q1",
            "Corvid Lane remained comfortable with portfolio liquidity.",
            "2024-03",
        ),
    )
    assert entity_link_manager(conn, "What did Corvid-Lane Capital say?") == "CLC"


def test_one_hop_author_employment_recovers_note_and_excludes_wrong_firm():
    conn = _loaded_graph()
    candidates = graph_candidates(conn, "CLC")
    assert candidates == ["L-2024Q1", "MTG-2024-05"]
    assert "DDQ-WEX" not in candidates
    assert candidate_paths(conn, "CLC", "MTG-2024-05") == (
        "authored_by:EV->employed_by:CLC",
    )


def test_no_theme_based_two_hop_expansion():
    conn = _loaded_graph()
    # Wexford uses the same liquidity theme in its text, but no manager/person edge
    # connects it to Corvid. Theme similarity alone must not expand the candidate set.
    assert "DDQ-WEX" not in graph_candidates(conn, "CLC")


def test_author_employment_path_respects_current_and_historical_intervals():
    fixture = graph_fixture()
    tables = {name: list(rows) for name, rows in fixture.tables.items()}
    tables["document"].append(
        _row(
            doc_id="L-2023Q3-EV",
            doc_type="letter",
            text="Elena Voss wrote this Selby Point letter before leaving the firm.",
            date="2023-09",
            file_path="authored/L-2023Q3-EV.txt",
            ingest_date="2024-06",
        )
    )
    tables["authored_by"].append(_row(doc_id="L-2023Q3-EV", person_id="EV"))
    conn = connect_graph()
    initialize_schema(conn)
    ingest_fixture(conn, GraphFixture(tables))

    assert graph_candidates(conn, "CLC") == ["L-2024Q1", "MTG-2024-05"]
    assert graph_candidates(conn, "SPA") == ["L-2023Q3-EV"]
    assert candidate_paths(conn, "SPA", "L-2023Q3-EV") == (
        "authored_by:EV->employed_by:SPA",
    )
    assert candidate_paths(conn, "SPA", "L-2024Q1") == ()
    assert candidate_paths(conn, "CLC", "L-2023Q3-EV") == ()
