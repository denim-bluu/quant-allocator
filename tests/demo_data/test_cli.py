import pytest

from quant_allocator.demo_data.__main__ import main


def test_build_unknown_card_errors():
    with pytest.raises(SystemExit):
        main(["build", "does-not-exist"])


def test_build_all_with_empty_registry_is_a_noop():
    # Registry is empty until the S1/M5 generator tasks register their builders.
    assert main(["build", "all"]) == 0
