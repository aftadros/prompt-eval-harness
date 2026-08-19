"""Model adapters.

Two HTTP endpoints, one Protocol, no vendor SDKs. Both providers here are a
single POST with a JSON body; importing two heavyweight packages to make two POST
requests would contradict the one architectural rule this repo has. The fields
a run keeps (text, the server-reported model id, usage) are three key lookups
on the response body, so the SDKs' main convenience, typed access to fields,
buys nothing that `raw["choices"][0]` does not.

The adapters are deliberately dumb. Text in, text out. No retry policy beyond one
attempt on a connection error, no streaming, no token accounting beyond what the
server reports. Everything interesting about a run is decided by the prompt, the
cases and the checks, and an adapter that started making decisions would be
another variable to control for.
"""

from __future__ import annotations

import http.client
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

import yaml

#: Generous on purpose. A local server under a concurrent batch can take minutes
#: on a single generation, and a timeout tuned for a hosted endpoint turns that
#: into a failed overnight run.
DEFAULT_TIMEOUT = 900
#: Bounded, and bounded low, which is the policy the corpus this harness runs
#: over recommends for exactly this situation.
MAX_ATTEMPTS = 3


class ModelError(RuntimeError):
    """The endpoint could not be used. Raised early and loudly."""


@dataclass(frozen=True)
class Decoding:
    temperature: float = 0.7
    top_p: float | None = 0.95
    max_tokens: int = 1024
    #: Passed through when the server accepts it. Recorded either way, and never
    #: trusted: reruns are the mechanism for handling nondeterminism here, not
    #: seeds, because seed handling is inconsistent across local backends and a
    #: run that quietly ignored its seed looks identical to one that honored it.
    seed: int | None = None

    def as_dict(self) -> dict:
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
            "seed": self.seed,
        }


@dataclass(frozen=True)
class Completion:
    text: str
    model_reported: str
    usage: dict | None
    raw: dict

    @property
    def is_empty(self) -> bool:
        """No content at all.

        This happens on reasoning models when the whole `max_tokens` budget goes
        to reasoning and the server strips those tokens from `content`. The
        result is a completed HTTP 200 carrying nothing, which is a rig condition
        rather than an answer, and it must never be scored as one: an empty
        string fails `must_refuse` and passes `must_not_cite` and
        `must_not_contain` vacuously, so it looks exactly like a refusal
        regression with specific evidence behind it.
        """
        return not self.text.strip()


class Model(Protocol):
    name: str

    def complete(self, system: str, user: str, decoding: Decoding) -> Completion: ...


def _post(url: str, payload: dict, headers: dict, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """POST with bounded retries on transient failures only.

    Transient means a connection error or a read timeout. Everything else fails
    immediately, because retrying a 400 buys the same 400 twice and spends the
    user's time to do it. That is the retry policy from the corpus this harness
    runs over, applied to the harness itself.

    The timeout case is the one that matters here and it is easy to get wrong:
    `socket.timeout` is raised as a builtin `TimeoutError`, which is NOT a
    subclass of `urllib.error.URLError`. An except clause that catches only
    URLError looks like it handles timeouts and does not, so one slow generation
    two hundred calls into an overnight batch takes the whole batch down. That
    happened, which is why the class is named explicitly below.
    """
    body = json.dumps(payload).encode("utf-8")
    last: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        for k, v in headers.items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            if exc.code == 429 or exc.code >= 500:
                last = exc
            else:
                raise ModelError(f"{url} returned {exc.code}: {detail}") from exc
        except (
            TimeoutError,
            urllib.error.URLError,
            # OSError covers ConnectionError, ssl.SSLError and socket errors; the
            # HTTPException branch is IncompleteRead and RemoteDisconnected when
            # the server drops mid-body, which a local server reloading a model
            # does; a non-JSON 200 (a proxy page) is the same transient shape.
            OSError,
            http.client.HTTPException,
            json.JSONDecodeError,
        ) as exc:
            last = exc
        if attempt < MAX_ATTEMPTS - 1:
            time.sleep(2**attempt)
    raise ModelError(
        f"{url} failed after {MAX_ATTEMPTS} attempts (timeout={timeout}s): {last}"
    ) from last


class OpenAICompat:
    """LM Studio, vLLM, llama.cpp server, and anything else speaking the shape."""

    def __init__(self, name: str, base_url: str, model: str, api_key_env: str | None = None):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = os.environ.get(api_key_env) if api_key_env else None
        if api_key_env and not self.api_key:
            raise ModelError(f"{name}: {api_key_env} is not set")

    def server_models(self) -> list[str]:
        """What the server says it is serving right now."""
        req = urllib.request.Request(f"{self.base_url}/models")
        if self.api_key:
            req.add_header("Authorization", f"Bearer {self.api_key}")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise ModelError(f"{self.base_url}/models unreachable: {exc}") from exc
        return [m["id"] for m in data.get("data", [])]

    def preflight(self) -> str:
        """Fail before the run if the server is not serving what we asked for.

        LM Studio will answer a request for an unknown model id out of whatever
        happens to be loaded, so a typo or a swapped model produces a complete,
        plausible run attributed to a model that never ran. Checking once at the
        start costs one request and removes an entire class of silently wrong
        results.
        """
        served = self.server_models()
        if self.model not in served:
            raise ModelError(
                f"{self.name}: models.yaml asks for {self.model!r} but the server at "
                f"{self.base_url} is serving {served}. This endpoint will answer anyway, "
                "out of whatever is loaded, so the run would be attributed to the wrong model."
            )
        return self.model

    def complete(self, system: str, user: str, decoding: Decoding) -> Completion:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": decoding.temperature,
            "max_tokens": decoding.max_tokens,
            "stream": False,
        }
        if decoding.top_p is not None:
            payload["top_p"] = decoding.top_p
        if decoding.seed is not None:
            payload["seed"] = decoding.seed
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        raw = _post(f"{self.base_url}/chat/completions", payload, headers)
        try:
            text = raw["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise ModelError(f"unexpected response shape: {json.dumps(raw)[:400]}") from exc
        return Completion(
            text=text or "",
            model_reported=raw.get("model", self.model),
            usage=raw.get("usage"),
            raw=raw,
        )


def complete_with_content(mdl, system: str, user: str, decoding: Decoding) -> Completion:
    """Call the model, retrying an empty completion as the transient failure it is.

    An empty body is not the model's answer to the question; it is the model
    running out of budget before it started answering. Retrying is right for the
    same reason retrying a 429 is right and retrying a 400 is not: the input was
    fine and the condition is not about the input. If it is still empty after the
    bounded retries, the caller records it as missing data rather than as a
    failed check.
    """
    last = None
    for _ in range(MAX_ATTEMPTS):
        last = mdl.complete(system, user, decoding)
        if not last.is_empty:
            return last
    return last


class AnthropicMessages:
    """POST /v1/messages."""

    API_VERSION = "2023-06-01"

    def __init__(self, name: str, base_url: str, model: str, api_key_env: str):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = os.environ.get(api_key_env)
        if not self.api_key:
            # A missing key is a config error at minute zero, not a stack trace
            # at case 37 of an overnight run.
            raise ModelError(f"{name}: {api_key_env} is not set")

    def preflight(self) -> str:
        return self.model

    def complete(self, system: str, user: str, decoding: Decoding) -> Completion:
        payload: dict[str, Any] = {
            "model": self.model,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "max_tokens": decoding.max_tokens,
            "temperature": decoding.temperature,
        }
        if decoding.top_p is not None:
            payload["top_p"] = decoding.top_p
        headers = {"x-api-key": self.api_key, "anthropic-version": self.API_VERSION}
        raw = _post(f"{self.base_url}/v1/messages", payload, headers)
        try:
            parts = [b.get("text", "") for b in raw["content"] if b.get("type") == "text"]
        except (KeyError, TypeError) as exc:
            raise ModelError(f"unexpected response shape: {json.dumps(raw)[:400]}") from exc
        return Completion(
            text="".join(parts),
            model_reported=raw.get("model", self.model),
            usage=raw.get("usage"),
            raw=raw,
        )


def load_config(path: str | None = None) -> dict:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = path or os.path.join(root, "models.yaml")
    return yaml.safe_load(open(path, encoding="utf-8"))


def build(name: str, config: dict | None = None) -> OpenAICompat | AnthropicMessages:
    config = config or load_config()
    entry = config.get("models", {}).get(name)
    if entry is None:
        known = ", ".join(sorted(config.get("models", {})))
        raise ModelError(f"unknown model {name!r} in models.yaml. Known: {known}")
    kind = entry["kind"]
    if kind == "openai_compat":
        return OpenAICompat(name, entry["base_url"], entry["model"], entry.get("api_key_env"))
    if kind == "anthropic":
        return AnthropicMessages(name, entry["base_url"], entry["model"], entry["api_key_env"])
    raise ModelError(f"unknown adapter kind {kind!r} for model {name!r}")
