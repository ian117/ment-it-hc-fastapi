from ...domain.channels import OutboundMessage
from .simulated import SimulatedGateway


class SimulatedEmailGateway(SimulatedGateway):
    channel = "email"

    def _fails(self, message: OutboundMessage) -> bool:
        return "fail" in message.recipient.lower()
