from uuid import UUID

import pytest

from fastappi_notification.domain.errors import NotificationNotFound
from fastappi_notification.domain.notification import Notification
from tests.application.fakes import OTHER, OWNER, SMS_OK, World


def crear(w: World):
    return w.create.execute(owner_id=OWNER, title="t", content="c", channel="sms", recipient=SMS_OK)


def test_borra_una_sent():
    w = World()
    n = crear(w)
    w.delete.execute(OWNER, n.id)
    assert w.repo.find_by_id(n.id, OWNER) is None


def test_borra_una_failed():
    w = World()
    w.sms.ok = False
    n = crear(w)
    w.delete.execute(OWNER, n.id)
    assert w.repo.is_empty()


def test_borra_una_pending():
    w = World()
    n = crear(w)
    # Fuerza un `pending` persistido (p. ej. el proceso cayó entre ambos commits).
    pending = Notification.create(
        id=n.id, owner_id=OWNER, title="t", content="c", channel="sms",
        recipient=SMS_OK, now=n.created_at,
    )
    w.repo.save(pending)
    w.delete.execute(OWNER, n.id)
    assert w.repo.is_empty()


def test_inexistente_lanza_not_found():
    with pytest.raises(NotificationNotFound):
        World().delete.execute(OWNER, UUID(int=99))


def test_ajena_lanza_not_found_y_no_borra():
    w = World()
    n = crear(w)
    with pytest.raises(NotificationNotFound):
        w.delete.execute(OTHER, n.id)
    assert w.repo.find_by_id(n.id, OWNER) is not None


def test_borrar_dos_veces_la_segunda_lanza_not_found():
    w = World()
    n = crear(w)
    w.delete.execute(OWNER, n.id)
    with pytest.raises(NotificationNotFound):
        w.delete.execute(OWNER, n.id)
