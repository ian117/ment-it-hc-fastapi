"""Tests unitarios de canales. No tocan la base: validan el contrato y la
lógica específica de cada canal en memoria (criterio 15, autoevaluación 4)."""

import pytest

from fastappi_notification.channels import (
    NotificationDraft,
    channel_names,
    get_channel,
)
from fastappi_notification.channels.base import Channel, ChannelValidationError


def draft(content="hola", payload=None):
    return NotificationDraft(title="t", content=content, payload=payload or {})


def test_registry_has_the_three_channels():
    assert channel_names() == ["email", "push", "sms"]


def test_unknown_channel_raises():
    with pytest.raises(ChannelValidationError):
        get_channel("whatsapp")


def test_channel_abc_cannot_be_instantiated():
    # Falta `deliver`: ABC lo impide en la instanciación, no al llamarlo.
    with pytest.raises(TypeError):
        Channel()


# --- Email ---------------------------------------------------------------

def test_email_valid_recipient_delivers():
    msg = get_channel("email").validate(draft(payload={"recipient": "a@ex.com"}))
    result = get_channel("email").deliver(msg)
    assert result.success
    assert "a@ex.com" in result.info["rendered"]


def test_email_invalid_recipient_rejected():
    with pytest.raises(ChannelValidationError):
        get_channel("email").validate(draft(payload={"recipient": "not-an-email"}))


def test_email_missing_recipient_rejected():
    with pytest.raises(ChannelValidationError):
        get_channel("email").validate(draft(payload={}))


# --- SMS -----------------------------------------------------------------

def test_sms_valid_delivers():
    msg = get_channel("sms").validate(draft(payload={"phone": "+541112345678"}))
    result = get_channel("sms").deliver(msg)
    assert result.success
    assert result.info["phone"] == "+541112345678"


def test_sms_over_160_chars_rejected_not_truncated():
    with pytest.raises(ChannelValidationError) as exc:
        get_channel("sms").validate(draft(content="x" * 161, payload={"phone": "+541112345678"}))
    assert "160" in str(exc.value)


def test_sms_invalid_phone_rejected():
    with pytest.raises(ChannelValidationError):
        get_channel("sms").validate(draft(payload={"phone": "abc"}))


# --- Push ----------------------------------------------------------------

def test_push_with_token_delivers():
    msg = get_channel("push").validate(draft(payload={"device_token": "abc123"}))
    result = get_channel("push").deliver(msg)
    assert result.success
    assert result.info["payload"]["token"] == "abc123"


def test_push_without_token_rejected():
    with pytest.raises(ChannelValidationError):
        get_channel("push").validate(draft(payload={}))
