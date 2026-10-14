from __future__ import annotations

import pytest

from fastappi_notification.domain.channels.policy import ChannelDraft, OutboundMessage
from fastappi_notification.domain.channels.push import PushPolicy
from fastappi_notification.domain.errors import ChannelRuleViolation


def draft(recipient: str = "device-token_01", title: str = "Hola", content: str = "Mundo") -> ChannelDraft:
    return ChannelDraft(title=title, content=content, recipient=recipient)


def test_channel_name():
    assert PushPolicy.channel == "push"
    assert PushPolicy().channel == "push"


@pytest.mark.parametrize(
    "recipient",
    [
        "a" * 8,  # límite inferior
        "a" * 4096,  # límite superior
        "fcm:APA91b-Hx_y.z" + "0" * 10,
        "ABCDEFGH",
        "01234567",
        "a:b_c.d-e",
    ],
)
def test_valid_recipients(recipient):
    assert PushPolicy().prepare(draft(recipient=recipient)).recipient == recipient


@pytest.mark.parametrize(
    "recipient",
    [
        "",
        "a" * 7,  # 7 caracteres
        "a" * 4097,
        "abcd efgh",
        "abcdefg!",
        "abcdefg/",
        "abcdefgé",
        "abcdefg\n",
        " abcdefgh",
        "abcdefgh ",
        "abc+defgh",
        "abc=defgh",
    ],
)
def test_invalid_recipients(recipient):
    with pytest.raises(ChannelRuleViolation) as exc:
        PushPolicy().prepare(draft(recipient=recipient))
    assert [v["field"] for v in exc.value.violations] == ["payload.recipient"]
    assert exc.value.violations[0]["message"]


def test_message_format():
    msg = PushPolicy().prepare(draft(title="Hola", content="Mundo <b>"))
    assert msg == OutboundMessage(
        channel="push",
        recipient="device-token_01",
        subject=None,
        body="Mundo <b>",
        html=None,
        data={"title": "Hola", "body": "Mundo <b>"},
    )


def test_data_is_a_fresh_dict_per_call():
    policy = PushPolicy()
    d = draft()
    a, b = policy.prepare(d), policy.prepare(d)
    assert a.data == b.data
    assert a.data is not b.data


def test_prepare_does_not_mutate_draft():
    d = draft()
    before = (d.title, d.content, d.recipient)
    PushPolicy().prepare(d)
    assert (d.title, d.content, d.recipient) == before
