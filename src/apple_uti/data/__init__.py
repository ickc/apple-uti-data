from __future__ import annotations

from typing import TYPE_CHECKING
from importlib import resources

if TYPE_CHECKING:
    from pathlib import Path, Optional

DATA_PATH: Optional[Path]
try:
    with resources.path(__package__, 'data.yml') as path:
        DATA_PATH = path
except FileNotFoundError:
        DATA_PATH = None
