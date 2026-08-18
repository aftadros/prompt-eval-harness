"""Adapter behavior that does not need a server.

The retry classification gets a test because it already cost a 250-call batch
once: `socket.timeout` surfaces as a builtin `TimeoutError`, which is not a
subclass of `urllib.error.URLError`, so an except clause that reads as though it
handles timeouts silently does not.
"""

import json
import urllib.error
from unittest import mock

import pytest

from harness import model as model_mod


def fake_response(payload):
    class R:
        def read(self):
            return json.dumps(payload).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    return R()


def test_timeout_error_is_not_a_urlerror():
    """The premise of the bug, asserted so nobody 'simplifies' the except clause."""
    assert not issubclass(TimeoutError, urllib.error.URLError)


def test_post_retries_a_timeout_then_succeeds():
    calls = {"n": 0}

    def urlopen(req, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise TimeoutError("timed out")
        return fake_response({"ok": True})

    with mock.patch("urllib.request.urlopen", urlopen), mock.patch("time.sleep"):
        assert model_mod._post("http://x/y", {}, {}) == {"ok": True}
    assert calls["n"] == 2


def test_post_gives_up_after_the_bounded_number_of_attempts():
    def urlopen(req, timeout=None):
        raise TimeoutError("timed out")

    with mock.patch("urllib.request.urlopen", urlopen), mock.patch("time.sleep"):
        with pytest.raises(model_mod.ModelError) as exc:
            model_mod._post("http://x/y", {}, {})
    assert "after 3 attempts" in str(exc.value)


def test_post_does_not_retry_a_client_error():
    """Retrying a 400 buys the same 400 twice."""
    calls = {"n": 0}

    def urlopen(req, timeout=None):
        calls["n"] += 1
        raise urllib.error.HTTPError("http://x/y", 400, "Bad Request", {}, None)

    with mock.patch("urllib.request.urlopen", urlopen), mock.patch("time.sleep"):
        with pytest.raises(model_mod.ModelError):
            model_mod._post("http://x/y", {}, {})
    assert calls["n"] == 1


def test_post_retries_a_server_error():
    calls = {"n": 0}

    def urlopen(req, timeout=None):
        calls["n"] += 1
        if calls["n"] < 3:
            raise urllib.error.HTTPError("http://x/y", 503, "Unavailable", {}, None)
        return fake_response({"ok": True})

    with mock.patch("urllib.request.urlopen", urlopen), mock.patch("time.sleep"):
        assert model_mod._post("http://x/y", {}, {}) == {"ok": True}
    assert calls["n"] == 3


def test_preflight_refuses_a_model_the_server_is_not_serving():
    """LM Studio answers for an unknown id out of whatever is loaded, so without
    this check a run is silently attributed to a model that never ran."""
    m = model_mod.OpenAICompat("local", "http://x/v1", "model-a")
    with mock.patch.object(m, "server_models", return_value=["model-b"]):
        with pytest.raises(model_mod.ModelError) as exc:
            m.preflight()
    assert "attributed to the wrong model" in str(exc.value)


def test_preflight_passes_when_the_server_agrees():
    m = model_mod.OpenAICompat("local", "http://x/v1", "model-a")
    with mock.patch.object(m, "server_models", return_value=["model-a", "other"]):
        assert m.preflight() == "model-a"


def test_anthropic_adapter_fails_fast_without_a_key(monkeypatch):
    """A missing key is a config error at minute zero, not a stack trace at case 37."""
    monkeypatch.delenv("PEH_TEST_KEY", raising=False)
    with pytest.raises(model_mod.ModelError) as exc:
        model_mod.AnthropicMessages("claude", "https://api.anthropic.com", "m", "PEH_TEST_KEY")
    assert "PEH_TEST_KEY is not set" in str(exc.value)


def test_build_rejects_an_unknown_model_name():
    with pytest.raises(model_mod.ModelError) as exc:
        model_mod.build("nope", {"models": {"local": {"kind": "openai_compat"}}})
    assert "Known: local" in str(exc.value)


def test_decoding_is_recorded_even_when_the_seed_is_unused():
    """The manifest records the requested seed; nothing here claims the server
    honored it, because local backends are inconsistent about that and a run
    that ignored its seed looks identical to one that did not."""
    d = model_mod.Decoding(temperature=0.7, top_p=0.95, max_tokens=1024, seed=42)
    assert d.as_dict()["seed"] == 42
