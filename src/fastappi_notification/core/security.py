import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from .config import get_settings

# argon2 como esquema recomendado. `PasswordHash.recommended()` deja lugar a
# migrar de esquema sin reescribir hashes viejos si algún día cambia la política.
_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _password_hash.verify(password, hashed)


def create_access_token(subject: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Decodifica y valida firma/expiración. Lanza jwt.PyJWTError si algo falla."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def generate_reset_token() -> tuple[str, str]:
    """Devuelve (token_en_claro, token_hasheado).

    Al cliente le entregamos el token en claro; en la base guardamos solo su
    hash. Así, robar la fila de la base no alcanza para resetear la contraseña
    (criterio 4): sin el valor en claro no se puede reconstruir.
    """
    raw = secrets.token_urlsafe(32)
    return raw, hash_reset_token(raw)


def hash_reset_token(raw: str) -> str:
    # SHA-256 y no argon2: el token ya es de alta entropía y aleatorio, no un
    # secreto humano débil. Necesitamos un hash rápido y determinístico para
    # poder buscar por él en la base.
    return hashlib.sha256(raw.encode()).hexdigest()
