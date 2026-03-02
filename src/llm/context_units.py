"""Token unit conversion helpers."""


def tk_to_tokens(tk: int) -> int:
    """Convert thousand-token units to token count."""
    return int(tk) * 1000


def tokens_to_tk(tokens: int) -> float:
    """Convert token count to thousand-token units."""
    return float(tokens) / 1000.0
