# Karigar MVP

Karigar is a local, structured agent runner for the Idea Refinery workspace.
It takes a job contract, runs the mock engine, and writes predictable artifacts to disk.

## Run a mock job

```bash
python -m workers.karigar --job-json examples/mock-job.json
```

Optional:

```bash
python -m workers.karigar --workspace . --job-json examples/mock-job.json
```

## Job contract

Karigar normalizes job input into a `JobContract`.

Required fields:

- `job_id`: unique job identifier
- `repo_root`: repository root path
- `command`: primary command to run

Supported fields:

- `worktree_path`: working tree path; defaults to `repo_root`
- `args`: extra command arguments
- `env`: environment variables
- `allow_network`: whether network access is permitted
- `allow_git_write`: whether git write actions are permitted
- `job_type`: job classification; defaults to `mock`
- `payload`: arbitrary job metadata

## Result artifacts

Each job writes artifacts under:

```text
artifacts/<job_id>/
```

Files:

- `job.json` — normalized job contract
- `result.json` — structured job result
- `logs.txt` — compact run log
- `diff.patch` — mock diff artifact when a repo is present

## Safety model

This MVP uses the mock engine only.

- commands are checked against the safe command policy
- unsafe or missing commands are blocked
- no code modification is performed
- git output is simulated as artifact data, not applied to the repo

## Deferred for later

Intentionally not included yet:

- real engine adapters
- backend integration
- UI surfaces
- persistent job orchestration
- real patch application / repository mutation
