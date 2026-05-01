// Package config provides local configuration path helpers for the node runtime.
package config

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"
)

const appDirName = "karkhana"

const (
	// EnvConfigDir overrides the user-level config directory. It is primarily
	// intended for tests and local smoke checks.
	EnvConfigDir = "KARKHANA_CONFIG_DIR"
	// EnvStateDir overrides the user-level state directory. It is primarily
	// intended for tests and local smoke checks.
	EnvStateDir = "KARKHANA_STATE_DIR"
)

// UserConfigDir returns a deterministic user-level configuration directory.
func UserConfigDir() (string, error) {
	if override := os.Getenv(EnvConfigDir); override != "" {
		return filepath.Abs(override)
	}
	base, err := os.UserConfigDir()
	if err != nil || base == "" {
		fallback, fallbackErr := fallbackHomeDir("config")
		if fallbackErr != nil {
			if err != nil {
				return "", fmt.Errorf("resolve user config dir: %w", err)
			}
			return "", fallbackErr
		}
		base = fallback
	}
	return filepath.Join(base, appDirName), nil
}

// UserStateDir returns a deterministic user-level state directory for local
// tasks, runs, logs, artifacts, and worktrees.
func UserStateDir() (string, error) {
	if override := os.Getenv(EnvStateDir); override != "" {
		return filepath.Abs(override)
	}

	home, err := os.UserHomeDir()
	if err != nil || home == "" {
		if err != nil {
			return "", fmt.Errorf("resolve user home dir: %w", err)
		}
		return "", fmt.Errorf("resolve user home dir: empty path")
	}

	switch runtime.GOOS {
	case "windows":
		base, err := os.UserCacheDir()
		if err != nil || base == "" {
			base = filepath.Join(home, "AppData", "Local")
		}
		return filepath.Join(base, appDirName, "state"), nil
	case "darwin":
		return filepath.Join(home, "Library", "Application Support", appDirName, "state"), nil
	default:
		if xdgState := os.Getenv("XDG_STATE_HOME"); xdgState != "" {
			return filepath.Join(xdgState, appDirName), nil
		}
		return filepath.Join(home, ".local", "state", appDirName), nil
	}
}

// UserDataDir returns a deterministic user-level data directory.
func UserDataDir() (string, error) {
	base, err := os.UserCacheDir()
	if err != nil || base == "" {
		fallback, fallbackErr := fallbackHomeDir("data")
		if fallbackErr != nil {
			if err != nil {
				return "", fmt.Errorf("resolve user data dir: %w", err)
			}
			return "", fallbackErr
		}
		base = fallback
	}
	return filepath.Join(base, appDirName), nil
}

// ConfigFilePath returns the future local node config file path.
func ConfigFilePath() (string, error) {
	dir, err := UserConfigDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(dir, "config.json"), nil
}

// StateDirs returns the required local runtime subdirectories below statePath.
func StateDirs(statePath string) []string {
	return []string{
		filepath.Join(statePath, "tasks"),
		filepath.Join(statePath, "runs"),
		filepath.Join(statePath, "logs"),
		filepath.Join(statePath, "artifacts"),
		filepath.Join(statePath, "worktrees"),
	}
}

// TaskDir returns the local self-build task directory below statePath.
func TaskDir(statePath string) string {
	return filepath.Join(statePath, "tasks")
}

// RunDir returns the local run directory below statePath.
func RunDir(statePath string) string {
	return filepath.Join(statePath, "runs")
}

func fallbackHomeDir(kind string) (string, error) {
	home, err := os.UserHomeDir()
	if err != nil || home == "" {
		if err != nil {
			return "", fmt.Errorf("resolve user home dir: %w", err)
		}
		return "", fmt.Errorf("resolve user home dir: empty path")
	}

	switch runtime.GOOS {
	case "windows":
		if kind == "data" {
			return filepath.Join(home, "AppData", "Local"), nil
		}
		return filepath.Join(home, "AppData", "Roaming"), nil
	case "darwin":
		if kind == "data" {
			return filepath.Join(home, "Library", "Caches"), nil
		}
		return filepath.Join(home, "Library", "Application Support"), nil
	default:
		if kind == "data" {
			return filepath.Join(home, ".local", "share"), nil
		}
		return filepath.Join(home, ".config"), nil
	}
}
