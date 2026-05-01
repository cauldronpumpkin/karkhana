#!/usr/bin/env node
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

function repoRoot() {
  return path.resolve(__dirname, '..', '..');
}

function binaryName() {
  return process.platform === 'win32' ? 'karkhana.exe' : 'karkhana';
}

function candidateBinaries() {
  const root = repoRoot();
  const fromEnv = process.env.KARKHANA_GO_BINARY ? [process.env.KARKHANA_GO_BINARY] : [];
  return [
    ...fromEnv,
    path.join(root, 'node', 'bin', binaryName()),
    path.join(root, 'node', binaryName()),
    path.join(root, 'node', 'cmd', 'karkhana', binaryName())
  ];
}

function run(command, args, options = {}) {
  return spawnSync(command, args, {
    stdio: 'inherit',
    shell: false,
    ...options
  });
}

function main() {
  const args = process.argv.slice(2);
  for (const candidate of candidateBinaries()) {
    if (candidate && fs.existsSync(candidate)) {
      const result = run(candidate, args);
      process.exit(result.status ?? 1);
    }
  }

  const root = repoRoot();
  const goEntry = path.join(root, 'node', 'cmd', 'karkhana');
  if (fs.existsSync(goEntry)) {
    const result = run('go', ['run', './cmd/karkhana', ...args], {
      cwd: path.join(root, 'node')
    });
    if (result.error && result.error.code === 'ENOENT') {
      printMissingBinaryHelp(root);
      process.exit(1);
    }
    process.exit(result.status ?? 1);
  }

  printMissingBinaryHelp(root);
  process.exit(1);
}

function printMissingBinaryHelp(root) {
  console.error('Karkhana Go binary is not built yet.');
  console.error('This npm package is currently only a launcher shim.');
  console.error('');
  console.error('From the repository root, run:');
  console.error('  cd node');
  console.error('  go run ./cmd/karkhana version');
  console.error('');
  console.error('Or build a local binary for the shim:');
  console.error('  cd node');
  console.error(`  go build -o ./bin/${binaryName()} ./cmd/karkhana`);
  console.error('');
  console.error(`Repository root detected as: ${root}`);
}

main();
