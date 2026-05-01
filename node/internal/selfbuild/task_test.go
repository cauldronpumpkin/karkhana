package selfbuild

import (
	"strings"
	"testing"

	"github.com/idearefinery/karkhana-node/internal/config"
)

func TestGenerateSampleTaskIncludesBranchesAndLocalConfig(t *testing.T) {
	cfg := config.LocalConfig{
		SchemaVersion: config.CurrentSchemaVersion,
		NodeID:        "node-123",
		MachineName:   "test-machine",
		Mode:          config.ModeLocalSelfBuild,
		RepoPath:      "C:/repo",
		StatePath:     "C:/state",
		DefaultModel:  config.DefaultModelPlaceholder,
	}
	task := GenerateSampleTask(cfg)
	if task.RepoPath != cfg.RepoPath {
		t.Fatalf("repo path mismatch: %q", task.RepoPath)
	}
	if task.BaseBranch == "" || task.WorkBranch == "" {
		t.Fatalf("expected base_branch and work_branch, got %#v", task)
	}
	if task.Engine != "opencode" || task.Payload.Engine != "opencode" {
		t.Fatalf("expected opencode engine, got %#v", task)
	}
	if task.OpenCode.ExecutionEnabled {
		t.Fatal("sample task must not enable execution")
	}
}

func TestMarshalSampleTaskIsDeterministic(t *testing.T) {
	cfg := config.LocalConfig{
		SchemaVersion: config.CurrentSchemaVersion,
		NodeID:        "node-123",
		MachineName:   "test-machine",
		Mode:          config.ModeLocalSelfBuild,
		RepoPath:      "C:/repo",
		StatePath:     "C:/state",
		DefaultModel:  config.DefaultModelPlaceholder,
	}
	task := GenerateSampleTask(cfg)
	first, err := MarshalSampleTask(task)
	if err != nil {
		t.Fatalf("MarshalSampleTask returned error: %v", err)
	}
	second, err := MarshalSampleTask(task)
	if err != nil {
		t.Fatalf("MarshalSampleTask returned error: %v", err)
	}
	if string(first) != string(second) {
		t.Fatal("sample task JSON should be deterministic")
	}
	json := string(first)
	for _, want := range []string{`"base_branch"`, `"work_branch"`, `"graphify_required"`} {
		if !strings.Contains(json, want) {
			t.Fatalf("expected JSON to contain %s: %s", want, json)
		}
	}
}
