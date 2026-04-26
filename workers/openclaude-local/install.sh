#!/usr/bin/env bash
set -euo pipefail

# ── IdeaRefinery / Karkhana — Local Worker Installer ──────────────────────────
# One-click macOS/Linux installer for the OpenClaude local worker.
# Usage:
#   ./install.sh https://api.example.com
#   ./install.sh --api-base https://api.example.com --tenant-id tenant-123
#   ./install.sh --api-base https://api.example.com --display-name "My Mac" --no-launchd
# ──────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE="${IDEAREFINERY_WORKER_STATE:-$HOME/.idearefinery-worker/openclaude-local/state.json}"
PLIST_LABEL="com.idearefinery.local-worker"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"
LOG_PATH="$HOME/Library/Logs/${PLIST_LABEL}.log"

# ── Colours & helpers ─────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}ℹ  $*${NC}"; }
ok()      { echo -e "${GREEN}✅ $*${NC}"; }
warn()    { echo -e "${YELLOW}⚠️  $*${NC}"; }
err()     { echo -e "${RED}❌ $*${NC}" >&2; }
die()     { err "$*"; exit 1; }

# ── Argument parsing ──────────────────────────────────────────────────────────
API_BASE=""
TENANT_ID=""
DISPLAY_NAME=""
NO_LAUNCHD=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-base)
      API_BASE="$2"; shift 2 ;;
    --tenant-id)
      TENANT_ID="$2"; shift 2 ;;
    --display-name)
      DISPLAY_NAME="$2"; shift 2 ;;
    --no-launchd)
      NO_LAUNCHD=true; shift ;;
    -h|--help)
      echo "Usage: $0 [API_BASE_URL] [OPTIONS]"
      echo ""
      echo "Arguments:"
      echo "  API_BASE_URL          IdeaRefinery API base URL (positional or --api-base)"
      echo ""
      echo "Options:"
      echo "  --api-base URL        API base URL (alternative to positional)"
      echo "  --tenant-id ID        Tenant ID for multi-tenant setups"
      echo "  --display-name NAME   Friendly name shown in the Local Workers UI"
      echo "  --no-launchd          Skip creating a launchd/systemd auto-start service"
      echo "  -h, --help            Show this help message"
      exit 0
      ;;
    -*)
      die "Unknown option: $1 (use --help for usage)"
      ;;
    *)
      # Positional: treat as API_BASE if not yet set
      if [[ -z "$API_BASE" ]]; then
        API_BASE="$1"; shift
      else
        die "Unexpected argument: $1 (use --help for usage)"
      fi
      ;;
  esac
done

# ── Validate required args ────────────────────────────────────────────────────
if [[ -z "$API_BASE" ]]; then
  die "API base URL is required. Provide as positional arg or --api-base URL"
fi

# Strip trailing slash for consistency
API_BASE="${API_BASE%/}"

# ── Detect OS ─────────────────────────────────────────────────────────────────
OS="$(uname -s)"
case "$OS" in
  Darwin*)  OS_NAME="macos" ;;
  Linux*)   OS_NAME="linux" ;;
  *)        OS_NAME="unknown" ;;
esac

info "Detected OS: $OS_NAME"
info "API base: $API_BASE"
[[ -n "$TENANT_ID" ]]    && info "Tenant ID: $TENANT_ID"
[[ -n "$DISPLAY_NAME" ]] && info "Display name: $DISPLAY_NAME"
$NO_LAUNCHD              && info "Auto-start: disabled (--no-launchd)"

# ── Python 3.10+ check & install ─────────────────────────────────────────────
ensure_python() {
  if command -v python3 &>/dev/null; then
    local version
    version="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    local major minor
    major="$(echo "$version" | cut -d. -f1)"
    minor="$(echo "$version" | cut -d. -f2)"
    if (( major >= 3 && minor >= 10 )); then
      ok "Python $version found"
      return 0
    fi
    warn "Python $version is too old (need 3.10+)"
  else
    warn "python3 not found on PATH"
  fi

  # Try Homebrew
  if command -v brew &>/dev/null; then
    info "Installing Python 3.12 via Homebrew..."
    brew install python@3.12 || brew install python@3.11 || brew install python
    if command -v python3 &>/dev/null; then
      ok "Python installed via Homebrew"
      return 0
    fi
  else
    warn "Homebrew not found"
  fi

  # Try Xcode CLI tools (macOS)
  if [[ "$OS_NAME" == "macos" ]]; then
    info "Attempting to install Xcode Command Line Tools..."
    xcode-select --install 2>/dev/null || true
    if command -v python3 &>/dev/null; then
      ok "Python installed via Xcode CLI tools"
      return 0
    fi
  fi

  die "Could not install Python 3.10+. Please install Python manually and re-run this script."
}

ensure_python

# ── Install pip dependencies ──────────────────────────────────────────────────
install_deps() {
  local req_file="$SCRIPT_DIR/requirements.txt"
  if [[ ! -f "$req_file" ]]; then
    die "requirements.txt not found at $req_file"
  fi

  info "Installing Python dependencies..."
  python3 -m pip install --quiet --upgrade pip 2>/dev/null || true
  python3 -m pip install -r "$req_file"
  ok "Dependencies installed"
}

install_deps

# ── Write display-name to worker config (if provided) ─────────────────────────
write_display_name() {
  if [[ -z "$DISPLAY_NAME" ]]; then
    return 0
  fi

  local config_file="$SCRIPT_DIR/worker-config.json"
  local tmp_file="${config_file}.tmp"

  if [[ -f "$config_file" ]]; then
    # Merge display_name into existing config using python3
    python3 -c "
import json, sys
path = sys.argv[1]
name = sys.argv[2]
with open(path, 'r') as f:
    data = json.load(f)
data['display_name'] = name
with open(path, 'w') as f:
    json.dump(data, f, indent=2)
" "$config_file" "$DISPLAY_NAME"
  else
    # Create minimal config
    python3 -c "
import json, sys
data = {'display_name': sys.argv[1]}
with open(sys.argv[2], 'w') as f:
    json.dump(data, f, indent=2)
" "$DISPLAY_NAME" "$config_file"
  fi

  ok "Display name set: $DISPLAY_NAME"
}

write_display_name

# ── Pairing flow (blocking — polls until admin approves) ──────────────────────
run_pair() {
  info "Starting pairing flow..."
  info "Open the IdeaRefinery web UI and approve this worker when prompted."

  local pair_cmd=(python3 "$SCRIPT_DIR/worker.py" pair --api-base "$API_BASE" --state "$STATE")
  [[ -n "$TENANT_ID" ]] && pair_cmd+=(--tenant-id "$TENANT_ID")

  "${pair_cmd[@]}"
  ok "Worker paired successfully — state saved to $STATE"
}

run_pair

# ── Auto-start service ────────────────────────────────────────────────────────
setup_autostart() {
  if $NO_LAUNCHD; then
    info "Skipping auto-start setup (--no-launchd)"
    return 0
  fi

  if [[ "$OS_NAME" == "macos" ]]; then
    setup_launchd
  elif [[ "$OS_NAME" == "linux" ]]; then
    setup_systemd
  else
    warn "Unsupported OS for auto-start ($OS_NAME). Run manually:"
    echo "   python3 $SCRIPT_DIR/worker.py run --state $STATE"
  fi
}

setup_launchd() {
  info "Creating launchd service..."

  # Resolve absolute path for the worker script
  local worker_abs
  worker_abs="$(cd "$SCRIPT_DIR" && pwd)/worker.py"
  local state_abs
  state_abs="$(mkdir -p "$(dirname "$STATE")" && cd "$(dirname "$STATE")" && pwd)/$(basename "$STATE")"
  local python_abs
  python_abs="$(command -v python3)"

  mkdir -p "$HOME/Library/LaunchAgents"

  cat > "$PLIST_PATH" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${python_abs}</string>
        <string>${worker_abs}</string>
        <string>run</string>
        <string>--state</string>
        <string>${state_abs}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${LOG_PATH}</string>
    <key>StandardErrorPath</key>
    <string>${LOG_PATH}</string>
</dict>
</plist>
PLIST_EOF

  # Unload existing service if present (allows re-install)
  launchctl unload "$PLIST_PATH" 2>/dev/null || true

  launchctl load "$PLIST_PATH"
  ok "launchd service loaded — worker will auto-start on boot"
  info "Logs: $LOG_PATH"
  info "To stop:  launchctl unload $PLIST_PATH"
  info "To remove: rm $PLIST_PATH"
}

setup_systemd() {
  info "Creating systemd user service..."

  local worker_abs
  worker_abs="$(cd "$SCRIPT_DIR" && pwd)/worker.py"
  local state_abs
  state_abs="$(mkdir -p "$(dirname "$STATE")" && cd "$(dirname "$STATE")" && pwd)/$(basename "$STATE")"
  local python_abs
  python_abs="$(command -v python3)"

  local service_dir="$HOME/.config/systemd/user"
  local service_file="$service_dir/idearefinery-local-worker.service"

  mkdir -p "$service_dir"

  cat > "$service_file" <<SYSTEMD_EOF
[Unit]
Description=IdeaRefinery Local Worker
After=network-online.target

[Service]
Type=simple
ExecStart=${python_abs} ${worker_abs} run --state ${state_abs}
Restart=always
RestartSec=10
StandardOutput=append:${HOME}/.local/share/idearefinery-worker.log
StandardError=append:${HOME}/.local/share/idearefinery-worker.log

[Install]
WantedBy=default.target
SYSTEMD_EOF

  # Try to enable and start (may fail if systemd user session isn't running)
  if command -v systemctl &>/dev/null; then
    systemctl --user daemon-reload 2>/dev/null || true
    systemctl --user enable idearefinery-local-worker.service 2>/dev/null || true
    systemctl --user restart idearefinery-local-worker.service 2>/dev/null || true
    ok "systemd user service created and enabled"
  else
    ok "systemd service file written to $service_file"
  fi

  info "To start:  systemctl --user start idearefinery-local-worker.service"
  info "To stop:   systemctl --user stop idearefinery-local-worker.service"
  info "Logs:      journalctl --user -u idearefinery-local-worker -f"
}

setup_autostart

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
ok "IdeaRefinery local worker installed and running!"
echo ""
echo "  State file : $STATE"
echo "  Worker dir : $SCRIPT_DIR"
echo ""
echo "Manual commands:"
echo "  Run once : python3 $SCRIPT_DIR/worker.py once --state $STATE"
echo "  Run loop : python3 $SCRIPT_DIR/worker.py run  --state $STATE"
echo "  Re-pair  : python3 $SCRIPT_DIR/worker.py pair --api-base $API_BASE --state $STATE"
