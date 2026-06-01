from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pydantic import BaseModel

from fleetlib.ai.client import ask, structured, LiteLLMCompleter, make_completer, Client


def test_ask_passes_through_to_completer():
    fake = MagicMock()
    fake.complete.return_value = "hi there"
    out = ask("say hi", model="gpt-4o-mini", completer=fake)
    assert out == "hi there"
    fake.complete.assert_called_once()


def test_litellm_completer_extracts_content():
    resp = {"choices": [{"message": {"content": "yo"}}]}
    with patch("fleetlib.ai.client.litellm.completion", return_value=resp):
        out = LiteLLMCompleter().complete("gpt-4o-mini", [{"role": "user", "content": "x"}])
    assert out == "yo"


def test_structured_uses_instructor_response_model():
    class Person(BaseModel):
        name: str

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = Person(name="Ada")
    with patch("fleetlib.ai.client.instructor.from_litellm", return_value=fake_client):
        out = structured(Person, "who?", model="gpt-4o-mini")
    assert out == Person(name="Ada")
    _, kwargs = fake_client.chat.completions.create.call_args
    assert kwargs["response_model"] is Person


# --- FIX 2: ask() reasoning fallback on thinking models ---


def test_completer_falls_back_to_reasoning_content_when_content_empty():
    """Thinking models put output in reasoning_content; content is empty/None."""
    msg = SimpleNamespace(content="", reasoning_content="the chain of thought", reasoning=None)
    resp = {"choices": [{"message": msg}]}
    with patch("fleetlib.ai.client.litellm.completion", return_value=resp):
        out = LiteLLMCompleter().complete("openai/minimax-m3", [{"role": "user", "content": "x"}])
    assert out == "the chain of thought"


def test_completer_falls_back_to_reasoning_field():
    msg = SimpleNamespace(content=None, reasoning_content=None, reasoning="alt reasoning field")
    resp = {"choices": [{"message": msg}]}
    with patch("fleetlib.ai.client.litellm.completion", return_value=resp):
        out = LiteLLMCompleter().complete("openai/x", [{"role": "user", "content": "x"}])
    assert out == "alt reasoning field"


def test_completer_reasoning_in_model_extra():
    msg = SimpleNamespace(content="", reasoning_content=None, reasoning=None,
                          model_extra={"reasoning_content": "from model_extra"})
    resp = {"choices": [{"message": msg}]}
    with patch("fleetlib.ai.client.litellm.completion", return_value=resp):
        out = LiteLLMCompleter().complete("openai/x", [{"role": "user", "content": "x"}])
    assert out == "from model_extra"


def test_completer_prefers_content_when_present():
    msg = SimpleNamespace(content="real answer", reasoning_content="thoughts", reasoning=None)
    resp = {"choices": [{"message": msg}]}
    with patch("fleetlib.ai.client.litellm.completion", return_value=resp):
        out = LiteLLMCompleter().complete("openai/x", [{"role": "user", "content": "x"}])
    assert out == "real answer"


def test_completer_plain_dict_message_still_works():
    """Backwards-compat: plain dict message (no reasoning fields) must still work."""
    resp = {"choices": [{"message": {"content": "yo"}}]}
    with patch("fleetlib.ai.client.litellm.completion", return_value=resp):
        out = LiteLLMCompleter().complete("gpt-4o-mini", [{"role": "user", "content": "x"}])
    assert out == "yo"


# --- FIX 1: structured() JSON mode default + TOOLS->JSON fallback ---


def test_structured_defaults_to_json_mode():
    class Person(BaseModel):
        name: str

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = Person(name="Ada")
    with patch("fleetlib.ai.client.instructor.from_litellm", return_value=fake_client) as ffl:
        structured(Person, "who?", model="openai/qwen3.6-plus")
    # default mode must be JSON (thinking-model-safe)
    _, kwargs = ffl.call_args
    assert kwargs.get("mode") is instructor_Mode().JSON


def test_structured_tools_falls_back_to_json_on_tool_choice_error():
    class Person(BaseModel):
        name: str

    import instructor as _inst

    # First (TOOLS) client raises a tool_choice 400; second (JSON) succeeds.
    tools_client = MagicMock()
    tools_client.chat.completions.create.side_effect = Exception(
        "litellm.BadRequestError: The tool_choice parameter is not supported in thinking mode"
    )
    json_client = MagicMock()
    json_client.chat.completions.create.return_value = Person(name="Ada")

    def from_litellm(_fn, *, mode):
        return tools_client if mode is _inst.Mode.TOOLS else json_client

    with patch("fleetlib.ai.client.instructor.from_litellm", side_effect=from_litellm):
        out = structured(Person, "who?", model="openai/qwen3.6-plus", mode=_inst.Mode.TOOLS)
    assert out == Person(name="Ada")
    json_client.chat.completions.create.assert_called_once()


def test_structured_tools_reraises_non_tool_choice_error():
    class Person(BaseModel):
        name: str

    import instructor as _inst

    tools_client = MagicMock()
    tools_client.chat.completions.create.side_effect = Exception("some unrelated 500 error")

    with patch("fleetlib.ai.client.instructor.from_litellm", return_value=tools_client):
        try:
            structured(Person, "who?", model="openai/x", mode=_inst.Mode.TOOLS)
            assert False, "should have re-raised"
        except Exception as e:
            assert "unrelated" in str(e)


def instructor_Mode():
    import instructor

    return instructor.Mode


# --- Cleanup: make_completer factory + Client facade ---


def test_make_completer_binds_api_base_and_key():
    captured = {}

    def fake_completion(**kw):
        captured.update(kw)
        return {"choices": [{"message": {"content": "ok"}}]}

    comp = make_completer(api_base="https://zen/v1", api_key="secret")
    with patch("fleetlib.ai.client.litellm.completion", side_effect=fake_completion):
        out = comp.complete("openai/qwen3.6-plus", [{"role": "user", "content": "hi"}])
    assert out == "ok"
    assert captured["api_base"] == "https://zen/v1"
    assert captured["api_key"] == "secret"


def test_make_completer_per_call_kwargs_override():
    captured = {}

    def fake_completion(**kw):
        captured.update(kw)
        return {"choices": [{"message": {"content": "ok"}}]}

    comp = make_completer(api_base="https://default/v1", api_key="k", temperature=0.0)
    with patch("fleetlib.ai.client.litellm.completion", side_effect=fake_completion):
        comp.complete("openai/x", [{"role": "user", "content": "hi"}], temperature=0.9)
    assert captured["temperature"] == 0.9  # per-call wins


def test_make_completer_tolerates_bound_model():
    """The DESIGN.md example uses make_completer(model=...); a stray bound model
    must not collide with the per-call model arg."""
    captured = {}

    def fake_completion(**kw):
        captured.update(kw)
        return {"choices": [{"message": {"content": "ok"}}]}

    comp = make_completer(model="openai/qwen3.6-plus", api_base="https://zen/v1", api_key="k")
    with patch("fleetlib.ai.client.litellm.completion", side_effect=fake_completion):
        out = comp.complete("openai/qwen3.6-plus", [{"role": "user", "content": "hi"}])
    assert out == "ok"
    assert captured["model"] == "openai/qwen3.6-plus"


def test_client_ask_routes_through_bound_completer():
    fake = MagicMock()
    fake.complete.return_value = "client says hi"
    c = Client(model="openai/qwen3.6-plus", completer=fake)
    out = c.ask("hi")
    assert out == "client says hi"
    args, _ = fake.complete.call_args
    assert args[0] == "openai/qwen3.6-plus"


def test_client_structured_threads_config_to_standalone_structured():
    class Person(BaseModel):
        name: str

    c = Client(model="openai/qwen3.6-plus", api_base="https://zen/v1", api_key="secret")
    with patch("fleetlib.ai.client.structured") as fake_structured:
        fake_structured.return_value = Person(name="Ada")
        out = c.structured(Person, "who?")
    assert out == Person(name="Ada")
    _, kwargs = fake_structured.call_args
    assert kwargs["model"] == "openai/qwen3.6-plus"
    assert kwargs["api_base"] == "https://zen/v1"
    assert kwargs["api_key"] == "secret"
