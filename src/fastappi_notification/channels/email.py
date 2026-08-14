from pydantic import BaseModel, EmailStr

from .base import Channel, DeliveryResult, ValidatedMessage, register


class EmailPayload(BaseModel):
    # EmailStr valida el formato del destinatario (paso propio del canal Email).
    recipient: EmailStr


@register
class EmailChannel(Channel):
    name = "email"
    payload_schema = EmailPayload

    def deliver(self, message: ValidatedMessage) -> DeliveryResult:
        # Genera el template y "envía". Con un proveedor real, acá iría la
        # llamada al SMTP/API; hoy es simulado.
        recipient = message.extra["recipient"]
        rendered = f"To: {recipient}\nSubject: {message.draft.title}\n\n{message.draft.content}"
        return DeliveryResult(success=True, info={"recipient": recipient, "rendered": rendered})
