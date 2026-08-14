import re
from datetime import datetime, timezone

from pydantic import BaseModel, field_validator

from .base import (
    Channel,
    ChannelValidationError,
    DeliveryResult,
    ValidatedMessage,
    register,
)

_E164 = re.compile(r"^\+?[1-9]\d{6,14}$")


class SmsPayload(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value: str) -> str:
        if not _E164.match(value):
            raise ValueError("must be a valid phone number (E.164)")
        return value


@register
class SmsChannel(Channel):
    name = "sms"
    payload_schema = SmsPayload
    max_length = 160

    def validate_message(self, message: ValidatedMessage) -> None:
        # Decisión: un SMS de más de 160 caracteres se **rechaza** (400), no se
        # trunca en silencio. Truncar mutila el mensaje sin que el usuario se
        # entere; fallar fuerte es preferible a perder contenido callado.
        if len(message.draft.content) > self.max_length:
            raise ChannelValidationError(
                f"SMS content exceeds {self.max_length} characters",
                [
                    {
                        "field": "content",
                        "message": f"max {self.max_length} characters, got {len(message.draft.content)}",
                    }
                ],
            )

    def deliver(self, message: ValidatedMessage) -> DeliveryResult:
        # Registra número y fecha de envío (pasos propios del canal SMS).
        return DeliveryResult(
            success=True,
            info={
                "phone": message.extra["phone"],
                "sent_at": datetime.now(timezone.utc).isoformat(),
            },
        )
