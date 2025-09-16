import logging

import httpx
import pytest

import orchestrator.external_info as external_info_module
from orchestrator.external_info import retrieve_external_info


class TestRetrieveExternalInfo:
    def test_returns_truncated_summary(self, monkeypatch):
        captured = {}

        def fake_get(url, timeout):
            captured["url"] = url
            captured["timeout"] = timeout
            request = httpx.Request("GET", url)
            return httpx.Response(
                status_code=200,
                json={"extract": "A" * 1200},
                request=request,
            )

        monkeypatch.setattr(external_info_module.httpx, "get", fake_get)

        result = retrieve_external_info("Sample Topic")

        assert len(result) == 1000
        assert result == "A" * 1000
        assert captured["timeout"] == 5.0

    def test_returns_empty_string_for_missing_summary(self, monkeypatch):
        def fake_get(url, timeout):
            request = httpx.Request("GET", url)
            return httpx.Response(status_code=404, request=request)

        monkeypatch.setattr(external_info_module.httpx, "get", fake_get)

        assert retrieve_external_info("Unknown Topic") == ""

    def test_returns_empty_string_when_request_fails(self, monkeypatch, caplog):
        def fake_get(url, timeout):
            raise httpx.RequestError("boom", request=httpx.Request("GET", url))

        monkeypatch.setattr(external_info_module.httpx, "get", fake_get)

        with caplog.at_level(logging.WARNING):
            assert retrieve_external_info("Network Issue") == ""

        assert "Failed to retrieve external info" in caplog.text

    @pytest.mark.parametrize("query", [123, "   "])
    def test_rejects_invalid_queries(self, query):
        with pytest.raises(ValueError):
            retrieve_external_info(query)

    def test_returns_empty_string_when_extract_missing(self, monkeypatch):
        def fake_get(url, timeout):
            request = httpx.Request("GET", url)
            return httpx.Response(status_code=200, json={}, request=request)

        monkeypatch.setattr(external_info_module.httpx, "get", fake_get)

        assert retrieve_external_info("No Extract") == ""
