"""Direct entry point for the focused pytest public-component coverage."""

from __future__ import annotations

import pytest

if __name__ == "__main__":
    raise SystemExit(
        pytest.main(["-q", "tests/test_architecture_refactor.py", "-k", "components_are_independent"])
    )
