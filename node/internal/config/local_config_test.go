package config

import (
	"errors"
	"os"
	"path/filepath"
	"testing"
)

func TestSaveAndLoadLocalConfig(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "config.json")
	cfg := LocalConfig{
		SchemaVersion: CurrentSchemaVersion,
		NodeID:        "node-123",
		MachineName:   "test-machine",
		Mode:          ModeLocalSelfBuild,
		RepoPath:      dir,
		StatePath:     filepath.Join(dir, "state"),
		DefaultModel:  DefaultModelPlaceholder,
	}

	if err := SaveLocalConfig(path, cfg, false); err != nil {
		t.Fatalf("SaveLocalConfig returned error: %v", err)
	}
	loaded, err := LoadLocalConfig(path)
	if err != nil {
		t.Fatalf("LoadLocalConfig returned error: %v", err)
	}
	if loaded != cfg {
		t.Fatalf("loaded config mismatch\nwant: %#v\n got: %#v", cfg, loaded)
	}
	if err := SaveLocalConfig(path, cfg, false); !errors.Is(err, ErrConfigExists) {
		t.Fatalf("expected ErrConfigExists, got %v", err)
	}
	if info, err := os.Stat(path); err != nil || info.IsDir() {
		t.Fatalf("expected config file to exist, info=%#v err=%v", info, err)
	}
}

func TestUserStateDirHonorsOverride(t *testing.T) {
	t.Setenv(EnvStateDir, filepath.Join(t.TempDir(), "state"))
	path, err := UserStateDir()
	if err != nil {
		t.Fatalf("UserStateDir returned error: %v", err)
	}
	if !filepath.IsAbs(path) {
		t.Fatalf("UserStateDir should return absolute override, got %q", path)
	}
}
