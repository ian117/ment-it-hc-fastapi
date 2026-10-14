"""Value object `PasswordHash` (ADR-013). Envuelve el string que produce el `PasswordHasher`."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PasswordHash:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            # Error de programación (un hasher que devuelve vacío), no una regla de dominio.
            raise ValueError("PasswordHash cannot be empty")

    def __repr__(self) -> str:
        return "PasswordHash(<redacted>)"
