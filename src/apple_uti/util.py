from __future__ import annotations

from typing import TYPE_CHECKING
from collections import defaultdict
from itertools import chain

if TYPE_CHECKING:
    from typing import Union, Iterable, Any, Dict, Set


def union(*args: Iterable) -> set:
    """A union function similar to set.union method."""
    return set(chain.from_iterable(*args))


def merge_data(*args: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    res: Dict[str, Set[str]] = defaultdict(set)
    for data in args:
        for key, value in data.items():
            res[key] |= value
    return res


def stringify(data: Union[list, dict, str, Any]) -> Union[list, dict, str]:
    """Apply str to any types that is not a list, dict, or str recursively."""
    type_ = type(data)
    if type_ is list:
        return [stringify(datum) for datum in data]
    elif type_ is dict:
        return {stringify(key): stringify(value) for key, value in data.items()}
    elif type_ is str:
        return data
    else:
        return str(data)
