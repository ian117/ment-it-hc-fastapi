from ...domain.channels import OutboundMessage
from .simulated import SimulatedGateway


class SimulatedSmsGateway(SimulatedGateway):
    channel = "sms"

    def _fails(self, message: OutboundMessage) -> bool:
        return message.recipient.endswith("0000")
