from __future__ import annotations

import pytest

from fastappi_notification.domain.channels.policy import ChannelDraft, OutboundMessage
from fastappi_notification.domain.channels.sms import SmsPolicy
from fastappi_notification.domain.errors import ChannelRuleViolation


def draft(recipient: str = "+5219611234567", content: str = "Hola", title: str = "T") -> ChannelDraft:
    return ChannelDraft(title=title, content=content, recipient=recipient)


def fields(exc_info) -> list[str]:
    return [v["field"] for v in exc_info.value.violations]


def test_channel_name():
    assert SmsPolicy.channel == "sms"
    assert SmsPolicy().channel == "sms"


@pytest.mark.parametrize(
    "recipient",
    [
        "+12",  # mínimo: 1 dígito + 1
        "+5219611234567",
        "+" + "1" * 15,  # 15 dígitos: límite
    ],
)
def test_valid_recipients(recipient):
    assert SmsPolicy().prepare(draft(recipient=recipient)).recipient == recipient


@pytest.mark.parametrize(
    "recipient",
    [
        "",
        "5219611234567",  # sin '+'
        "+0123456789",  # '0' inicial
        "+" + "1" * 16,  # 16 dígitos
        "+1",  # un solo dígito
        "+",
        "+52 1961 123 4567",
        "+52-196-1234567",
        "+52abc",
        " +5219611234567",
        "+5219611234567 ",
        "+5219611234567\n",
        "++5219611234567",
        "+٥٢١٩٦١",  # dígitos no ASCII
    ],
)
def test_invalid_recipients(recipient):
    with pytest.raises(ChannelRuleViolation) as exc:
        SmsPolicy().prepare(draft(recipient=recipient))
    assert fields(exc) == ["payload.recipient"]
    assert exc.value.violations[0]["message"]


def test_content_160_is_valid():
    content = "a" * 160
    assert SmsPolicy().prepare(draft(content=content)).body == content


def test_content_161_is_rejected_not_truncated():
    with pytest.raises(ChannelRuleViolation) as exc:
        SmsPolicy().prepare(draft(content="a" * 161))
    assert fields(exc) == ["content"]


def test_content_counts_code_points_not_bytes_or_utf16_units():
    # '😀' es 1 code point (2 unidades UTF-16, 4 bytes UTF-8)
    assert SmsPolicy().prepare(draft(content="😀" * 160)).body == "😀" * 160
    with pytest.raises(ChannelRuleViolation) as exc:
        SmsPolicy().prepare(draft(content="😀" * 161))
    assert fields(exc) == ["content"]


def test_empty_content_has_no_sms_rule():
    assert SmsPolicy().prepare(draft(content="")).body == ""


def test_multiple_violations_are_all_reported():
    with pytest.raises(ChannelRuleViolation) as exc:
        SmsPolicy().prepare(draft(recipient="123", content="a" * 161))
    assert sorted(fields(exc)) == ["content", "payload.recipient"]
    assert all(set(v) == {"field", "message"} for v in exc.value.violations)
    assert all(v["message"] for v in exc.value.violations)


def test_message_format():
    msg = SmsPolicy().prepare(draft(content="Hola <b>&", title="ignorado"))
    assert msg == OutboundMessage(
        channel="sms",
        recipient="+5219611234567",
        subject=None,
        body="Hola <b>&",
        html=None,
        data=None,
    )


def test_prepare_does_not_mutate_draft():
    d = draft()
    before = (d.title, d.content, d.recipient)
    SmsPolicy().prepare(d)
    assert (d.title, d.content, d.recipient) == before
