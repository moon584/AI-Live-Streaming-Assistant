"""Compatibility shim: export `db` from the improved `db_backend` implementation.

This module previously contained a full Database implementation duplicated in the
repo. To safely merge the implementations we now delegate to `db_backend.Database`
while keeping the old module name (`database`) for backwards compatibility.

Callers can continue to use `from database import db` until we complete the
migration. After downstream code has been updated we can remove this shim.
"""

from db_backend import db

__all__ = ["db"]