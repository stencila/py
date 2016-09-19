import pytest

slow = pytest.mark.skipif(
    not pytest.config.getoption("--all"),
    reason="Needs --all option to run"
)
