from __future__ import annotations

from typing import TYPE_CHECKING
from functools import cached_property
from dataclasses import dataclass
from logging import getLogger
import string
import re

import pandas as pd

from .util import union, stringify

if TYPE_CHECKING:
    from typing import List, Union, Dict, Set

logger = getLogger('pantable')


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


@dataclass
class UtiFromWeb:
    url: str = 'https://developer.apple.com/library/archive/documentation/Miscellaneous/Reference/UTIRef/Articles/System-DeclaredUniformTypeIdentifiers.html'

    @staticmethod
    def filter_string(text: str) -> str:
        """filter out non-printable characters from string.

        Some non-printable character such as non-printable space exists in Apple's table."""
        return ''.join(filter(lambda x: x in string.printable, text))

    @staticmethod
    def parse_node(text: str, regex=re.compile(r'^([\w.-]+)( \(\w+\))?$')) -> str:
        """Parse the UTI from column 1

        of first table in https://developer.apple.com/library/archive/documentation/Miscellaneous/Reference/UTIRef/Articles/System-DeclaredUniformTypeIdentifiers.html"""
        res = regex.search(UtiFromWeb.filter_string(text))
        return res.group(1)

    @staticmethod
    def parse_parent(text: str, regex=re.compile(r'[\w.-]+')) -> List[str]:
        """Parse the UTI from column 2

        of first table in https://developer.apple.com/library/archive/documentation/Miscellaneous/Reference/UTIRef/Articles/System-DeclaredUniformTypeIdentifiers.html"""
        if text == "-":
            return []
        else:
            res = regex.findall(UtiFromWeb.filter_string(text))
            # probably a typo
            return ['public.mpeg-4' if uti == 'public.mpeg4' else uti for uti in res]

    @cached_property
    def name_to_node(
        self,
    ) -> Dict[str, Node]:
        """Return a dict from name to a node with that name."""
        url = self.url

        dfs = pd.read_html(url)
        df = dfs[0]
        logger.info('Obtained a table from %s with shape %s', url, df.shape)

        name_to_node: Dict[str, Node] = {}
        for i, row in df.iterrows():
            try:
                name = self.parse_node(row.iloc[0])
            except Exception:
                raise RuntimeError(f'Cannot parse {name} in row {i}')
            if name not in name_to_node:
                name_to_node[name] = node = Node(name)
            else:
                node = name_to_node[name]

            parent_names = self.parse_parent(row.iloc[1])
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

    @property
    def tree(self) -> List[Dict[Node, dict]]:
        name_to_node = self.name_to_node

        grandgrandparents = union(node.proper_grandparents for node in name_to_node.values())
        logger.info('Obtained %s top level UTIs.', len(grandgrandparents))
        grandgrandparents = sorted(grandgrandparents)
        tree = [grandgrandparent.tree for grandgrandparent in grandgrandparents]
        return tree

    @property
    def children(self) -> Dict[str, List[Node]]:
        name_to_node = self.name_to_node

        return {name: node.proper_children_and_grandchildren for name, node in name_to_node.items()}

    @property
    def tree_json_like(self) -> List[Dict[str, dict]]:
        return stringify(self.tree)

    @property
    def children_json_like(self) -> List[Dict[str, dict]]:
        return stringify(self.children)
