from coactra.ai import ApproximateTokenCounter, TokenCounter, count_tokens


def test_dependency_light_token_counter_is_injectable():
    counter = ApproximateTokenCounter()
    assert isinstance(counter, TokenCounter)
    assert count_tokens("") == 0
    assert count_tokens("12345", counter=counter) == 2


def test_count_tokens_uses_injected_model_aware_counter():
    class Counter:
        def count(self, text, *, model=None):
            return len(text) + (1 if model == "special" else 0)

    assert count_tokens("abc", model="special", counter=Counter()) == 4
