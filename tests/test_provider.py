from unittest.mock import MagicMock, patch

import pytest

from src.llm.provider import (
    LLMProvider,
    MockProvider,
    OpenAIProvider,
    LocalProvider,
    create_provider,
    _history_to_openai_messages,
)


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


def test_history_maps_model_to_assistant():
    msgs = _history_to_openai_messages(
        [{"role": "user", "content": "hi"}, {"role": "model", "content": "yo"}],
        system_instruction="be brief",
    )
    assert msgs[0] == {"role": "system", "content": "be brief"}
    assert msgs[2]["role"] == "assistant"


def test_create_provider_mock():
    assert isinstance(create_provider("mock"), MockProvider)


def test_create_provider_unknown():
    with pytest.raises(ValueError, match="Unknown provider"):
        create_provider("nope")


def test_openai_model_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    p = OpenAIProvider()
    assert p.model == "gpt-4o"


def test_openai_model_arg_overrides_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    p = OpenAIProvider(model="gpt-4o-mini")
    assert p.model == "gpt-4o-mini"


@patch("src.llm.provider.requests.post")
def test_openai_provider_chat(mock_post):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "hello from openai"}}]
    }
    mock_post.return_value = mock_resp

    p = OpenAIProvider(api_key="sk-test", model="gpt-4o-mini")
    out = p.generate_chat_response(
        [{"role": "user", "content": "hi"}],
        system_instruction="sys",
    )
    assert out == "hello from openai"
    assert mock_post.called
    body = mock_post.call_args.kwargs["json"]
    assert body["model"] == "gpt-4o-mini"
    assert body["messages"][0]["role"] == "system"


@patch("src.llm.provider.requests.post")
def test_local_provider_chat(mock_post):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "hello from local"}}]
    }
    mock_post.return_value = mock_resp

    p = LocalProvider(base_url="http://127.0.0.1:11434/v1", model="llama3.2")
    assert p.generate("ping") == "hello from local"
    url = mock_post.call_args.args[0]
    assert url.endswith("/chat/completions")
