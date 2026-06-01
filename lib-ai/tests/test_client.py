from unittest.mock import MagicMock, patch

from pydantic import BaseModel

from fleetlib.ai.client import ask, structured, LiteLLMCompleter


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
