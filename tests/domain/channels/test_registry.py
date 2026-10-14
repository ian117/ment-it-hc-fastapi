from __future__ import annotations

import pytest

from fastappi_notification.domain.channels.email import EmailPolicy
from fastappi_notification.domain.channels.policy import ChannelDraft, OutboundMessage
from fastappi_notification.domain.channels.push import PushPolicy
from fastappi_notification.domain.channels.registry import ChannelPolicyRegistry
from fastappi_notification.domain.channels.sms import SmsPolicy
from fastappi_notification.domain.errors import ChannelRuleViolation, UnknownChannel


def test_returns_registered_policy():
    email, sms = EmailPolicy(), SmsPolicy()
    registry = ChannelPolicyRegistry([email, sms])
    assert registry.policy("email") is email
    assert registry.policy("sms") is sms


def test_unknown_channel_raises_with_name():
    registry = ChannelPolicyRegistry([EmailPolicy()])
    with pytest.raises(UnknownChannel) as exc:
        registry.policy("whatsapp")
    assert exc.value.channel == "whatsapp"


def test_lookup_is_exact_no_normalization():
    registry = ChannelPolicyRegistry([EmailPolicy()])
    with pytest.raises(UnknownChannel):
        registry.policy("EMAIL")


def test_duplicate_channels_raise_value_error():
    with pytest.raises(ValueError):
        ChannelPolicyRegistry([EmailPolicy(), SmsPolicy(), EmailPolicy()])


def test_has():
    registry = ChannelPolicyRegistry([EmailPolicy(), PushPolicy()])
    assert registry.has("email") is True
    assert registry.has("push") is True
    assert registry.has("sms") is False


def test_channels_lists_registered_names():
    registry = ChannelPolicyRegistry([EmailPolicy(), SmsPolicy(), PushPolicy()])
    assert registry.channels() == ["email", "sms", "push"]


def test_channels_returns_a_copy():
    registry = ChannelPolicyRegistry([EmailPolicy()])
    registry.channels().append("x")
    assert registry.channels() == ["email"]


def test_empty_registry():
    registry = ChannelPolicyRegistry([])
    assert registry.channels() == []
    assert registry.has("email") is False
    with pytest.raises(UnknownChannel):
        registry.policy("email")


def test_open_for_extension_with_a_new_policy():
    class WhatsAppPolicy:
        channel = "whatsapp"

        def prepare(self, draft: ChannelDraft) -> OutboundMessage:
            return OutboundMessage(
                channel=self.channel,
                recipient=draft.recipient,
                subject=None,
                body=draft.content,
                html=None,
                data=None,
            )

    registry = ChannelPolicyRegistry([EmailPolicy(), WhatsAppPolicy()])
    assert registry.has("whatsapp")
    msg = registry.policy("whatsapp").prepare(ChannelDraft("t", "c", "+521"))
    assert msg.channel == "whatsapp"


def test_policy_violations_propagate_through_registry():
    registry = ChannelPolicyRegistry([SmsPolicy()])
    with pytest.raises(ChannelRuleViolation):
        registry.policy("sms").prepare(ChannelDraft("t", "c", "nope"))


def test_exceptions_attributes():
    violations = [{"field": "content", "message": "m"}]
    err = ChannelRuleViolation(violations)
    assert err.violations == violations
    assert isinstance(err, Exception)
    with pytest.raises(ValueError):
        ChannelRuleViolation([])
    assert UnknownChannel("x").channel == "x"
