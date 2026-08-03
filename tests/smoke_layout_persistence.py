"""Direct entry point for focused layout-format coverage."""

from __future__ import annotations

import pytest

if __name__ == "__main__":
    raise SystemExit(
        pytest.main(
            [
                "-q",
                "tests/test_architecture_refactor.py",
                "-k",
                "layout_format or unsupported_version",
            ]
        )
    )
