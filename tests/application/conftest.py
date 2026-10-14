import pytest

from tests.application.auth_fakes import AuthWorld
from tests.application.fakes import World


@pytest.fixture
def world() -> World:
    return World()


@pytest.fixture
def auth_world() -> AuthWorld:
    return AuthWorld()
