"""Worker subprocess entry point."""

from __future__ import annotations

import sys
from typing import List, Optional


def main(argv: Optional[List[str]] = None) -> int:
    raise NotImplementedError("filled by SL-1")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
