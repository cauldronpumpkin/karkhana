"""Unit tests for token unit conversion."""

from src.llm.context_units import tk_to_tokens, tokens_to_tk


def test_tk_to_tokens() -> None:
    assert tk_to_tokens(1) == 1000
    assert tk_to_tokens(128) == 128000


def test_tokens_to_tk() -> None:
    assert tokens_to_tk(1000) == 1.0
    assert tokens_to_tk(64000) == 64.0
