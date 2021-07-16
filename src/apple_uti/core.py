from __future__ import annotations

from typing import TYPE_CHECKING
from pathlib import Path
from functools import cached_property
from dataclasses import dataclass
from logging import getLogger
import string
import re

import pandas as pd

from .util import union, stringify

if TYPE_CHECKING:
    from typing import List, Union, Dict, Set, Tuple, Optional

logger = getLogger('apple_uti')


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
class Uti:

    @property
    def data(self) -> Dict[str, List[str]]:
        raise NotImplementedError

    @cached_property
    def name_to_node(
        self,
    ) -> Dict[str, Node]:
        """Return a dict from name to a node with that name."""
        data = self.data

        name_to_node: Dict[str, Node] = {}
        for name, parent_names in data.items():
            if name not in name_to_node:
                name_to_node[name] = node = Node(name)
            else:
                node = name_to_node[name]
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

    @cached_property
    def tree(self) -> List[Dict[Node, dict]]:
        name_to_node = self.name_to_node

        grandgrandparents = union(node.proper_grandparents for node in name_to_node.values())
        logger.info('Obtained %s top level UTIs.', len(grandgrandparents))
        grandgrandparents = sorted(grandgrandparents)
        tree = [grandgrandparent.tree for grandgrandparent in grandgrandparents]
        return tree

    @cached_property
    def children(self) -> Dict[str, List[Node]]:
        name_to_node = self.name_to_node

        return {name: node.proper_children_and_grandchildren for name, node in name_to_node.items()}

    @cached_property
    def tree_json_like(self) -> List[Dict[str, dict]]:
        return stringify(self.tree)

    @cached_property
    def children_json_like(self) -> List[Dict[str, dict]]:
        return stringify(self.children)


@dataclass
class UtiFromWeb(Uti):
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
    def table(
        self,
    ) -> pd.DataFrame:
        url = self.url
        dfs = pd.read_html(url)
        df = dfs[0]
        logger.info('Obtained a table from %s with shape %s', url, df.shape)
        return df

    @cached_property
    def data(self) -> Dict[str, List[str]]:
        return {
            self.parse_node(row.iloc[0]):
            self.parse_parent(row.iloc[1])
            for _, row in self.table.iterrows()
        }


@dataclass
class UtiFromSystem(Uti):
    path: Path = Path('/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister')

    def __post_init__(self):
        import platform

        assert platform.system() == 'Darwin'
        assert self.path.is_file()

    @cached_property
    def get_lsregister_dump(self) -> str:
        import subprocess

        cmd = [
            str(self.path),
            '-dump',
        ]
        logger.info('Running %s', subprocess.list2cmdline(cmd))
        res = subprocess.run(cmd, capture_output=True, check=True)
        logger.info('Obtained data from lsregister.')
        return res.stdout.decode()

    @staticmethod
    def split_lsregister_dump(
        text: str,
        regex=re.compile(r'\n-+\n'),
    ) -> Tuple[str, List[str]]:
        temp = regex.split(text)
        # summary, list of data
        return temp[0], temp[1:]

    @staticmethod
    def parse_datum(
        text: str,
        regex=re.compile(r'\n([\w -]+): +(.+)'),
    ) -> Dict[str, str]:
        return dict(regex.findall('\n' + text))

    @staticmethod
    def get_keys(
        text: str,
        regex=re.compile(r'^([^ ][^:]*):'),
    ) -> List[str]:
        keys = []
        for line in text.split('\n'):
            res = regex.findall(line)
            assert len(res) < 2
            if len(res) == 1:
                keys.append(res[0])
        return keys

    @staticmethod
    def parse_parent(text: Optional[str]) -> List[str]:
        """Parse the UTI from "conforms to" column.
        """
        if type(text) is str:
            return [i.strip() for i in text.split(',')]
        else:
            return []

    @cached_property
    def table(self):
        text = self.get_lsregister_dump
        summary, data = self.split_lsregister_dump(text)
        logger.info('lsregister summary:\n%s', summary)

        # sanity check
        for i, datum in enumerate(data):
            keys = self.get_keys(datum)
            dict_ = self.parse_datum(datum)
            assert set(keys) == set(dict_.keys())

        df = pd.DataFrame([self.parse_datum(datum) for datum in data])
        df_uti = df[~df.uti.isna()].dropna(axis=1, how='all')
        logger.info('Obtained a table with shape %s', df_uti.shape)
        return df_uti

    @cached_property
    def data(self) -> Dict[str, List[str]]:
        from collections import defaultdict

        df_uti = self.table

        temp: Dict[str, Set[str]] = defaultdict(set)
        for _, row in df_uti.iterrows():
            temp[row.uti].update(self.parse_parent(row['conforms to']))
        logger.info('Consolidated data into %s unique UTIs.', len(temp))
        for name, parents in temp.items():
            if name in parents:
                logger.warning('%s in %s', name, parents)
                parents.remove(name)
        res = {key: sorted(value) for key, value in temp.items()}
        return res
