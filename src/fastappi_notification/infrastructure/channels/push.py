from ...domain.channels import OutboundMessage
from .simulated import SimulatedGateway


class SimulatedPushGateway(SimulatedGateway):
    channel = "push"

    def _fails(self, message: OutboundMessage) -> bool:
        return "fail" in message.recipient.lower()
