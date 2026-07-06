import pytest

from quant_allocator.flagships.saydo.alignment import (
    DIRECTIONS,
    score_alignment,
)


def test_planted_contradiction_labels_contradicted():
    # Worked rule (M5 spec §3.2): stated short/cautious + measured move against by >= delta.
    assert score_alignment("short/cautious", move=+0.6, delta=0.5) == "contradicted"


def test_planted_aligned_labels_aligned():
    assert score_alignment("long/constructive", move=+0.6, delta=0.5) == "aligned"


def test_long_view_scoring():
    assert score_alignment("long/constructive", move=+0.15, delta=0.10) == "aligned"
    assert score_alignment("long/constructive", move=+0.05, delta=0.10) == "partial"
    assert score_alignment("long/constructive", move=-0.15, delta=0.10) == "contradicted"


def test_short_view_scoring():
    assert score_alignment("short/cautious", move=-0.15, delta=0.10) == "aligned"
    assert score_alignment("short/cautious", move=-0.05, delta=0.10) == "partial"
    assert score_alignment("short/cautious", move=+0.15, delta=0.10) == "contradicted"


def test_neutral_view_scoring():
    assert score_alignment("neutral-explicit", move=0.02, delta=0.05) == "aligned"
    assert score_alignment("neutral-explicit", move=-0.02, delta=0.05) == "aligned"
    assert score_alignment("neutral-explicit", move=0.20, delta=0.05) == "contradicted"


def test_boundary_at_exactly_delta_is_material():
    assert score_alignment("long/constructive", move=+0.10, delta=0.10) == "aligned"
    assert score_alignment("short/cautious", move=+0.10, delta=0.10) == "contradicted"


def test_every_label_is_in_the_allowed_set():
    labels = {
        score_alignment(d, move=m, delta=0.10)
        for d in DIRECTIONS
        for m in (-0.3, -0.05, 0.0, 0.05, 0.3)
    }
    assert labels <= {"aligned", "partial", "contradicted"}


def test_unknown_direction_raises():
    with pytest.raises(ValueError):
        score_alignment("mildly bullish", move=0.1, delta=0.1)
