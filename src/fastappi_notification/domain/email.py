"""Value object `Email` (ADR-013). Dominio puro: solo stdlib.

`EMAIL_PATTERN` y `MAX_EMAIL_LENGTH` son la única definición de "email válido";
`EmailPolicy` (canal email) las reutiliza.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from fastappi_notification.domain.errors import InvalidEmail

EMAIL_PATTERN = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
MAX_EMAIL_LENGTH = 320


@dataclass(frozen=True)
class Email:
    value: str

    @classmethod
    def create(cls, raw: str) -> Email:
        """Normaliza (trim + minúsculas) y valida; inválido -> `InvalidEmail`."""
        value = raw.strip().lower()
        if len(value) > MAX_EMAIL_LENGTH or EMAIL_PATTERN.fullmatch(value) is None:
            raise InvalidEmail()
        return cls(value)

    def __str__(self) -> str:
        return self.value
