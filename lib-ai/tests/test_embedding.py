from unittest.mock import patch

from fleetlib.ai.embedding import cosine, LiteLLMEmbedding


def test_cosine_identical_is_one():
    assert abs(cosine([1.0, 0.0], [1.0, 0.0]) - 1.0) < 1e-9


def test_cosine_orthogonal_is_zero():
    assert abs(cosine([1.0, 0.0], [0.0, 1.0])) < 1e-9


def test_cosine_zero_vector_is_safe():
    assert cosine([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_default_embedding_uses_litellm():
    fake = {"data": [{"embedding": [0.1, 0.2, 0.3]}]}
    with patch("fleetlib.ai.embedding.litellm.embedding", return_value=fake) as m:
        embed = LiteLLMEmbedding(model="text-embedding-3-small")
        out = embed("hello")
    assert out == [0.1, 0.2, 0.3]
    m.assert_called_once()
