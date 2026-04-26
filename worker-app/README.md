# IdeaRefinery Worker Desktop App

A standalone Tauri v2 desktop application that serves as the IdeaRefinery local worker.

## Prerequisites

- Rust 1.70+
- Node.js 18+

## Development

```bash
cd worker-app
npm install
cd src-tauri
cargo build
```

## Build

### Windows (.exe/.msi)

```bash
cd worker-app
cargo tauri build --target x86_64-pc-windows-msvc
```

Output: `src-tauri/target/release/bundle/msi/*.msi` and `src-tauri/target/release/bundle/nsis/*.exe`

### macOS (.dmg)

Requires a macOS machine. Cannot be cross-compiled from Windows.

```bash
cd worker-app
cargo tauri build --target aarch64-apple-darwin
```

Output: `src-tauri/target/release/bundle/dmg/*.dmg`

### Code Signing (macOS distribution)

```bash
codesign --sign "Developer ID Application: ..." target/release/bundle/macos/*.app
xcrun notarytool submit target/release/bundle/dmg/*.dmg --wait
```

## Project Structure

- `src-tauri/src/` — Rust backend (HTTP client, SQS, git ops, worker logic)
- `src/` — Svelte 5 frontend (dashboard, pairing, config editor)
- `src-tauri/icons/` — App icons
- `src-tauri/capabilities/` — Tauri permission capabilities
