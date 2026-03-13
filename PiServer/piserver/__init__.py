"""PiServer package.

Expose create_app lazily so importing the package does not eagerly import
piserver.app during package initialisation.
"""

from __future__ import annotations


def create_app(*args, **kwargs):
    from .app import create_app as _create_app
    return _create_app(*args, **kwargs)


__all__ = ["create_app"]
