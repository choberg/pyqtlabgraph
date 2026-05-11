from __future__ import annotations

from pathlib import Path
import re
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import pyqt_lab_graph


def main() -> int:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"\s*$', pyproject)
    assert match is not None
    expected_version = match.group(1)
    assert pyqt_lab_graph.__version__ == expected_version

    print("version metadata smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
