#!/usr/bin/env python

from __future__ import annotations

from logging import getLogger
import defopt

from .core import UtiFromWeb, UtiFromSystem, UtiFromAll

logger = getLogger('apple_uti')


def cli():
    uti = defopt.run(
        {
            'web': UtiFromWeb,
            'system': UtiFromSystem,
            'all': UtiFromAll,
        },
        strict_kwonly=False,
        show_types=True,
    )
    uti.run_all()


if __name__ == "__main__":
    cli()
