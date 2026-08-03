"""Direct entry point for the focused pytest cursor-domain coverage."""

from __future__ import annotations

import pytest

if __name__ == "__main__":
    raise SystemExit(
        pytest.main(["-q", "tests/test_architecture_refactor.py", "-k", "cursor_domain or pair_indices"])
    )
