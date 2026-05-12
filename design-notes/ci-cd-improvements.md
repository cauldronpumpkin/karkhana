# CI/CD Improvements

**Source:** GPT-5.5 via codex-lb, 2026-05-05 | **3,790 tokens**

## 1. Parallel Job Execution

Split serial `lint → typecheck → test → build` into independent jobs. Lint, format, typecheck, and test start simultaneously. Build only after all pass.

```yaml
concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:     # ruff check
  format:   # ruff format --check
  typecheck: # mypy
  test:     # pytest (sharded)
  build:
    needs: [lint, format, typecheck, test]
```

## 2. Caching Strategies

- `setup-python` with `cache: pip` + `cache-dependency-path` pointing at lockfile/pyproject.toml
- `actions/cache@v4` for `.pytest_cache` (duration data)
- Pre-commit cache: `~/.cache/pre-commit` keyed on `.pre-commit-config.yaml`
- **uv cache** (if using uv): `astral-sh/setup-uv@v5` with `enable-cache: true`

## 3. Test Splitting (467 Tests)

Use `pytest-split` with `least_duration` algorithm across 4 shards:

```yaml
strategy:
  fail-fast: false
  matrix:
    group: [1, 2, 3, 4]

- run: |
    pytest \
      --splits 4 --group ${{ matrix.group }} \
      --splitting-algorithm least_duration \
      --durations=20 \
      --junitxml=reports/junit-shard-${{ matrix.group }}.xml
```

~115 tests per shard. Increase to 6 shards if still slow. Coverage: per-shard `coverage run --parallel-mode`, combine in final job.

## Full YAML

See original GPT-5.5 output for complete workflow YAML with artifact upload, coverage combination, and per-shard junit reporting.
