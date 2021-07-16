from __future__ import annotations

from typing import TYPE_CHECKING
from importlib import resources

if TYPE_CHECKING:
    from pathlib import Path

with resources.path(__package__, 'data.yml') as path:
    DATA_PATH: Path = path
