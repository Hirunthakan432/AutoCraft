from src.llm.provider import MockProvider, LLMProvider


def test_mock_generate():
    p = MockProvider(prefix="Hi")
    assert p.generate("world") == "Hi: world"
    assert p.calls[0]["type"] == "generate"


def test_mock_chat_uses_last_user():
    p = MockProvider()
    history = [
        {"role": "user", "content": "one"},
        {"role": "model", "content": "reply"},
        {"role": "user", "content": "two"},
    ]
    assert p.generate_chat_response(history) == "Mock response: two"


def test_mock_is_llm_provider():
    assert isinstance(MockProvider(), LLMProvider)
