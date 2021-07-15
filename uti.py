#!/usr/bin/env python

from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass, field
import re
from itertools import chain
import string
import logging
from pathlib import Path

import pandas as pd
import yaml
import yamlloader
import defopt

try:
    from coloredlogs import ColoredFormatter as Formatter
except ImportError:
    from logging import Formatter

if TYPE_CHECKING:
    from typing import List, Union, Dict, Set, Iterable, Any

__version__ = '0.1.0'

logger = logging.getLogger('uti')
handler = logging.StreamHandler()
logger.addHandler(handler)
handler.setFormatter(Formatter('%(name)s %(levelname)s %(message)s'))
logger.setLevel(level=logging.INFO)


def union(*args: Iterable) -> set:
    """A union function similar to set.union method."""
    return set(chain.from_iterable(*args))


def filter_string(text: str) -> str:
    """filter out non-printable characters from string.

    Some non-printable character such as non-printable space exists in Apple's table."""
    return ''.join(filter(lambda x: x in string.printable, text))


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


def parse_node(text: str, regex=re.compile(r'^([\w.-]+)( \(\w+\))?$')) -> str:
    """Parse the UTI from column 1

    of first table in https://developer.apple.com/library/archive/documentation/Miscellaneous/Reference/UTIRef/Articles/System-DeclaredUniformTypeIdentifiers.html"""
    res = regex.search(filter_string(text))
    return res.group(1)


def parse_parent(text: str, regex=re.compile(r'[\w.-]+')) -> List[str]:
    """Parse the UTI from column 2

    of first table in https://developer.apple.com/library/archive/documentation/Miscellaneous/Reference/UTIRef/Articles/System-DeclaredUniformTypeIdentifiers.html"""
    if text == "-":
        return []
    else:
        res = regex.findall(filter_string(text))
        # probably a typo
        return ['public.mpeg-4' if uti == 'public.mpeg4' else uti for uti in res]


@dataclass(order=True)
class Node:
    name: str

    def __post_init__(self):
        self.parents = []
        self.children = []

    def __hash__(self) -> int:
        return hash(self.name)

    def __str__(self) -> str:
        return self.name

    @property
    def grandparents(self) -> Set[Node]:
        """Return the ultimate grandparents containing self."""
        if self.parents:
            return union(parent.grandparents for parent in self.parents)
        else:
            return {self, }

    @property
    def proper_grandparents(self) -> List[Node]:
        """Return the ultimate grandparents without self."""
        return sorted(grandparent for grandparent in self.grandparents if grandparent is not self)

    @property
    def children_and_grandchildren(self) -> Set[Node]:
        """Return children recursively containing self."""
        if self.children:
            children_set = set(self.children)
            return children_set.union(*(child.children_and_grandchildren for child in self.children))
        else:
            return {self, }

    @property
    def proper_children_and_grandchildren(self) -> List[Node]:
        """Return children recursively without self."""
        return sorted(children_and_grandchildren for children_and_grandchildren in self.children_and_grandchildren if children_and_grandchildren is not self)

    @property
    def tree(self) -> Union[Node, Dict[Node, list]]:
        """Construct a tree of children and its children recursively."""
        if self.children:
            return {
                self: [child.tree for child in self.children]
            }
        else:
            return self


def get_name_to_node(
    url: str = 'https://developer.apple.com/library/archive/documentation/Miscellaneous/Reference/UTIRef/Articles/System-DeclaredUniformTypeIdentifiers.html',
) -> Dict[str, Node]:
    """Return a dict from name to a node with that name."""
    dfs = pd.read_html(url)
    df = dfs[0]
    logger.info('Obtained a table from %s with shape %s', url, df.shape)

    name_to_node: Dict[str, Node] = {}
    for i, row in df.iterrows():
        try:
            name = parse_node(row.iloc[0])
        except Exception:
            raise RuntimeError(f'Cannot parse {name} in row {i}')
        if name not in name_to_node:
            name_to_node[name] = node = Node(name)
        else:
            node = name_to_node[name]

        parent_names = parse_parent(row.iloc[1])
        if parent_names:
            for parent_name in parent_names:
                if parent_name not in name_to_node:
                    name_to_node[parent_name] = parent = Node(parent_name)
                else:
                    parent = name_to_node[parent_name]
                node.parents.append(parent)
                parent.children.append(node)
    logger.info('Obtained %s UTIs.', len(name_to_node))

    name_to_node = dict(sorted(name_to_node.items()))
    return name_to_node


def get_tree(name_to_node: Dict[str, Node]) -> List[Dict[Node, dict]]:
    grandgrandparents = union(node.proper_grandparents for node in name_to_node.values())
    logger.info('Obtained %s top level UTIs.', len(grandgrandparents))
    grandgrandparents = sorted(grandgrandparents)
    tree = [grandgrandparent.tree for grandgrandparent in grandgrandparents]
    return tree


def main(
    url: str = 'https://developer.apple.com/library/archive/documentation/Miscellaneous/Reference/UTIRef/Articles/System-DeclaredUniformTypeIdentifiers.html',
    *,
    tree_path: Path = Path('dist/UTI-tree.yml'),
    children_path: Path = Path('dist/UTI-children.yml'),
):
    """Parse Apple UTI table to usable data structure and dump to YAML.

    :param url: url to Apple's UTI table.
    :param tree_path: path to dump a tree structure of the UTI in YAML.
    :param children_path: path to dump a mapping from UTI to all children in YAML.
    """
    name_to_node = get_name_to_node(url=url)

    children = {name: node.proper_children_and_grandchildren for name, node in name_to_node.items()}
    children_path.parent.mkdir(parents=True, exist_ok=True)
    with children_path.open('w') as f:
        yaml.dump(stringify(children), f, Dumper=yamlloader.ordereddict.CSafeDumper, default_flow_style=False)

    tree = get_tree(name_to_node)
    tree_path.parent.mkdir(parents=True, exist_ok=True)
    with tree_path.open('w') as f:
        yaml.dump(stringify(tree), f, Dumper=yamlloader.ordereddict.CSafeDumper, default_flow_style=False)


def cli():
    defopt.run(main)


if __name__ == "__main__":
    cli()
