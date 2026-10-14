import pytest

from tests.application.fakes import World


@pytest.fixture
def world() -> World:
    return World()
