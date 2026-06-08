"""Wrap shelf. LiteLLM routes; Instructor types. We add nothing but the seam.

Thinking-model-safe (v0.2). Two real gaps were found live against opencode zen:

1. ``structured()`` — instructor's default TOOLS mode sends ``tool_choice=required``,
   which thinking models (qwen3.6-plus, minimax-m3, deepseek-v4-flash) reject with a
   400 ("tool_choice ... not supported in thinking mode"). We default to instructor
   JSON mode (``Mode.JSON``) and keep a robust TOOLS->JSON fallback for callers that
   explicitly opt into TOOLS.

2. ``ask()`` — thinking models often place their output in the message's
   ``reasoning_content`` (or ``reasoning``) field and leave ``content`` empty,
   especially when the token budget is spent reasoning. When ``content`` is
   empty/None we fall back to ``reasoning_content`` / ``reasoning`` (and
   ``model_extra``) so ``ask()`` returns non-empty text.
"""

from __future__ import annotations

from typing import Any, TypeVar

import instructor
import litellm
from pydantic import BaseModel

from coactra.ai.protocols import Completer

T = TypeVar("T", bound=BaseModel)


def _extract_text(message: Any) -> str:
    """Return the model's text output.

    Prefer ``content``; on a thinking model with empty/None content, fall back to
    ``reasoning_content`` then ``reasoning`` (checked as attributes and inside
    ``model_extra``). Works for both plain dict messages and litellm Message objects.
    """
    content = (
        message.get("content") if isinstance(message, dict) else getattr(message, "content", None)
    )
    if content:
        return content

    for field in ("reasoning_content", "reasoning"):
        # litellm Message exposes these as attributes
        val = getattr(message, field, None)
        if val:
            return val
        # ...or buried in model_extra (provider passthrough)
        extra = getattr(message, "model_extra", None)
        if isinstance(extra, dict) and extra.get(field):
            return extra[field]
        # ...or a plain dict message
        if isinstance(message, dict) and message.get(field):
            return message[field]

    return content or ""


class BoundCompleter:
    """A Completer with provider config (api_base/api_key/defaults) pre-bound.

    Per-call kwargs override the bound defaults. This is the single litellm call path;
    ``LiteLLMCompleter`` is just the zero-binding case. Includes the reasoning_content
    fallback via ``_extract_text``.
    """

    def __init__(self, **bound: Any) -> None:
        self._bound = bound

    def complete(self, model: str, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        merged = {**self._bound, **kwargs}
        # model is per-call in the Completer Protocol; drop any stray bound model
        # so the positional arg always wins (no "multiple values for 'model'").
        merged.pop("model", None)
        resp = litellm.completion(model=model, messages=messages, **merged)
        return _extract_text(resp["choices"][0]["message"])


class LiteLLMCompleter(BoundCompleter):
    """Default Completer over litellm.completion with no pre-bound provider config.

    Equivalent to ``BoundCompleter()`` — kept as a named public default. The litellm
    routing and reasoning_content fallback live in the base class, so there is one
    implementation of the call path, not two that must stay in sync.
    """

    def __init__(self) -> None:
        super().__init__()


def _provider_config(
    api_base: str | None, api_key: str | None, defaults: dict[str, Any]
) -> dict[str, Any]:
    """Merge optional provider credentials into the default kwargs (omitting unset ones).

    Single source of truth for how ``api_base``/``api_key`` become litellm kwargs, so the
    Completer path (``make_completer``) and the Instructor path that bypasses the Completer
    (``Client.structured``) cannot silently drift when a config key is added.
    """
    cfg: dict[str, Any] = dict(defaults)
    if api_base is not None:
        cfg["api_base"] = api_base
    if api_key is not None:
        cfg["api_key"] = api_key
    return cfg


def make_completer(
    *,
    api_base: str | None = None,
    api_key: str | None = None,
    **defaults: Any,
) -> Completer:
    """Build a Completer with provider config pre-bound so callers stop repeating
    ``api_base``/``api_key`` (and any default kwargs) on every call. Injectable
    anywhere a ``Completer`` is expected (``ReasoningEngine``, ``ask``)."""
    return BoundCompleter(**_provider_config(api_base, api_key, defaults))


def ask(
    prompt: str,
    *,
    model: str = "gpt-4o-mini",
    completer: Completer | None = None,
    **kwargs: Any,
) -> str:
    """Call any model for free-text. completer is swappable; default = LiteLLM.

    On thinking models that return empty ``content`` (output in ``reasoning_content``),
    the default completer surfaces the reasoning text so this returns non-empty.
    """
    completer = completer or LiteLLMCompleter()
    return completer.complete(model, [{"role": "user", "content": prompt}], **kwargs)


def _is_tool_choice_error(exc: BaseException) -> bool:
    """True if the exception chain mentions an unsupported ``tool_choice`` — the
    signature of a thinking model rejecting instructor's TOOLS mode."""
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        if "tool_choice" in str(cur).lower():
            return True
        cur = cur.__cause__ or cur.__context__
    return False


def structured[T: BaseModel](
    schema: type[T],
    prompt: str,
    *,
    model: str = "gpt-4o-mini",
    mode: instructor.Mode = instructor.Mode.JSON,
    **kwargs: Any,
) -> T:
    """Typed output via Instructor (response_model enforcement) over LiteLLM.

    Defaults to instructor JSON mode (``Mode.JSON``) — thinking-model-safe, since
    TOOLS mode's ``tool_choice=required`` is rejected by reasoning models. If a
    caller explicitly passes ``mode=Mode.TOOLS`` and the provider rejects
    ``tool_choice``, we transparently fall back to JSON mode.
    """

    def _run(active_mode: instructor.Mode, **extra: Any) -> T:
        client = instructor.from_litellm(litellm.completion, mode=active_mode)
        return client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_model=schema,
            **{**kwargs, **extra},
        )

    if mode is instructor.Mode.TOOLS:
        try:
            # Surface the 400 immediately rather than burying it under retries.
            return _run(instructor.Mode.TOOLS, max_retries=kwargs.get("max_retries", 0))
        except Exception as exc:  # noqa: BLE001 - inspect then re-raise if unrelated
            if not _is_tool_choice_error(exc):
                raise
            return _run(instructor.Mode.JSON)

    return _run(mode)


class Client:
    """Provider facade so callers configure ``model``/``api_base``/``api_key`` once.

    ``ask()`` routes through the injected (or built) Completer Protocol.
    ``structured()`` threads the bound config as kwargs to the standalone
    ``structured()`` (which uses instructor directly, not the Completer). Standalone
    ``ask``/``structured`` and the DI Protocols remain fully usable.
    """

    def __init__(
        self,
        *,
        model: str,
        api_base: str | None = None,
        api_key: str | None = None,
        completer: Completer | None = None,
        **defaults: Any,
    ) -> None:
        self.model = model
        self._api_base = api_base
        self._api_key = api_key
        self._defaults = defaults
        self._completer = completer or make_completer(
            api_base=api_base, api_key=api_key, **defaults
        )

    def ask(self, prompt: str, **kwargs: Any) -> str:
        return ask(prompt, model=self.model, completer=self._completer, **kwargs)

    def structured(self, schema: type[T], prompt: str, **kwargs: Any) -> T:
        cfg = _provider_config(self._api_base, self._api_key, self._defaults)
        return structured(schema, prompt, model=self.model, **{**cfg, **kwargs})
