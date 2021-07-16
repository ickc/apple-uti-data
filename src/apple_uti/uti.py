#!/usr/bin/env python

from __future__ import annotations

from logging import getLogger
from pathlib import Path

import yaml
import yamlloader
import defopt

from .core import UtiFromWeb

logger = getLogger('apple_uti')


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
    uti = UtiFromWeb(url=url)

    children_path.parent.mkdir(parents=True, exist_ok=True)
    with children_path.open('w') as f:
        yaml.dump(uti.children_json_like, f, Dumper=yamlloader.ordereddict.CSafeDumper, default_flow_style=False)

    tree_path.parent.mkdir(parents=True, exist_ok=True)
    with tree_path.open('w') as f:
        yaml.dump(uti.tree_json_like, f, Dumper=yamlloader.ordereddict.CSafeDumper, default_flow_style=False)


def cli():
    defopt.run(main)


if __name__ == "__main__":
    cli()
