# Karkhana CLI launcher

This package is the initial npm launcher shim for the Karkhana local node runtime.

The long-running runtime is intended to be a Go daemon. This package only exposes a `karkhana` command and delegates to the Go implementation when available.

## Development usage

From this directory:

```powershell
npm install
node ./bin/karkhana.js version
node ./bin/karkhana.js init
node ./bin/karkhana.js doctor
node ./bin/karkhana.js status
node ./bin/karkhana.js self-build sample-task
```

If a built Go binary is not present, the shim attempts to run the development Go entrypoint in `../node` with `go run`.

For local smoke checks without writing to your real user config/state paths, set `KARKHANA_CONFIG_DIR` and `KARKHANA_STATE_DIR` before running `init` or `self-build sample-task`.

To build a local binary for the shim:

```powershell
cd ../node
go build -o ./bin/karkhana.exe ./cmd/karkhana
```

On macOS/Linux, build `./bin/karkhana` instead.

## Current limitations

- No binary download/install flow yet.
- No daemon service installation yet.
- No real auth yet.
- No real OpenCode job execution yet.
- No real master lease yet.
