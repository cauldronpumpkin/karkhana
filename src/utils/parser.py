"""JSON extraction utilities."""

import json
import re


def extract_json(text: str) -> dict | None:
    """Extract JSON from text that may contain markdown or other formatting."""
    # Try to find JSON in backticks first (markdown code blocks)
    json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', text, re.DOTALL | re.IGNORECASE)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find JSON object in plain text
    json_match = re.search(r'({[^{}]*})', text)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try parsing entire text as JSON
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return None


def extract_code_block(text: str) -> str:
    """Extract code from markdown code blocks."""
    code_match = re.search(r'```(?:\w+)?\s*(.*?)```', text, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()
    return text.strip()


def parse_list(text: str) -> list[str]:
    """Parse bullet points or numbered lists."""
    items = []
    for line in text.split('\n'):
        # Match bullet points
        match = re.match(r'^[-*•]\s+(.+)$', line)
        if match:
            items.append(match.group(1).strip())
        # Match numbered lists
        match = re.match(r'^\d+\.\s+(.+)$', line)
        if match:
            items.append(match.group(1).strip())
    return items
