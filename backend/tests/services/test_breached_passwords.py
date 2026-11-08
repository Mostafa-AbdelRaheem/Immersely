import asyncio
import logging

import httpx
import pytest

from app.services.breach_logic import sha1_prefix_suffix
from app.services.breached_passwords import count_breaches, is_password_breached

LOGGER_NAME = "app.services.breached_passwords"
_, PASSWORD_SUFFIX = sha1_prefix_suffix("password")  # prefix is 5BAA6


def run_check(password, handler):
    """Run is_password_breached against a fake transport (no network)."""

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await is_password_breached(password, timeout_s=1, client=client)

    return asyncio.run(go())


def test_breached_password_returns_true():
    def handler(request):
        return httpx.Response(200, text=f"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA:2\r\n{PASSWORD_SUFFIX}:3")

    assert run_check("password", handler) is True


def test_request_sends_only_the_prefix_and_required_headers():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["user_agent"] = request.headers["user-agent"]
        seen["padding"] = request.headers["add-padding"]
        return httpx.Response(200, text="")

    run_check("password", handler)

    assert seen["url"] == "https://api.pwnedpasswords.com/range/5BAA6"
    assert PASSWORD_SUFFIX not in seen["url"]
    assert seen["user_agent"] == "immersely-password-check"
    assert seen["padding"] == "true"


def test_unbreached_password_returns_false():
    def handler(request):
        return httpx.Response(200, text="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA:2")

    assert run_check("password", handler) is False


def test_padded_zero_count_entry_is_not_breached():
    def handler(request):
        return httpx.Response(200, text=f"{PASSWORD_SUFFIX}:0")

    assert run_check("password", handler) is False


def test_server_error_fails_open_and_logs_a_warning(caplog):
    def handler(request):
        return httpx.Response(500)

    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        assert run_check("password", handler) is False

    assert any("fail-open" in message for message in caplog.messages)


@pytest.mark.parametrize(
    "error", [httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError]
)
def test_network_errors_fail_open(error):
    def handler(request):
        raise error("boom")

    assert run_check("password", handler) is False


def test_redirect_fails_open():
    def handler(request):
        return httpx.Response(302, headers={"Location": "https://example.invalid/"})

    assert run_check("password", handler) is False


def test_non_http_error_propagates():
    # A real bug must stay loud: only httpx errors are swallowed.
    def handler(request):
        raise RuntimeError("bug")

    with pytest.raises(RuntimeError):
        run_check("password", handler)


def test_log_never_contains_the_password_or_its_hash_prefix(caplog):
    password = "Tr0ub4dor&3-sentinel"
    prefix, _ = sha1_prefix_suffix(password)

    def handler(request):
        # The exception message itself carries the URL (and so the prefix).
        raise httpx.ConnectError(f"failed for {request.url}")

    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        run_check(password, handler)

    logged = " ".join(caplog.messages)
    assert "ConnectError" in logged
    assert password not in logged
    assert prefix not in logged


def test_count_breaches_raises_on_server_error():
    def handler(request):
        return httpx.Response(500)

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await count_breaches("password", client=client)

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(go())