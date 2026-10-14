from uuid import UUID

import pytest

from fastappi_notification.domain.errors import NotificationNotFound
from tests.application.fakes import OTHER, OWNER, SMS_OK, World


def test_devuelve_la_notificacion_propia():
    w = World()
    n = w.create.execute(owner_id=OWNER, title="t", content="c", channel="sms", recipient=SMS_OK)
    assert w.get.execute(OWNER, n.id).id == n.id


def test_inexistente_lanza_not_found():
    with pytest.raises(NotificationNotFound):
        World().get.execute(OWNER, UUID(int=99))


def test_ajena_lanza_not_found_igual_que_inexistente():
    w = World()
    n = w.create.execute(owner_id=OWNER, title="t", content="c", channel="sms", recipient=SMS_OK)
    with pytest.raises(NotificationNotFound):
        w.get.execute(OTHER, n.id)
