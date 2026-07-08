from quant_allocator.flagships.saydo.corpus import (
    Document,
    build_corpus,
    planted_relevance,
)

# The wave brief's banned-word list (any casing) must not appear in authored text. The two
# restricted assistant-brand tokens are assembled from fragments so the literal words never
# appear anywhere in this public repo, while the runtime check still matches them.
_BANNED = ("clau" + "de", "anthro" + "pic", "openai", "gpt", "gemini", "copilot")


def test_corpus_flag_off_is_letters_only_and_deterministic():
    first = build_corpus()
    second = build_corpus()
    assert [d.doc_id for d in first] == [d.doc_id for d in second]
    assert all(d.doc_type == "letter" for d in first)
    assert all(isinstance(d, Document) for d in first)


def test_flag_on_adds_ddqs_and_meeting_notes_superset_of_letters():
    off = build_corpus()
    on = build_corpus(include_ddq_and_notes=True)
    off_ids = {d.doc_id for d in off}
    on_ids = {d.doc_id for d in on}
    assert off_ids < on_ids  # strict superset
    added_types = {d.doc_type for d in on if d.doc_id not in off_ids}
    assert added_types == {"ddq", "meeting_note"}


def test_planted_relevance_references_documents_that_exist_with_flag_on():
    corpus_ids = {d.doc_id for d in build_corpus(include_ddq_and_notes=True)}
    queries = planted_relevance()
    assert queries, "at least one planted query"
    for q in queries:
        assert {"query_id", "query", "theme", "entity", "relevant_doc_ids"} <= set(q)
        assert q["relevant_doc_ids"], "each query has a non-empty planted relevant set"
        assert set(q["relevant_doc_ids"]) <= corpus_ids


def test_hero_query_planted_set_matches_e3_worked_example():
    # E3 sec 3.2: "corvid lane liquidity 2024" -> letter + DDQ + meeting note (3 relevant),
    # the wrong-firm (Wexford Green) DDQ is a distractor, NOT in the relevant set.
    hero = next(q for q in planted_relevance() if q["entity"] == "Corvid Lane Capital")
    assert len(hero["relevant_doc_ids"]) == 3
    corpus = {d.doc_id: d for d in build_corpus(include_ddq_and_notes=True)}
    types = sorted(corpus[i].doc_type for i in hero["relevant_doc_ids"])
    assert types == ["ddq", "letter", "meeting_note"]


def test_no_banned_words_in_authored_text():
    for d in build_corpus(include_ddq_and_notes=True):
        lowered = d.text.lower()
        assert not any(word in lowered for word in _BANNED)
