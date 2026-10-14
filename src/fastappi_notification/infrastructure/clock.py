"""Adaptadores triviales de los puertos `Clock` e `IdGenerator`."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class UuidIdGenerator:
    def new_id(self) -> UUID:
        return uuid4()
