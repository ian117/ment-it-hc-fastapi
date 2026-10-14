import pytest

from fastappi_notification.domain.email import EMAIL_PATTERN, MAX_EMAIL_LENGTH, Email
from fastappi_notification.domain.errors import InvalidEmail


def test_normaliza_a_minusculas_y_recorta():
    assert Email.create("  Ana@Example.COM ").value == "ana@example.com"


def test_igualdad_por_valor():
    assert Email.create("A@b.co") == Email.create("a@B.CO")


@pytest.mark.parametrize(
    "raw", ["", "   ", "sin-arroba", "a@b", "a@@b.co", "a b@c.co", "@b.co", "a@.co"]
)
def test_invalido_lanza_invalid_email(raw):
    with pytest.raises(InvalidEmail):
        Email.create(raw)


def test_maximo_320_caracteres():
    ok = "a" * (MAX_EMAIL_LENGTH - len("@b.co")) + "@b.co"
    assert len(ok) == MAX_EMAIL_LENGTH
    assert Email.create(ok).value == ok
    with pytest.raises(InvalidEmail):
        Email.create("a" + ok)


def test_comparte_patron_con_la_politica_de_email():
    from fastappi_notification.domain.channels import email as policy_module

    assert policy_module.EMAIL_PATTERN is EMAIL_PATTERN
    assert policy_module.MAX_EMAIL_LENGTH == MAX_EMAIL_LENGTH
