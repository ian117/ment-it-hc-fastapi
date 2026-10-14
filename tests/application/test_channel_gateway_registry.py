import pytest

from fastappi_notification.application.channel_gateway_registry import ChannelGatewayRegistry
from fastappi_notification.domain.errors import UnknownChannel
from tests.application.fakes import FakeChannelGateway, InMemoryNotificationRepository


def gw(channel: str) -> FakeChannelGateway:
    return FakeChannelGateway(channel, InMemoryNotificationRepository())


def test_devuelve_el_gateway_del_canal():
    sms, email = gw("sms"), gw("email")
    registry = ChannelGatewayRegistry([sms, email])
    assert registry.gateway("sms") is sms
    assert registry.gateway("email") is email


def test_canal_desconocido_lanza_unknown_channel():
    with pytest.raises(UnknownChannel) as exc:
        ChannelGatewayRegistry([gw("sms")]).gateway("fax")
    assert exc.value.channel == "fax"


def test_duplicados_lanzan_value_error():
    with pytest.raises(ValueError):
        ChannelGatewayRegistry([gw("sms"), gw("sms")])


def test_has():
    registry = ChannelGatewayRegistry([gw("sms")])
    assert registry.has("sms")
    assert not registry.has("push")
