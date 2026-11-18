"""The shared helpers fail as a test module's asserts do, with the values they compared."""

from collections.abc import Callable

import pytest
from helpers import dependencies, live_secrets


@pytest.mark.parametrize("helper", [dependencies, live_secrets])
def test_a_shared_assert_reports_what_it_compared(
    helper: Callable[[dict[str, object]], object],
) -> None:
    """``conftest.py`` registers ``helpers`` for pytest's assertion rewriting before it is
    imported, so an assert there that fails names the value, as it did in the test module
    the helpers came from; a plain import leaves the message empty."""
    answers: dict[str, object] = {"source_dependencies": "{name: x}", "live_secrets": "{name: x}"}
    with pytest.raises(AssertionError, match=r"isinstance\(\{'name': 'x'\}, list\)"):
        helper(answers)
