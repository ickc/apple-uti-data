#!/usr/bin/env python

from __future__ import annotations

from logging import getLogger
import defopt

from .core import UtiFromWeb, UtiFromSystem, UtiFromFile, UtiFromAll

logger = getLogger('apple_uti')


def cli():
    uti = defopt.run(
        {
            'web': UtiFromWeb,
            'system': UtiFromSystem,
            'file': UtiFromFile,
            'all': UtiFromAll,
        },
        strict_kwonly=False,
        show_types=True,
    )
    uti.run_all()


if __name__ == "__main__":
    cli()
