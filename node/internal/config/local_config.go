// Package config provides local configuration path helpers for the node runtime.
package config

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

const (
	// CurrentSchemaVersion is the schema used by the local foundation slice.
	CurrentSchemaVersion = "karkhana.local_config.v1"
	// ModeLocalSelfBuild is the local runtime/config mode. It is deliberately
	// separate from install service modes such as worker/master.
	ModeLocalSelfBuild = "local-self-build"
	// DefaultModelPlaceholder is intentionally not a real model name.
	DefaultModelPlaceholder = "__CONFIGURE_MODEL__"
)

// ErrConfigExists is returned when a config write would overwrite an existing file.
var ErrConfigExists = errors.New("karkhana config already exists")

// LocalConfig is the user-level Karkhana node identity and local state config.
type LocalConfig struct {
	SchemaVersion string `json:"schema_version"`
	NodeID        string `json:"node_id"`
	MachineName   string `json:"machine_name"`
	Mode          string `json:"mode"`
	RepoPath      string `json:"repo_path"`
	StatePath     string `json:"state_path"`
	DefaultModel  string `json:"default_model"`
}

// LoadLocalConfig reads and validates a local Karkhana config file.
func LoadLocalConfig(path string) (LocalConfig, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return LocalConfig{}, err
	}

	var cfg LocalConfig
	if err := json.Unmarshal(data, &cfg); err != nil {
		return LocalConfig{}, fmt.Errorf("parse local config %s: %w", path, err)
	}
	if err := cfg.Validate(); err != nil {
		return LocalConfig{}, err
	}
	return cfg, nil
}

// SaveLocalConfig writes a local Karkhana config file using a same-directory
// temporary file before renaming it into place.
func SaveLocalConfig(path string, cfg LocalConfig, overwrite bool) error {
	if err := cfg.Validate(); err != nil {
		return err
	}
	if !overwrite {
		if _, err := os.Stat(path); err == nil {
			return ErrConfigExists
		} else if !errors.Is(err, os.ErrNotExist) {
			return fmt.Errorf("check local config %s: %w", path, err)
		}
	}

	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return fmt.Errorf("create config directory: %w", err)
	}

	data, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal local config: %w", err)
	}
	data = append(data, '\n')

	tmp, err := os.CreateTemp(filepath.Dir(path), filepath.Base(path)+".*.tmp")
	if err != nil {
		return fmt.Errorf("create temp config file: %w", err)
	}
	tmpPath := tmp.Name()
	cleanup := true
	defer func() {
		if cleanup {
			_ = os.Remove(tmpPath)
		}
	}()

	if err := tmp.Chmod(0o600); err != nil {
		_ = tmp.Close()
		return fmt.Errorf("secure temp config file: %w", err)
	}
	if _, err := tmp.Write(data); err != nil {
		_ = tmp.Close()
		return fmt.Errorf("write temp config file: %w", err)
	}
	if err := tmp.Close(); err != nil {
		return fmt.Errorf("close temp config file: %w", err)
	}

	if overwrite {
		_ = os.Remove(path)
	}
	if err := os.Rename(tmpPath, path); err != nil {
		return fmt.Errorf("replace local config %s: %w", path, err)
	}
	cleanup = false
	return nil
}

// Validate checks that required local config fields are present and coherent.
func (cfg LocalConfig) Validate() error {
	if strings.TrimSpace(cfg.SchemaVersion) == "" {
		return fmt.Errorf("local config schema_version is required")
	}
	if cfg.SchemaVersion != CurrentSchemaVersion {
		return fmt.Errorf("unsupported local config schema_version %q", cfg.SchemaVersion)
	}
	if strings.TrimSpace(cfg.NodeID) == "" {
		return fmt.Errorf("local config node_id is required")
	}
	if strings.TrimSpace(cfg.MachineName) == "" {
		return fmt.Errorf("local config machine_name is required")
	}
	if cfg.Mode != ModeLocalSelfBuild {
		return fmt.Errorf("invalid runtime mode %q: expected %s", cfg.Mode, ModeLocalSelfBuild)
	}
	if strings.TrimSpace(cfg.RepoPath) == "" {
		return fmt.Errorf("local config repo_path is required")
	}
	if strings.TrimSpace(cfg.StatePath) == "" {
		return fmt.Errorf("local config state_path is required")
	}
	if strings.TrimSpace(cfg.DefaultModel) == "" {
		return fmt.Errorf("local config default_model is required")
	}
	return nil
}
