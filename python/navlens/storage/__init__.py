"""Shared local-storage primitives for infrastructure adapters."""

from .atomic import atomic_write_bytes

__all__ = ["atomic_write_bytes"]
