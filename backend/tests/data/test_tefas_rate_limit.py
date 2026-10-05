from __future__ import annotations

import httpx

from app.data.providers.tefas import TefasProvider, TefasSettings


def test_tefas_post_retries_429_then_succeeds(monkeypatch):
    calls = []

    def request(method, url, **kwargs):
        calls.append(len(calls))
        if len(calls) == 1:
            return httpx.Response(429, request=httpx.Request(method, url))
        return httpx.Response(
            200,
            json={"resultList": []},
            request=httpx.Request(method, url),
        )

    sleeps = []
    monkeypatch.setattr("app.data.providers.tefas.sleep", sleeps.append)

    provider = TefasProvider(
        settings=TefasSettings(rate_limit_retries=2, rate_limit_backoff_seconds=2.0),
        request=request,
    )

    result = provider._post("fonGnlBlgSiraliGetir", {})

    assert result == {"resultList": []}
    assert len(calls) == 2
    assert sleeps == [2.0]


def test_tefas_post_raises_after_exhausting_rate_limit_retries(monkeypatch):
    def request(method, url, **kwargs):
        return httpx.Response(429, request=httpx.Request(method, url))

    sleeps = []
    monkeypatch.setattr("app.data.providers.tefas.sleep", sleeps.append)

    provider = TefasProvider(
        settings=TefasSettings(rate_limit_retries=2, rate_limit_backoff_seconds=1.0),
        request=request,
    )

    try:
        provider._post("fonGnlBlgSiraliGetir", {})
    except Exception as exc:
        assert type(exc).__name__ == "TefasProviderError"
    else:
        raise AssertionError("expected TefasProviderError")

    assert sleeps == [1.0, 2.0]


def test_tefas_post_retries_transient_transport_error_then_succeeds(monkeypatch):
    calls = []

    def request(method, url, **kwargs):
        calls.append(len(calls))
        if len(calls) == 1:
            raise httpx.RemoteProtocolError(
                "Server disconnected without sending a response",
                request=httpx.Request(method, url),
            )
        return httpx.Response(
            200,
            json={"resultList": []},
            request=httpx.Request(method, url),
        )

    sleeps = []
    monkeypatch.setattr("app.data.providers.tefas.sleep", sleeps.append)

    provider = TefasProvider(
        settings=TefasSettings(rate_limit_retries=2, rate_limit_backoff_seconds=2.0),
        request=request,
    )

    result = provider._post("fonGnlBlgSiraliGetir", {})

    assert result == {"resultList": []}
    assert len(calls) == 2
    assert sleeps == [2.0]


def test_tefas_post_retries_transient_non_json_response_then_succeeds(monkeypatch):
    calls = []

    def request(method, url, **kwargs):
        calls.append(len(calls))
        request_obj = httpx.Request(method, url)
        if len(calls) == 1:
            return httpx.Response(
                200,
                text="<html>temporarily blocked</html>",
                headers={"Content-Type": "text/html"},
                request=request_obj,
            )
        return httpx.Response(
            200,
            json={"resultList": []},
            request=request_obj,
        )

    sleeps = []
    monkeypatch.setattr("app.data.providers.tefas.sleep", sleeps.append)

    provider = TefasProvider(
        settings=TefasSettings(rate_limit_retries=2, rate_limit_backoff_seconds=2.0),
        request=request,
    )

    result = provider._post("fonGnlBlgSiraliGetir", {})

    assert result == {"resultList": []}
    assert len(calls) == 2
    assert sleeps == [2.0]


def test_tefas_post_reports_non_json_response_after_retries(monkeypatch):
    def request(method, url, **kwargs):
        return httpx.Response(
            200,
            text="temporarily blocked",
            headers={"Content-Type": "text/html"},
            request=httpx.Request(method, url),
        )

    sleeps = []
    monkeypatch.setattr("app.data.providers.tefas.sleep", sleeps.append)

    provider = TefasProvider(
        settings=TefasSettings(rate_limit_retries=1, rate_limit_backoff_seconds=1.0),
        request=request,
    )

    try:
        provider._post("fonGnlBlgSiraliGetir", {})
    except Exception as exc:
        assert type(exc).__name__ == "TefasProviderError"
        assert "non-JSON response" in str(exc)
        assert "content_type=text/html" in str(exc)
        assert "temporarily blocked" in str(exc)
    else:
        raise AssertionError("expected TefasProviderError")

    assert sleeps == [1.0]
