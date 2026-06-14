from unittest.mock import patch

from coactra.ai.embedding import LiteLLMEmbedding, cosine


def test_cosine_identical_is_one():
    assert abs(cosine([1.0, 0.0], [1.0, 0.0]) - 1.0) < 1e-9


def test_cosine_orthogonal_is_zero():
    assert abs(cosine([1.0, 0.0], [0.0, 1.0])) < 1e-9


def test_cosine_zero_vector_is_safe():
    assert cosine([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_default_embedding_uses_litellm():
    fake = {"data": [{"embedding": [0.1, 0.2, 0.3]}]}
    with patch("coactra.ai.completion.embedding._litellm_embedding", return_value=fake) as m:
        embed = LiteLLMEmbedding(model="text-embedding-3-small")
        out = embed("hello")
    assert out == [0.1, 0.2, 0.3]
    m.assert_called_once_with(model="text-embedding-3-small", input=["hello"])


def test_embedding_binds_provider_defaults_and_batches():
    fake = {
        "data": [
            {"embedding": [0.1, 0.2]},
            {"embedding": [0.3, 0.4]},
        ]
    }
    with patch("coactra.ai.completion.embedding._litellm_embedding", return_value=fake) as m:
        embed = LiteLLMEmbedding(
            model="openai/text-embedding-3-small",
            api_base="https://embed.example/v1",
            api_key="sk-test",
            dimensions=2,
        )
        out = embed.embed_many(["hello", "world"])
    assert out == [[0.1, 0.2], [0.3, 0.4]]
    m.assert_called_once_with(
        model="openai/text-embedding-3-small",
        input=["hello", "world"],
        api_base="https://embed.example/v1",
        api_key="sk-test",
        dimensions=2,
    )
