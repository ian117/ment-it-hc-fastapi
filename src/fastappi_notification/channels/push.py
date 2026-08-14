from pydantic import BaseModel, Field

from .base import Channel, DeliveryResult, ValidatedMessage, register


class PushPayload(BaseModel):
    # Valida la presencia del token de dispositivo (paso propio del canal Push).
    device_token: str = Field(min_length=1)


@register
class PushChannel(Channel):
    name = "push"
    payload_schema = PushPayload

    def deliver(self, message: ValidatedMessage) -> DeliveryResult:
        # Formatea el payload y registra el estado del envío (pasos propios).
        formatted = {
            "token": message.extra["device_token"],
            "notification": {"title": message.draft.title, "body": message.draft.content},
        }
        return DeliveryResult(success=True, info={"payload": formatted})
