from uuid import UUID

import pytest

from fastappi_notification.domain.errors import UserNotFound
from tests.application.auth_fakes import AuthWorld


def test_devuelve_el_usuario():
    w = AuthWorld()
    user = w.registered_user()
    assert w.get_current_user.execute(user_id=user.id).id == user.id


def test_inexistente_lanza_user_not_found():
    with pytest.raises(UserNotFound):
        AuthWorld().get_current_user.execute(user_id=UUID(int=99))
