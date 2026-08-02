def test_autocraft_imports():
    from src.core.llm import GeminiClient

    assert GeminiClient is not None
