import pytest

from app.services.email_messages import (
    build_link,
    describe_minutes,
    verification_message,
)

TOKEN = "abc_DEF-123"
LINK = "https://x.test/verify-email#token=T"


def test_build_link_puts_the_token_in_the_fragment():
    assert build_link("http://localhost:5173", "verify-email", TOKEN) == (
        "http://localhost:5173/verify-email#token=abc_DEF-123"
    )


@pytest.mark.parametrize(
    "base, path",
    [
        ("http://localhost:5173/", "verify-email"),
        ("http://localhost:5173", "/verify-email"),
        ("http://localhost:5173//", "//verify-email"),
    ],
)
def test_slashes_at_the_join_are_normalized(base, path):
    assert build_link(base, path, TOKEN) == (
        "http://localhost:5173/verify-email#token=abc_DEF-123"
    )


def test_the_token_is_never_in_a_query_string():
    link = build_link("https://app.example.test", "verify-email", TOKEN)
    assert "?" not in link
    assert link.split("#", 1)[0] == "https://app.example.test/verify-email"


def test_unsafe_characters_are_escaped_not_injected():
    link = build_link("https://app.example.test", "verify-email", "a b&c#d")
    assert link.count("#") == 1  # only the real fragment marker
    assert " " not in link
    assert "&" not in link


@pytest.mark.parametrize(
    "minutes, expected",
    [
        (1, "1 minute"),
        (30, "30 minutes"),
        (60, "1 hour"),
        (90, "90 minutes"),
        (120, "2 hours"),
        (1440, "24 hours"),
    ],
)
def test_describe_minutes(minutes, expected):
    assert describe_minutes(minutes) == expected


def message(**overrides):
    kwargs = dict(
        to="mostafa@example.com", name="Mostafa", link=LINK, valid_for_minutes=1440
    )
    kwargs.update(overrides)
    return verification_message(**kwargs)


def test_message_is_addressed_and_titled():
    m = message()
    assert m.to == "mostafa@example.com"
    assert m.subject == "Verify your email for Immersely"


def test_body_contains_the_link_the_name_and_the_lifetime():
    body = message().text_body
    assert LINK in body
    assert "Hi Mostafa," in body
    assert "24 hours" in body


def test_body_without_a_name_falls_back_to_a_generic_greeting():
    body = message(name=None).text_body
    assert "Hi there," in body
    assert "None" not in body


def test_the_link_appears_exactly_once():
    assert message().text_body.count(LINK) == 1