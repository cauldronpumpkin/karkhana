package status

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/idearefinery/karkhana-node/internal/config"
)

func TestRunReportsUninitialized(t *testing.T) {
	result := Run(Options{ConfigPath: filepath.Join(t.TempDir(), "missing.json")})
	if result.Initialized {
		t.Fatal("expected uninitialized status")
	}
	if len(result.Warnings) == 0 {
		t.Fatal("expected warning for missing config")
	}
}

func TestRunReportsInitializedState(t *testing.T) {
	dir := t.TempDir()
	statePath := filepath.Join(dir, "state")
	for _, path := range config.StateDirs(statePath) {
		if err := os.MkdirAll(path, 0o700); err != nil {
			t.Fatalf("create state dir: %v", err)
		}
	}
	if err := os.WriteFile(filepath.Join(config.TaskDir(statePath), "task.json"), []byte("{}"), 0o600); err != nil {
		t.Fatalf("write task: %v", err)
	}
	cfg := config.LocalConfig{
		SchemaVersion: config.CurrentSchemaVersion,
		NodeID:        "node-123",
		MachineName:   "test-machine",
		Mode:          config.ModeLocalSelfBuild,
		RepoPath:      dir,
		StatePath:     statePath,
		DefaultModel:  config.DefaultModelPlaceholder,
	}
	configPath := filepath.Join(dir, "config.json")
	if err := config.SaveLocalConfig(configPath, cfg, false); err != nil {
		t.Fatalf("save config: %v", err)
	}

	result := Run(Options{ConfigPath: configPath})
	if !result.Initialized {
		t.Fatal("expected initialized status")
	}
	if result.TaskCount != 1 {
		t.Fatalf("expected task count 1, got %d", result.TaskCount)
	}
	for _, dir := range result.StateDirs {
		if !dir.Ready {
			t.Fatalf("expected ready dir: %#v", dir)
		}
	}
}
