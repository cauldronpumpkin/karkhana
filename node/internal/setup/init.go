// Package setup initializes local Karkhana node configuration and state.
package setup

import (
	"crypto/rand"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/idearefinery/karkhana-node/internal/config"
)

// Options controls local initialization.
type Options struct {
	ConfigPath  string
	RepoPath    string
	StatePath   string
	MachineName string
	Force       bool
}

// Result describes the initialized local config and state layout.
type Result struct {
	Config             config.LocalConfig
	ConfigPath         string
	CreatedDirs        []string
	AlreadyInitialized bool
}

// Run initializes user-level Karkhana local state.
func Run(opts Options) (Result, error) {
	configPath := strings.TrimSpace(opts.ConfigPath)
	if configPath == "" {
		path, err := config.ConfigFilePath()
		if err != nil {
			return Result{}, err
		}
		configPath = path
	}

	if !opts.Force {
		if existing, err := config.LoadLocalConfig(configPath); err == nil {
			created, ensureErr := ensureStateDirs(existing.StatePath)
			return Result{Config: existing, ConfigPath: configPath, CreatedDirs: created, AlreadyInitialized: true}, ensureErr
		} else if !os.IsNotExist(err) {
			return Result{}, err
		}
	}

	repoPath, err := resolvePath(opts.RepoPath, os.Getwd)
	if err != nil {
		return Result{}, fmt.Errorf("resolve repo path: %w", err)
	}
	statePath := strings.TrimSpace(opts.StatePath)
	if statePath == "" {
		statePath, err = config.UserStateDir()
		if err != nil {
			return Result{}, err
		}
	} else {
		statePath, err = filepath.Abs(statePath)
		if err != nil {
			return Result{}, fmt.Errorf("resolve state path: %w", err)
		}
	}
	machineName := strings.TrimSpace(opts.MachineName)
	if machineName == "" {
		machineName, err = os.Hostname()
		if err != nil || strings.TrimSpace(machineName) == "" {
			machineName = "unknown-machine"
		}
	}
	nodeID, err := newNodeID()
	if err != nil {
		return Result{}, err
	}
	cfg := config.LocalConfig{
		SchemaVersion: config.CurrentSchemaVersion,
		NodeID:        nodeID,
		MachineName:   machineName,
		Mode:          config.ModeLocalSelfBuild,
		RepoPath:      repoPath,
		StatePath:     statePath,
		DefaultModel:  config.DefaultModelPlaceholder,
	}
	created, err := ensureStateDirs(statePath)
	if err != nil {
		return Result{}, err
	}
	if err := config.SaveLocalConfig(configPath, cfg, opts.Force); err != nil {
		return Result{}, err
	}
	return Result{Config: cfg, ConfigPath: configPath, CreatedDirs: created}, nil
}

func ensureStateDirs(statePath string) ([]string, error) {
	dirs := append([]string{statePath}, config.StateDirs(statePath)...)
	created := make([]string, 0, len(dirs))
	for _, dir := range dirs {
		if _, err := os.Stat(dir); os.IsNotExist(err) {
			created = append(created, dir)
		} else if err != nil {
			return created, fmt.Errorf("inspect state directory %s: %w", dir, err)
		}
		if err := os.MkdirAll(dir, 0o700); err != nil {
			return created, fmt.Errorf("create state directory %s: %w", dir, err)
		}
	}
	return created, nil
}

func resolvePath(value string, fallback func() (string, error)) (string, error) {
	path := strings.TrimSpace(value)
	if path == "" {
		var err error
		path, err = fallback()
		if err != nil {
			return "", err
		}
	}
	return filepath.Abs(path)
}

func newNodeID() (string, error) {
	var b [16]byte
	if _, err := rand.Read(b[:]); err != nil {
		return "", fmt.Errorf("generate node_id: %w", err)
	}
	b[6] = (b[6] & 0x0f) | 0x40
	b[8] = (b[8] & 0x3f) | 0x80
	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16]), nil
}
