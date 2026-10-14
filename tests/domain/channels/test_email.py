from __future__ import annotations

import pytest

from fastappi_notification.domain.channels.email import EmailPolicy
from fastappi_notification.domain.channels.policy import ChannelDraft, OutboundMessage
from fastappi_notification.domain.errors import ChannelRuleViolation


def draft(recipient: str = "ana@example.com", title: str = "Hola", content: str = "Mundo") -> ChannelDraft:
    return ChannelDraft(title=title, content=content, recipient=recipient)


def test_channel_name():
    assert EmailPolicy.channel == "email"
    assert EmailPolicy().channel == "email"


@pytest.mark.parametrize(
    "recipient",
    ["a@b.c", "ana@example.com", "ana.perez+tag@mail.example.co", "a@b.c.d"],
)
def test_valid_recipients(recipient):
    msg = EmailPolicy().prepare(draft(recipient=recipient))
    assert msg.recipient == recipient


@pytest.mark.parametrize(
    "recipient",
    [
        "",
        "sin-arroba.com",
        "ana@",
        "@example.com",
        "ana@example",  # sin dominio de nivel superior
        "ana@example.",
        "ana@.com",
        "ana @example.com",
        "ana@exa mple.com",
        " ana@example.com",
        "ana@example.com ",
        "ana@example.com\n",
        "a@@b.c",
        "a@b@c.d",
    ],
)
def test_invalid_recipients(recipient):
    with pytest.raises(ChannelRuleViolation) as exc:
        EmailPolicy().prepare(draft(recipient=recipient))
    assert [v["field"] for v in exc.value.violations] == ["payload.recipient"]
    assert exc.value.violations[0]["message"]


def _email_of_length(n: int) -> str:
    suffix = "@example.com"
    return "a" * (n - len(suffix)) + suffix


def test_length_320_is_valid():
    recipient = _email_of_length(320)
    assert len(recipient) == 320
    assert EmailPolicy().prepare(draft(recipient=recipient)).recipient == recipient


def test_length_321_is_invalid():
    recipient = _email_of_length(321)
    assert len(recipient) == 321
    with pytest.raises(ChannelRuleViolation) as exc:
        EmailPolicy().prepare(draft(recipient=recipient))
    assert exc.value.violations[0]["field"] == "payload.recipient"


def test_message_format():
    msg = EmailPolicy().prepare(draft(title="Hola", content="Mundo"))
    assert msg == OutboundMessage(
        channel="email",
        recipient="ana@example.com",
        subject="Hola",
        body="Mundo",
        html="<h1>Hola</h1><p>Mundo</p>",
        data=None,
    )


def test_html_escapes_title_and_content_but_not_subject_or_body():
    title = "<b>T & \"q\" 'x'</b>"
    content = "<script>alert('x')</script> & \"y\""
    msg = EmailPolicy().prepare(draft(title=title, content=content))
    assert msg.subject == title
    assert msg.body == content
    assert msg.html == (
        "<h1>&lt;b&gt;T &amp; &quot;q&quot; &#x27;x&#x27;&lt;/b&gt;</h1>"
        "<p>&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt; &amp; &quot;y&quot;</p>"
    )


def test_does_not_trim_or_normalize_recipient():
    with pytest.raises(ChannelRuleViolation):
        EmailPolicy().prepare(draft(recipient="  ana@example.com"))
    msg = EmailPolicy().prepare(draft(recipient="Ana@Example.COM"))
    assert msg.recipient == "Ana@Example.COM"


def test_prepare_does_not_mutate_draft():
    d = draft()
    before = (d.title, d.content, d.recipient)
    EmailPolicy().prepare(d)
    assert (d.title, d.content, d.recipient) == before


def test_draft_and_message_are_frozen():
    from dataclasses import FrozenInstanceError

    d = draft()
    with pytest.raises(FrozenInstanceError):
        d.title = "x"  # type: ignore[misc]
    msg = EmailPolicy().prepare(d)
    with pytest.raises(FrozenInstanceError):
        msg.body = "x"  # type: ignore[misc]
