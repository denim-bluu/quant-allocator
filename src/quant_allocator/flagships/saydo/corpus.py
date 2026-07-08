"""Shared say-do synthetic corpus (E3 §6.4 substrate; M5 letter baseline).

Authored constants, RNG-free (the demo-facts-are-authored discipline, E3 §8 ruling 4).
build_corpus() returns LETTERS only (the byte-identical baseline); the DDQ and
meeting-note emitters are added behind include_ddq_and_notes=False so the letter corpus is
unchanged when the flag is off. planted_relevance() carries the query -> relevant-document
ground truth planted at generation time, reproducing the E3 §3.2 worked example so the
retrieval eval is measurable without human annotation.

Fictional names only (E3 §8 ruling 6): Corvid Lane Capital, Selby Point Advisors,
Wexford Green Capital, Elena Voss, Priya Anand. No real firms; no banned brand names.
"""

from __future__ import annotations

from dataclasses import dataclass

_DOC_TYPES = ("letter", "ddq", "meeting_note")


@dataclass(frozen=True)
class Document:
    doc_id: str
    doc_type: str  # one of _DOC_TYPES
    manager_code: str
    author: str
    text: str
    as_of: str  # "YYYY-MM"


# --- Letters: the flag-off baseline. Authored constants. ---
_LETTERS: tuple[Document, ...] = (
    Document(
        doc_id="L-2024Q1",
        doc_type="letter",
        manager_code="CLC",
        author="Elena Voss",
        as_of="2024-03",
        text=(
            "In the first quarter we remained comfortable with portfolio liquidity and "
            "kept the book positioned for a range of outcomes. Corvid Lane continues to "
            "favour durable cash generators over crowded momentum names."
        ),
    ),
    Document(
        doc_id="L-2023Q4",
        doc_type="letter",
        manager_code="SPA",
        author="Priya Anand",
        as_of="2023-12",
        text=(
            "Selby Point closed the year with a modest net long and a value tilt. We "
            "trimmed several positions into strength and added to higher-quality names."
        ),
    ),
)

# --- DDQs + meeting notes: added only when include_ddq_and_notes=True. ---
_DDQS_AND_NOTES: tuple[Document, ...] = (
    Document(
        doc_id="DDQ-2024",
        doc_type="ddq",
        manager_code="CLC",
        author="Corvid Lane Capital",
        as_of="2024-02",
        text=(
            "Liquidity terms: the fund offers quarterly redemption with ninety day "
            "notice. Corvid Lane maintains a documented liquidity policy reviewed by the "
            "risk committee."
        ),
    ),
    Document(
        doc_id="DDQ-WEX",  # distractor: right topic (liquidity), WRONG firm.
        doc_type="ddq",
        manager_code="WGC",
        author="Wexford Green Capital",
        as_of="2024-02",
        text=(
            "Liquidity and notice terms: investors may redeem semi-annually subject to "
            "standard notice. Wexford Green publishes its liquidity framework annually."
        ),
    ),
    Document(
        doc_id="MTG-2024-05",  # the paraphrase hero: on-topic, shares NO query token.
        doc_type="meeting_note",
        manager_code="CLC",
        author="Elena Voss",
        as_of="2024-05",
        text=(
            "The portfolio manager walked through how redemption gates would apply under "
            "stress and how she sizes cash buffers against a wave of withdrawals. She "
            "described the order in which sleeves would be raised."
        ),
    ),
)


def build_corpus(include_ddq_and_notes: bool = False) -> list[Document]:
    """Authored corpus. Letters only by default (byte-identical baseline); DDQs and
    meeting notes appended when the flag is on. Deterministic order, RNG-free."""
    docs = list(_LETTERS)
    if include_ddq_and_notes:
        docs.extend(_DDQS_AND_NOTES)
    return docs


def planted_relevance() -> list[dict]:
    """Query -> planted relevant-document ground truth (E3 §3.2 / §6.4). The relevant set
    references DDQ/meeting-note docs, so the retrieval eval builds the corpus with the flag
    on. The Wexford Green DDQ (DDQ-WEX) is a deliberate distractor and is NOT relevant."""
    return [
        {
            "query_id": "Q1",
            "query": "corvid lane liquidity 2024",
            "theme": "liquidity",
            "entity": "Corvid Lane Capital",
            "relevant_doc_ids": ("L-2024Q1", "DDQ-2024", "MTG-2024-05"),
        }
    ]
