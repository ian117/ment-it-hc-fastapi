"""Tests unitarios de la máquina de estados de `Notification` (diseño 2.1 y 2.2).

Sin base de datos, sin FastAPI, sin SQLAlchemy: solo dominio puro.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from fastappi_notification.domain.errors import (
    InvalidNotificationTransition,
    NotificationNotEditable,
)
from fastappi_notification.domain.notification import (
    Notification,
    NotificationStatus,
)

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
T1 = T0 + timedelta(minutes=1)
T2 = T0 + timedelta(minutes=2)
T3 = T0 + timedelta(minutes=3)
T4 = T0 + timedelta(minutes=4)
T5 = T0 + timedelta(minutes=5)

NOTIFICATION_ID = uuid4()
OWNER_ID = uuid4()


def crear(channel: str = "sms", recipient: str = "+5219611234567") -> Notification:
    return Notification.create(
        id=NOTIFICATION_ID,
        owner_id=OWNER_ID,
        title="Hola",
        content="Contenido original",
        channel=channel,
        recipient=recipient,
        now=T0,
    )


def crear_pending() -> Notification:
    return crear()


def crear_failed() -> Notification:
    n = crear()
    n.mark_failed("proveedor caído", T1)
    return n


def crear_sent() -> Notification:
    n = crear()
    n.mark_sent(T1)
    return n


# --------------------------------------------------------------------------
# Estado inicial
# --------------------------------------------------------------------------


def test_status_del_enum_tiene_los_valores_del_contrato():
    assert NotificationStatus.PENDING.value == "pending"
    assert NotificationStatus.SENT.value == "sent"
    assert NotificationStatus.FAILED.value == "failed"


def test_status_se_compara_como_string():
    assert NotificationStatus.PENDING == "pending"


def test_create_deja_la_notificacion_en_pending():
    assert crear().status == NotificationStatus.PENDING


def test_create_inicia_attempts_en_cero():
    assert crear().attempts == 0


def test_create_inicia_error_message_en_none():
    assert crear().error_message is None


def test_create_inicia_sent_at_en_none():
    assert crear().sent_at is None


def test_create_fija_created_at_y_updated_at_con_now():
    n = crear()
    assert n.created_at == T0
    assert n.updated_at == T0


def test_create_conserva_el_id_recibido():
    n = crear()
    assert n.id == NOTIFICATION_ID
    assert isinstance(n.id, UUID)


def test_create_conserva_los_datos_recibidos():
    n = crear(channel="email", recipient="a@b.com")
    assert n.owner_id == OWNER_ID
    assert n.title == "Hola"
    assert n.content == "Contenido original"
    assert n.channel == "email"
    assert n.recipient == "a@b.com"


# --------------------------------------------------------------------------
# Transiciones válidas
# --------------------------------------------------------------------------


def test_mark_sent_desde_pending_cambia_status_a_sent():
    n = crear_pending()
    n.mark_sent(T1)
    assert n.status == NotificationStatus.SENT


def test_mark_sent_fija_sent_at():
    n = crear_pending()
    n.mark_sent(T1)
    assert n.sent_at == T1


def test_mark_sent_incrementa_attempts():
    n = crear_pending()
    n.mark_sent(T1)
    assert n.attempts == 1


def test_mark_sent_actualiza_updated_at():
    n = crear_pending()
    n.mark_sent(T1)
    assert n.updated_at == T1


def test_mark_sent_deja_error_message_en_none():
    n = crear_pending()
    n.mark_sent(T1)
    assert n.error_message is None


def test_mark_failed_desde_pending_cambia_status_a_failed():
    n = crear_pending()
    n.mark_failed("timeout", T1)
    assert n.status == NotificationStatus.FAILED


def test_mark_failed_fija_error_message():
    n = crear_pending()
    n.mark_failed("timeout", T1)
    assert n.error_message == "timeout"


def test_mark_failed_incrementa_attempts():
    n = crear_pending()
    n.mark_failed("timeout", T1)
    assert n.attempts == 1


def test_mark_failed_actualiza_updated_at():
    n = crear_pending()
    n.mark_failed("timeout", T1)
    assert n.updated_at == T1


def test_mark_failed_no_fija_sent_at():
    n = crear_pending()
    n.mark_failed("timeout", T1)
    assert n.sent_at is None


def test_revise_desde_failed_vuelve_a_pending():
    n = crear_failed()
    n.revise(T2, content="Nuevo contenido")
    assert n.status == NotificationStatus.PENDING


def test_revise_limpia_error_message():
    n = crear_failed()
    n.revise(T2, content="Nuevo contenido")
    assert n.error_message is None


def test_revise_actualiza_updated_at():
    n = crear_failed()
    n.revise(T2, content="Nuevo contenido")
    assert n.updated_at == T2


def test_revise_conserva_attempts():
    n = crear_failed()
    n.revise(T2, content="Nuevo contenido")
    assert n.attempts == 1


def test_revise_aplica_title_content_y_recipient_cuando_se_envian():
    n = crear_failed()
    n.revise(T2, title="Nuevo título", content="Nuevo contenido", recipient="+5215512345678")
    assert n.title == "Nuevo título"
    assert n.content == "Nuevo contenido"
    assert n.recipient == "+5215512345678"


def test_revise_sin_campos_igual_vuelve_a_pending():
    n = crear_failed()
    n.revise(T2)
    assert n.status == NotificationStatus.PENDING
    assert n.title == "Hola"
    assert n.content == "Contenido original"
    assert n.recipient == "+5219611234567"


# --------------------------------------------------------------------------
# Revise parcial: conserva lo no enviado
# --------------------------------------------------------------------------


def test_revise_solo_title_conserva_content_y_recipient():
    n = crear_failed()
    n.revise(T2, title="Solo título")
    assert n.title == "Solo título"
    assert n.content == "Contenido original"
    assert n.recipient == "+5219611234567"


def test_revise_solo_content_conserva_title_y_recipient():
    n = crear_failed()
    n.revise(T2, content="Solo contenido")
    assert n.title == "Hola"
    assert n.content == "Solo contenido"
    assert n.recipient == "+5219611234567"


def test_revise_solo_recipient_conserva_title_y_content():
    n = crear_failed()
    n.revise(T2, recipient="+5215512345678")
    assert n.title == "Hola"
    assert n.content == "Contenido original"
    assert n.recipient == "+5215512345678"


def test_revise_conserva_id_owner_id_y_created_at():
    n = crear_failed()
    n.revise(T2, title="Otro")
    assert n.id == NOTIFICATION_ID
    assert n.owner_id == OWNER_ID
    assert n.created_at == T0


# --------------------------------------------------------------------------
# Canal inmutable
# --------------------------------------------------------------------------


def test_revise_conserva_el_canal():
    n = crear_failed()
    n.revise(T2, title="Otro")
    assert n.channel == "sms"


def test_revise_no_acepta_parametro_channel():
    n = crear_failed()
    with pytest.raises(TypeError):
        n.revise(T2, channel="email")  # type: ignore[call-arg]
    assert n.channel == "sms"


# --------------------------------------------------------------------------
# Transiciones inválidas
# --------------------------------------------------------------------------


def test_mark_sent_desde_sent_lanza_invalid_transition():
    n = crear_sent()
    with pytest.raises(InvalidNotificationTransition):
        n.mark_sent(T2)


def test_mark_failed_desde_sent_lanza_invalid_transition():
    n = crear_sent()
    with pytest.raises(InvalidNotificationTransition):
        n.mark_failed("tarde", T2)


def test_revise_desde_sent_lanza_not_editable():
    n = crear_sent()
    with pytest.raises(NotificationNotEditable):
        n.revise(T2, title="Otro")


def test_mark_sent_desde_failed_lanza_invalid_transition():
    n = crear_failed()
    with pytest.raises(InvalidNotificationTransition):
        n.mark_sent(T2)


def test_mark_failed_desde_failed_lanza_invalid_transition():
    n = crear_failed()
    with pytest.raises(InvalidNotificationTransition):
        n.mark_failed("otra vez", T2)


def test_revise_desde_pending_lanza_not_editable():
    n = crear_pending()
    with pytest.raises(NotificationNotEditable):
        n.revise(T1, title="Otro")


def test_transicion_invalida_desde_sent_no_modifica_la_entidad():
    n = crear_sent()
    with pytest.raises(InvalidNotificationTransition):
        n.mark_failed("tarde", T2)
    assert n.status == NotificationStatus.SENT
    assert n.attempts == 1
    assert n.error_message is None
    assert n.sent_at == T1
    assert n.updated_at == T1


def test_transicion_invalida_desde_failed_no_modifica_la_entidad():
    n = crear_failed()
    with pytest.raises(InvalidNotificationTransition):
        n.mark_sent(T2)
    assert n.status == NotificationStatus.FAILED
    assert n.attempts == 1
    assert n.error_message == "proveedor caído"
    assert n.sent_at is None
    assert n.updated_at == T1


def test_revise_rechazado_desde_pending_no_modifica_la_entidad():
    n = crear_pending()
    with pytest.raises(NotificationNotEditable):
        n.revise(T1, title="Otro")
    assert n.title == "Hola"
    assert n.status == NotificationStatus.PENDING
    assert n.updated_at == T0


def test_los_errores_de_dominio_extienden_exception():
    assert issubclass(NotificationNotEditable, Exception)
    assert issubclass(InvalidNotificationTransition, Exception)


# --------------------------------------------------------------------------
# Ciclo completo
# --------------------------------------------------------------------------


def test_ciclo_completo_pending_failed_revise_pending_failed_revise_sent():
    n = crear()
    assert n.status == NotificationStatus.PENDING
    assert n.attempts == 0

    n.mark_failed("primer fallo", T1)
    assert n.status == NotificationStatus.FAILED
    assert n.attempts == 1
    assert n.error_message == "primer fallo"

    n.revise(T2, recipient="+5215512345678")
    assert n.status == NotificationStatus.PENDING
    assert n.attempts == 1
    assert n.error_message is None

    n.mark_failed("segundo fallo", T3)
    assert n.status == NotificationStatus.FAILED
    assert n.attempts == 2
    assert n.error_message == "segundo fallo"

    n.revise(T4, content="Contenido corregido")
    assert n.status == NotificationStatus.PENDING
    assert n.attempts == 2
    assert n.error_message is None

    n.mark_sent(T5)
    assert n.status == NotificationStatus.SENT
    assert n.attempts == 3
    assert n.error_message is None
    assert n.sent_at == T5
    assert n.updated_at == T5

    # Datos acumulados de las revisiones y campos inmutables intactos
    assert n.recipient == "+5215512345678"
    assert n.content == "Contenido corregido"
    assert n.title == "Hola"
    assert n.channel == "sms"
    assert n.created_at == T0
    assert n.id == NOTIFICATION_ID
    assert n.owner_id == OWNER_ID


def test_tras_el_ciclo_sent_sigue_siendo_terminal():
    n = crear_failed()
    n.revise(T2)
    n.mark_sent(T3)
    with pytest.raises(NotificationNotEditable):
        n.revise(T4, title="Otro")
    with pytest.raises(InvalidNotificationTransition):
        n.mark_failed("tarde", T4)


# --------------------------------------------------------------------------
# ensure_editable y NotificationNotFound
# --------------------------------------------------------------------------


def test_ensure_editable_desde_failed_no_lanza():
    crear_failed().ensure_editable()


def test_ensure_editable_desde_pending_lanza_not_editable():
    with pytest.raises(NotificationNotEditable):
        crear_pending().ensure_editable()


def test_ensure_editable_desde_sent_lanza_not_editable():
    with pytest.raises(NotificationNotEditable):
        crear_sent().ensure_editable()


def test_ensure_editable_no_modifica_la_entidad():
    n = crear_failed()
    n.ensure_editable()
    assert n.status is NotificationStatus.FAILED
    assert n.error_message == "proveedor caído"


def test_notification_not_found_guarda_el_id_opcional():
    from fastappi_notification.domain.errors import NotificationNotFound

    assert NotificationNotFound().id is None
    assert NotificationNotFound(NOTIFICATION_ID).id == NOTIFICATION_ID
    assert issubclass(NotificationNotFound, Exception)
