"""ADR-015: en producción la app no arranca con un JWT_SECRET inseguro."""

import pytest
from pydantic import ValidationError

from fastappi_notification.core.config import (
    DEV_JWT_SECRET,
    MIN_PRODUCTION_JWT_SECRET_LENGTH,
    Settings,
)

STRONG = "x" * MIN_PRODUCTION_JWT_SECRET_LENGTH


def build(**kwargs) -> Settings:
    # Ignora el .env del desarrollador: solo cuenta lo que pasa el test.
    return Settings(_env_file=None, **kwargs)


@pytest.mark.parametrize("environment", ["development", "test"])
def test_outside_production_the_dev_default_is_allowed(environment):
    assert build(environment=environment).jwt_secret == DEV_JWT_SECRET


def test_outside_production_a_short_secret_is_allowed():
    assert build(environment="development", jwt_secret="corto").jwt_secret == "corto"


def test_production_accepts_a_long_own_secret():
    assert build(environment="production", jwt_secret=STRONG).jwt_secret == STRONG


@pytest.mark.parametrize("secret", [DEV_JWT_SECRET, "randomword"])
def test_production_rejects_known_dev_secrets(secret):
    with pytest.raises(ValidationError, match="conocido"):
        build(environment="production", jwt_secret=secret)


def test_production_rejects_the_default_when_no_secret_is_given():
    with pytest.raises(ValidationError, match="conocido"):
        build(environment="production")


def test_production_rejects_a_short_secret():
    with pytest.raises(ValidationError, match="al menos 32"):
        build(environment="production", jwt_secret="x" * (MIN_PRODUCTION_JWT_SECRET_LENGTH - 1))
