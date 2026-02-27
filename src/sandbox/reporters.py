"""Error parsers for different languages."""

import re
from pathlib import Path


class ErrorParser:
    """Parse error tracebacks from different language runtimes."""

    @staticmethod
    def parse_python_error(stderr: str) -> dict:
        """Parse Python traceback."""
        result = {
            "error_type": "runtime",
            "message": "",
            "line_number": None,
            "column": None,
            "traceback_snippet": stderr[:500]
        }

        # Match patterns like "File \"app/main.py\", line 10, in <module>"
        file_match = re.search(r'File\s+"([^"]+)",\s*line\s+(\d+)', stderr)
        if file_match:
            result["file_path"] = file_match.group(1)
            result["line_number"] = int(file_match.group(2))
        
        # Extract error type and message
        error_line_match = re.search(r'(\w+Error):\s*(.+)$', stderr, re.MULTILINE)
        if error_line_match:
            result["error_type"] = error_line_match.group(1).lower()
            result["message"] = error_line_match.group(2).strip()
        else:
            # Try generic error
            generic_match = re.search(r'Error:\s*(.+)$', stderr, re.MULTILINE)
            if generic_match:
                result["message"] = generic_match.group(1).strip()

        return result

    @staticmethod
    def parse_javascript_error(stderr: str) -> dict:
        """Parse JavaScript/TypeScript error."""
        result = {
            "error_type": "runtime",
            "message": "",
            "line_number": None,
            "column": None,
            "traceback_snippet": stderr[:500]
        }

        # Match patterns like "    at main (app/page.ts:10:5)"
        stack_match = re.search(r'at\s+(\w+)\s+\(([^:]+):(\d+):(\d+)\)', stderr)
        if stack_match:
            result["function_name"] = stack_match.group(1)
            result["file_path"] = stack_match.group(2)
            result["line_number"] = int(stack_match.group(3))
            result["column"] = int(stack_match.group(4))

        # Extract error message
        message_match = re.search(r'^(\w+Error|TypeError):\s*(.+)$', stderr, re.MULTILINE)
        if message_match:
            result["error_type"] = message_match.group(1).lower()
            result["message"] = message_match.group(2).strip()

        return result

    @staticmethod
    def parse_lint_error(stderr: str) -> dict:
        """Parse linter output (ruff/eslint)."""
        result = {
            "error_type": "lint",
            "message": "",
            "line_number": None,
            "column": None,
            "traceback_snippet": stderr[:500]
        }

        # Ruff pattern: path/to/file.py:10:5: error[CODE] message
        ruff_match = re.search(r'(.+\.py):(\d+):(\d+):\s*(.+)$', stderr)
        if ruff_match:
            result["file_path"] = ruff_match.group(1)
            result["line_number"] = int(ruff_match.group(2))
            result["column"] = int(ruff_match.group(3))
            result["message"] = ruff_match.group(4).strip()

        # ESLint pattern: path/to/file.ts:10:5 - message
        eslint_match = re.search(r'(.+\.tsx?|.+\.js):(\d+):(\d+)\s+-\s+(.+)$', stderr)
        if eslint_match:
            result["file_path"] = eslint_match.group(1)
            result["line_number"] = int(eslint_match.group(2))
            result["column"] = int(eslint_match.group(3))
            result["message"] = eslint_match.group(4).strip()

        return result

    @classmethod
    def parse(cls, stderr: str, language: str) -> dict:
        """Parse error based on language."""
        if language == "python":
            return cls.parse_python_error(stderr)
        elif language in ("javascript", "typescript"):
            return cls.parse_javascript_error(stderr)
        else:
            # Fallback to generic parsing
            result = {
                "error_type": "runtime",
                "message": stderr[:500],
                "traceback_snippet": stderr[:500]
            }
            return result
