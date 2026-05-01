package setup

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/idearefinery/karkhana-node/internal/config"
)

func TestRunInitializesLocalConfigAndState(t *testing.T) {
	dir := t.TempDir()
	configPath := filepath.Join(dir, "config", "config.json")
	statePath := filepath.Join(dir, "state")

	result, err := Run(Options{
		ConfigPath:  configPath,
		RepoPath:    dir,
		StatePath:   statePath,
		MachineName: "test-machine",
	})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}
	if result.Config.Mode != config.ModeLocalSelfBuild {
		t.Fatalf("unexpected mode: %q", result.Config.Mode)
	}
	if result.Config.MachineName != "test-machine" {
		t.Fatalf("unexpected machine name: %q", result.Config.MachineName)
	}
	if result.Config.NodeID == "" {
		t.Fatal("expected node id")
	}
	for _, path := range append([]string{statePath}, config.StateDirs(statePath)...) {
		info, err := os.Stat(path)
		if err != nil {
			t.Fatalf("expected state path %s: %v", path, err)
		}
		if !info.IsDir() {
			t.Fatalf("expected directory: %s", path)
		}
	}

	second, err := Run(Options{ConfigPath: configPath})
	if err != nil {
		t.Fatalf("second Run returned error: %v", err)
	}
	if !second.AlreadyInitialized {
		t.Fatal("expected second run to report AlreadyInitialized")
	}
	if second.Config.NodeID != result.Config.NodeID {
		t.Fatalf("expected existing node id to be preserved")
	}
}
