from uuid import UUID

import pytest

from fastappi_notification.domain.errors import (
    ChannelRuleViolation,
    NotificationNotEditable,
    NotificationNotFound,
)
from fastappi_notification.domain.notification import Notification, NotificationStatus
from tests.application.fakes import OTHER, OWNER, SMS_OK, SMS_OTHER, World


def crear(w: World, ok: bool = False, channel="sms", recipient=SMS_OK, content="Contenido"):
    """Crea una notificación; por defecto queda `failed` (el gateway falla)."""
    gateway = getattr(w, channel)
    previous = gateway.ok
    gateway.ok, gateway.detail = ok, None if ok else "proveedor caído"
    n = w.create.execute(
        owner_id=OWNER, title="Hola", content=content, channel=channel, recipient=recipient
    )
    gateway.ok, gateway.detail = previous, None
    w.events.clear()
    w.repo.saved_statuses.clear()
    for g in (w.sms, w.email, w.push):
        g.messages.clear()
    return n


def test_revise_desde_failed_reenvia_y_queda_sent():
    w = World()
    n = crear(w)
    w.clock.advance(minutes=5)
    r = w.revise.execute(OWNER, n.id, content="Corregido")
    assert r.status is NotificationStatus.SENT
    assert r.attempts == 2
    assert r.error_message is None
    assert r.sent_at == w.clock.now()
    assert w.sms.calls == 1
    assert w.sms.messages[0].body == "Corregido"
    assert w.repo.stored(n.id).status is NotificationStatus.SENT


def test_revise_que_vuelve_a_fallar_conserva_failed_con_el_nuevo_detalle():
    w = World()
    n = crear(w)
    w.sms.ok, w.sms.detail = False, "otro fallo"
    r = w.revise.execute(OWNER, n.id, title="Nuevo")
    assert r.status is NotificationStatus.FAILED
    assert r.error_message == "otro fallo"
    assert r.attempts == 2
    assert r.title == "Nuevo"


def test_revise_con_gateway_que_lanza_queda_failed():
    w = World()
    n = crear(w)
    w.sms.raises = RuntimeError("boom")
    r = w.revise.execute(OWNER, n.id)
    assert r.status is NotificationStatus.FAILED
    assert r.error_message == "boom"


def test_revise_guarda_pending_antes_de_entregar_y_hace_dos_saves():
    w = World()
    n = crear(w)
    w.revise.execute(OWNER, n.id, content="x")
    assert w.events == [("save", "pending"), ("deliver", "pending"), ("save", "sent")]
    assert w.repo.saved_statuses == [NotificationStatus.PENDING, NotificationStatus.SENT]


def test_lo_no_enviado_conserva_el_valor_actual():
    w = World()
    n = crear(w, content="Original")
    r = w.revise.execute(OWNER, n.id, recipient=SMS_OTHER)
    assert (r.title, r.content, r.recipient) == ("Hola", "Original", SMS_OTHER)
    assert w.sms.messages[0].recipient == SMS_OTHER
    assert w.sms.messages[0].body == "Original"


def test_revise_no_cambia_el_canal():
    w = World()
    n = crear(w)
    assert w.revise.execute(OWNER, n.id, title="x").channel == "sms"


def test_revise_desde_sent_lanza_not_editable_sin_entregar():
    w = World()
    n = crear(w, ok=True)
    with pytest.raises(NotificationNotEditable):
        w.revise.execute(OWNER, n.id, title="x")
    assert w.sms.calls == 0
    assert w.repo.saved_statuses == []
    assert w.repo.stored(n.id).status is NotificationStatus.SENT


def test_revise_desde_pending_lanza_not_editable_sin_entregar():
    w = World()
    n = crear(w)
    w.repo.save(
        Notification.create(
            id=n.id, owner_id=OWNER, title="Hola", content="c", channel="sms",
            recipient=SMS_OK, now=n.created_at,
        )
    )
    w.repo.saved_statuses.clear()
    with pytest.raises(NotificationNotEditable):
        w.revise.execute(OWNER, n.id, title="x")
    assert w.sms.calls == 0
    assert w.repo.saved_statuses == []


def test_payload_invalido_sobre_failed_lanza_violation_y_deja_la_notificacion_intacta():
    w = World()
    n = crear(w)
    before = w.repo.stored(n.id)
    snapshot = (before.status, before.recipient, before.attempts, before.error_message,
                before.updated_at)
    with pytest.raises(ChannelRuleViolation):
        w.revise.execute(OWNER, n.id, recipient="no-es-un-telefono")
    after = w.repo.stored(n.id)
    assert (after.status, after.recipient, after.attempts, after.error_message,
            after.updated_at) == snapshot
    assert after.status is NotificationStatus.FAILED
    assert w.sms.calls == 0
    assert w.repo.saved_statuses == []


def test_revise_valida_con_datos_fusionados_solo_content_largo_en_sms_falla():
    w = World()
    n = crear(w)  # recipient SMS válido ya existente
    with pytest.raises(ChannelRuleViolation) as exc:
        w.revise.execute(OWNER, n.id, content="x" * 161)
    assert exc.value.violations[0]["field"] == "content"
    assert w.sms.calls == 0


def test_revise_valida_con_datos_fusionados_content_valido_con_recipient_existente_pasa():
    w = World()
    n = crear(w)
    assert w.revise.execute(OWNER, n.id, content="x" * 160).status is NotificationStatus.SENT


def test_inexistente_lanza_not_found():
    with pytest.raises(NotificationNotFound):
        World().revise.execute(OWNER, UUID(int=99), title="x")


def test_ajena_lanza_not_found():
    w = World()
    n = crear(w)
    with pytest.raises(NotificationNotFound):
        w.revise.execute(OTHER, n.id, title="x")
    assert w.sms.calls == 0


def test_precedencia_404_antes_que_409_y_400():
    w = World()
    n = crear(w, ok=True)  # sent: no editable
    # Ajena + payload inválido + no editable -> 404
    with pytest.raises(NotificationNotFound):
        w.revise.execute(OTHER, n.id, recipient="malo")


def test_precedencia_409_antes_que_400():
    w = World()
    n = crear(w, ok=True)  # sent
    with pytest.raises(NotificationNotEditable):
        w.revise.execute(OWNER, n.id, recipient="malo")


def test_precedencia_400_cuando_es_propia_y_failed():
    w = World()
    n = crear(w)
    with pytest.raises(ChannelRuleViolation):
        w.revise.execute(OWNER, n.id, recipient="malo")


def test_revise_en_email_usa_la_politica_y_gateway_de_email():
    w = World()
    n = crear(w, channel="email", recipient="a@b.com")
    r = w.revise.execute(OWNER, n.id, recipient="c@d.com")
    assert r.status is NotificationStatus.SENT
    assert w.email.calls == 1
    with pytest.raises(NotificationNotEditable):
        w.revise.execute(OWNER, n.id, title="otra vez")
