import pytest

from app.services.email_messages import (
    build_link,
    describe_minutes,
    password_changed_message,
    password_reset_message,
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

def reset_message(**overrides):
    kwargs = dict(
        to="mostafa@example.com", name="Mostafa", link=LINK, valid_for_minutes=30
    )
    kwargs.update(overrides)
    return password_reset_message(**kwargs)


def test_reset_message_is_addressed_and_titled():
    m = reset_message()
    assert m.to == "mostafa@example.com"
    assert m.subject == "Reset your Immersely password"


def test_reset_body_contains_the_link_the_name_and_the_lifetime():
    body = reset_message().text_body
    assert LINK in body
    assert "Hi Mostafa," in body
    assert "30 minutes" in body


def test_reset_body_says_the_link_works_once_and_can_be_ignored():
    body = reset_message().text_body
    assert "works once" in body
    assert "ignore" in body


def test_reset_link_appears_exactly_once():
    assert reset_message().text_body.count(LINK) == 1


def test_reset_without_a_name_uses_a_generic_greeting():
    body = reset_message(name=None).text_body
    assert "Hi there," in body
    assert "None" not in body


def test_changed_notice_is_addressed_and_titled():
    m = password_changed_message(to="mostafa@example.com", name="Mostafa")
    assert m.to == "mostafa@example.com"
    assert m.subject == "Your Immersely password was changed"
    assert "Hi Mostafa," in m.text_body


def test_changed_notice_contains_no_link():
    body = password_changed_message(to="a@b.com", name="Mostafa").text_body
    assert "http" not in body
    assert "#token" not in body


def test_changed_notice_without_a_name_uses_a_generic_greeting():
    body = password_changed_message(to="a@b.com", name=None).text_body
    assert "Hi there," in body
    assert "None" not in body


def test_changed_notice_tells_the_user_what_to_do_if_it_was_not_them():
    body = password_changed_message(to="a@b.com", name="Mostafa").text_body
    assert "request a new password reset" in body