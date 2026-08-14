"""Contrato de canal y registry.

Este módulo es deliberadamente agnóstico del framework: no importa FastAPI ni
SQLAlchemy. Un canal opera sobre datos planos, así se puede testear sin levantar
la base (criterio 15 y autoevaluación 4).

## Por qué `abc.ABC` y no `typing.Protocol`

Elegí una **clase base abstracta** (tipado nominal) y no un `Protocol` (tipado
estructural) por una razón concreta: además del *contrato* quiero **compartir
comportamiento**. `validate()` es concreto en la base —parsea el payload contra
el esquema Pydantic que cada canal declara y traduce el error a un
`ChannelValidationError` uniforme— y solo `deliver()` queda abstracto. Con un
`Protocol` obtendría el chequeo de forma pero **cero reuso**: cada canal tendría
que reimplementar el parseo y la traducción del error, que es justo lo que "lo
que se repite vive en un solo lugar" pide evitar.

`Protocol` (estructural) brilla cuando el objeto no es mío y solo me importa que
"tenga la forma" —típico al aceptar tipos de terceros—. Acá soy dueño de todos
los canales y *quiero* obligarlos a pasar por un mismo esqueleto: el modelo
honesto es nominal (heredás de `Channel` explícitamente).

Qué se rompería con `Protocol`: perdería el `validate()` compartido y la
garantía de instanciación que da `ABC` (una subclase sin `deliver` falla al
instanciarse, no recién al llamarla). El orden "validar → entregar → registrar"
tampoco vive acá: lo impone el despachador (ver `services/notifications.py`), no
la subclase, de modo que un canal **no puede** registrar un envío sin validar.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar

from pydantic import BaseModel, ValidationError


class ChannelValidationError(Exception):
    """El payload/mensaje no cumple lo que el canal exige. Se traduce a 400."""

    def __init__(self, message: str, details: list | None = None):
        self.message = message
        self.details = details or []
        super().__init__(message)


@dataclass
class NotificationDraft:
    """Datos crudos de una notificación, antes de validar contra un canal."""

    title: str
    content: str
    payload: dict = field(default_factory=dict)


@dataclass
class ValidatedMessage:
    """Resultado de validar un draft contra un canal. Lo que `deliver` consume."""

    channel: str
    draft: NotificationDraft
    extra: dict = field(default_factory=dict)


@dataclass
class DeliveryResult:
    """Resultado del envío simulado. Si `success` es False, `error` explica por qué."""

    success: bool
    error: str | None = None
    info: dict = field(default_factory=dict)


class Channel(ABC):
    """Contrato que todo canal debe cumplir.

    - `name`: clave con la que el canal se registra y se referencia.
    - `payload_schema`: modelo Pydantic con los campos propios del canal
      (destinatario, número, device token…). Es donde vive la validación
      declarativa específica de cada canal.
    """

    name: ClassVar[str]
    payload_schema: ClassVar[type[BaseModel]]

    def validate(self, draft: NotificationDraft) -> ValidatedMessage:
        """Valida el draft contra este canal. Concreto y compartido.

        Parsea el payload con el esquema del canal y delega reglas extra
        (que no son solo del payload, como el largo del contenido en SMS) en
        `validate_message`, que las subclases pueden extender.
        """
        try:
            parsed = self.payload_schema.model_validate(draft.payload)
        except ValidationError as exc:
            raise ChannelValidationError(
                f"Invalid payload for channel '{self.name}'",
                _pydantic_details(exc),
            )
        message = ValidatedMessage(
            channel=self.name, draft=draft, extra=parsed.model_dump()
        )
        self.validate_message(message)
        return message

    def validate_message(self, message: ValidatedMessage) -> None:
        """Hook para reglas que exceden al payload. Vacío por defecto: un canal
        que solo valida su payload no necesita tocarlo."""

    @abstractmethod
    def deliver(self, message: ValidatedMessage) -> DeliveryResult:
        """Ejecuta el envío simulado. Es el punto donde entraría un proveedor
        real: cada canal formatea a su manera y devuelve el resultado."""


def _pydantic_details(exc: ValidationError) -> list:
    return [
        {"field": ".".join(str(p) for p in err["loc"]), "message": err["msg"]}
        for err in exc.errors()
    ]


# --- Registry -------------------------------------------------------------
# Un dict nombre -> instancia. Los canales se registran solos al importarse con
# el decorador `register`. El despachador resuelve por nombre; no hay ningún
# `if canal == ...` en toda la app. Sumar un canal = crear su módulo y
# registrarlo; no se toca nada de lo existente.

_registry: dict[str, Channel] = {}


def register(channel_cls: type[Channel]) -> type[Channel]:
    _registry[channel_cls.name] = channel_cls()
    return channel_cls


def get_channel(name: str) -> Channel:
    channel = _registry.get(name)
    if channel is None:
        raise ChannelValidationError(
            f"Unknown channel '{name}'",
            [{"field": "channel", "message": f"'{name}' is not a supported channel"}],
        )
    return channel


def channel_names() -> list[str]:
    return sorted(_registry)
