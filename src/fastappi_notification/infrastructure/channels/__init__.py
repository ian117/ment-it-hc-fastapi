"""Gateways simulados por canal (ADR-012). Mañana: Twilio / FCM / SendGrid."""

from .email import SimulatedEmailGateway
from .push import SimulatedPushGateway
from .simulated import SimulatedGateway
from .sms import SimulatedSmsGateway

__all__ = ["SimulatedEmailGateway", "SimulatedGateway", "SimulatedPushGateway", "SimulatedSmsGateway"]
