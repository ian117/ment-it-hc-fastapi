import pytest

from fastappi_notification.domain.errors import ChannelRuleViolation, UnknownChannel
from fastappi_notification.domain.notification import NotificationStatus
from tests.application.fakes import OWNER, SMS_OK, T0, World


def crear(world: World, **over):
    args = dict(
        owner_id=OWNER, title="Hola", content="Contenido", channel="sms", recipient=SMS_OK
    )
    args.update(over)
    return world.create.execute(**args)


def test_crear_con_entrega_ok_queda_sent():
    w = World()
    w.clock.advance(minutes=1)
    n = crear(w)
    assert n.status is NotificationStatus.SENT
    assert n.sent_at == w.clock.now()
    assert n.error_message is None
    assert n.owner_id == OWNER


def test_crear_persiste_el_estado_final():
    w = World()
    n = crear(w)
    assert w.repo.stored(n.id).status is NotificationStatus.SENT


def test_crear_usa_el_id_del_generador_y_la_hora_del_reloj():
    w = World()
    n = crear(w)
    assert int(n.id) == 1
    assert n.created_at == T0


def test_crear_con_entrega_fallida_queda_failed_con_el_detalle():
    w = World()
    w.sms.ok, w.sms.detail = False, "proveedor caído"
    n = crear(w)
    assert n.status is NotificationStatus.FAILED
    assert n.error_message == "proveedor caído"
    assert n.sent_at is None


def test_fallo_sin_detalle_usa_mensaje_por_defecto():
    w = World()
    w.sms.ok = False
    assert crear(w).error_message == "Delivery failed"


def test_gateway_que_lanza_excepcion_queda_failed_con_su_mensaje_y_no_se_propaga():
    w = World()
    w.sms.raises = RuntimeError("timeout de red")
    n = crear(w)
    assert n.status is NotificationStatus.FAILED
    assert n.error_message == "timeout de red"
    assert w.repo.stored(n.id).status is NotificationStatus.FAILED


def test_gateway_que_lanza_excepcion_sin_mensaje_usa_mensaje_por_defecto():
    w = World()
    w.sms.raises = RuntimeError()
    assert crear(w).error_message == "Delivery failed"


def test_attempts_es_uno_tras_crear():
    w = World()
    assert crear(w).attempts == 1
    w.sms.ok = False
    assert crear(w).attempts == 1


def test_primer_save_es_pending_y_ocurre_antes_de_deliver_con_exactamente_dos_saves():
    w = World()
    crear(w)
    assert w.repo.saved_statuses == [NotificationStatus.PENDING, NotificationStatus.SENT]
    assert w.events == [("save", "pending"), ("deliver", "pending"), ("save", "sent")]


def test_el_orden_se_mantiene_cuando_el_gateway_falla_o_lanza():
    for configure in (
        lambda g: setattr(g, "ok", False),
        lambda g: setattr(g, "raises", RuntimeError("x")),
    ):
        w = World()
        configure(w.sms)
        crear(w)
        assert w.events == [("save", "pending"), ("deliver", "pending"), ("save", "failed")]


def test_el_gateway_recibe_el_mensaje_preparado_por_la_politica():
    w = World()
    crear(w, content="Texto")
    (message,) = w.sms.messages
    assert message.channel == "sms"
    assert message.recipient == SMS_OK
    assert message.body == "Texto"


def test_solo_se_usa_el_gateway_del_canal():
    w = World()
    crear(w, channel="email", recipient="a@b.com")
    assert w.email.calls == 1
    assert w.sms.calls == 0


def test_canal_desconocido_no_escribe_nada():
    w = World()
    with pytest.raises(UnknownChannel):
        crear(w, channel="fax")
    assert w.repo.is_empty()
    assert w.repo.saved_statuses == []
    assert w.sms.calls == w.email.calls == w.push.calls == 0


def test_violacion_de_canal_no_escribe_nada():
    w = World()
    with pytest.raises(ChannelRuleViolation):
        crear(w, recipient="no-es-un-telefono")
    assert w.repo.is_empty()
    assert w.repo.saved_statuses == []
    assert w.sms.calls == 0


def test_sms_con_mas_de_160_caracteres_se_rechaza():
    w = World()
    with pytest.raises(ChannelRuleViolation):
        crear(w, content="x" * 161)
    assert w.repo.is_empty()
