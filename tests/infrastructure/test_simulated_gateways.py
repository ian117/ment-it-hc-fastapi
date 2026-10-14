import pytest

from fastappi_notification.domain.channels import OutboundMessage
from fastappi_notification.infrastructure.channels import (
    SimulatedEmailGateway,
    SimulatedPushGateway,
    SimulatedSmsGateway,
)
from tests.application.fakes import T0


class FixedClock:
    def now(self):
        return T0


def _msg(channel: str, recipient: str) -> OutboundMessage:
    return OutboundMessage(channel=channel, recipient=recipient, subject=None, body="b", html=None, data=None)


@pytest.mark.parametrize(
    "gateway_cls, recipient, ok",
    [
        (SimulatedEmailGateway, "ana@example.com", True),
        (SimulatedEmailGateway, "FAIL@example.com", False),
        (SimulatedEmailGateway, "x@fail.example.com", False),
        (SimulatedPushGateway, "device-token-1", True),
        (SimulatedPushGateway, "device-Fail-1", False),
        (SimulatedSmsGateway, "+5219611234567", True),
        (SimulatedSmsGateway, "+5219610000000", False),
        (SimulatedSmsGateway, "+520000123456", True),  # "0000" solo cuenta al final
    ],
)
def test_deterministic_failure_rule(gateway_cls, recipient, ok):
    gateway = gateway_cls(FixedClock())
    result = gateway.deliver(_msg(gateway.channel, recipient))
    assert result.ok is ok
    assert result.at == T0
    assert result.detail == (None if ok else "Simulated delivery failure")


def test_each_delivery_is_logged(caplog):
    caplog.set_level("INFO", logger="fastappi_notification.channels")
    SimulatedSmsGateway(FixedClock()).deliver(_msg("sms", "+5219610000000"))
    assert "channel=sms" in caplog.text
    assert "result=failed" in caplog.text
