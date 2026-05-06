# Codex Engine for Karigar

**Source:** GPT-5.5 via codex-lb, 2026-05-05 | **3,748 tokens**

## Integration

Add `CodexEngine` alongside `OpenCodeEngine` and `HermesAgentEngine` in `workers/karigar/karigar/engines.py`.

## Binary Resolution

Priority order:
1. Constructor `codex_bin=` argument
2. `KARIGAR_CODEX_BIN` env var
3. `CODEX_BIN` env var
4. `codex` on PATH

Falls back with clear error message if not found.

## Engine Class

```python
class CodexEngine:
    name = "codex"
    
    def __init__(self, model=None, codex_bin=None, sandbox=None, 
                 approval_policy=None, extra_args=None, **kwargs):
        ...
    
    def run(self, prompt, cwd=".") -> str:
        # codex exec --cd $cwd --sandbox $mode --approval-policy never $prompt
```

Uses `codex exec` with `--skip-git-repo-check`, configurable sandbox mode (default: `workspace-write`), and approval policy (default: `never`).

## Registration

```python
register_engine(name="codex", engine_cls=CodexEngine,
                description="OpenAI Codex CLI engine using `codex exec`.")
```

## CLI

```bash
karigar --engine codex ...
CODEX_MODEL=gpt-5-codex karigar --engine codex ...
KARIGAR_CODEX_BIN=/usr/local/bin/codex karigar --engine codex ...
```

Add `"codex"` to argparse `choices` list. Expose `--codex-bin`, `--codex-sandbox`, `--codex-approval-policy` flags.

## Full Code

See original GPT-5.5 output for complete Python implementation with `_resolve_codex_binary()`, `_build_command()`, and `run()`.
