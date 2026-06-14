"""Tests for the Graphiti LLMClient backed by coactra.ai."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

pytest.importorskip("graphiti_core")

from graphiti_core.llm_client.config import ModelSize  # noqa: E402
from graphiti_core.prompts.models import Message  # noqa: E402

from coactra.memory.integrations import (  # noqa: E402
    GraphitiAIClient,
    GraphitiEmbeddingClient,
    GraphitiEmbeddingReranker,
)


class Entities(BaseModel):
    extracted_entities: list[str]


class _FakeAIClient:
    def __init__(self, *, name: str = "main") -> None:
        self.name = name
        self.structured_calls: list[tuple[type[BaseModel], str, dict]] = []
        self.ask_calls: list[tuple[str, dict]] = []

    def structured(self, schema, prompt, **kwargs):  # noqa: ANN001
        self.structured_calls.append((schema, prompt, kwargs))
        return schema(extracted_entities=[self.name])

    def ask(self, prompt: str, **kwargs):  # noqa: ANN001
        self.ask_calls.append((prompt, kwargs))
        return f'```json\n{{"ok": true, "client": "{self.name}"}}\n```'


@pytest.mark.asyncio
async def test_graphiti_ai_client_routes_schema_calls_through_structured() -> None:
    ai = _FakeAIClient()
    client = GraphitiAIClient(ai_client=ai, model="openai/qwen", api_base="https://llm.test/v1")

    out = await client.generate_response(
        [
            Message(role="system", content="Extract entities."),
            Message(role="user", content="Harbor runs Neo4j."),
        ],
        response_model=Entities,
        max_tokens=123,
    )

    assert out == {"extracted_entities": ["main"]}
    assert len(ai.structured_calls) == 1
    schema, prompt, kwargs = ai.structured_calls[0]
    assert schema is Entities
    assert "Harbor runs Neo4j" in prompt
    assert "JSON object" in prompt
    assert kwargs["max_tokens"] == 123


@pytest.mark.asyncio
async def test_graphiti_ai_client_parses_json_from_ask() -> None:
    ai = _FakeAIClient()
    client = GraphitiAIClient(ai_client=ai, model="openai/qwen")

    out = await client.generate_response([Message(role="user", content="Return JSON.")])

    assert out == {"ok": True, "client": "main"}
    assert len(ai.ask_calls) == 1
    prompt, kwargs = ai.ask_calls[0]
    assert "Return JSON" in prompt
    assert kwargs["max_tokens"] > 0


@pytest.mark.asyncio
async def test_graphiti_ai_client_uses_small_client_for_small_model_size() -> None:
    main = _FakeAIClient(name="main")
    small = _FakeAIClient(name="small")
    client = GraphitiAIClient(
        ai_client=main,
        small_ai_client=small,
        model="openai/qwen",
        small_model="openai/qwen-small",
    )

    out = await client.generate_response(
        [Message(role="user", content="Return JSON.")],
        model_size=ModelSize.small,
    )

    assert out == {"ok": True, "client": "small"}
    assert small.ask_calls
    assert not main.ask_calls


class _FakeEmbedding:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.batch_calls: list[list[str]] = []

    def __call__(self, text: str) -> list[float]:
        self.calls.append(text)
        return [float(len(text)), 1.0]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        self.batch_calls.append(list(texts))
        return [[float(len(text)), 1.0] for text in texts]


@pytest.mark.asyncio
async def test_graphiti_embedding_client_wraps_embedding_fn() -> None:
    embed = _FakeEmbedding()
    client = GraphitiEmbeddingClient(embed=embed, embedding_dim=1)

    one = await client.create("hello")
    many = await client.create_batch(["a", "abcd"])

    assert one == [5.0]
    assert many == [[1.0], [4.0]]
    assert embed.calls == ["hello"]
    assert embed.batch_calls == [["a", "abcd"]]


@pytest.mark.asyncio
async def test_graphiti_embedding_reranker_orders_by_cosine() -> None:
    vectors = {
        "query": [1.0, 0.0],
        "near": [1.0, 0.0],
        "far": [0.0, 1.0],
    }

    def embed(text: str) -> list[float]:
        return vectors[text]

    reranker = GraphitiEmbeddingReranker(embed=embed)

    out = await reranker.rank("query", ["far", "near"])

    assert out[0][0] == "near"
    assert out[0][1] > out[1][1]
