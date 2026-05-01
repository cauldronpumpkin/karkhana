// Package selfbuild emits local Karkhana self-build task specifications.
package selfbuild

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/idearefinery/karkhana-node/internal/config"
)

const sampleTaskID = "karkhana-self-build-sample"

// Task is the machine-readable self-build task specification.
type Task struct {
	SchemaVersion        string   `json:"schema_version"`
	ID                   string   `json:"id"`
	Goal                 string   `json:"goal"`
	RepoPath             string   `json:"repo_path"`
	BaseBranch           string   `json:"base_branch"`
	WorkBranch           string   `json:"work_branch"`
	ContextFiles         []string `json:"context_files"`
	Requirements         []string `json:"requirements"`
	Guardrails           []string `json:"guardrails"`
	VerificationCommands []string `json:"verification_commands"`
	GraphifyRequired     bool     `json:"graphify_required"`
	Engine               string   `json:"engine"`
	Model                string   `json:"model"`
	Payload              Payload  `json:"payload"`
	OpenCode             OpenCode `json:"opencode"`
}

// Payload mirrors backend WorkItem payload conventions without creating one.
type Payload struct {
	JobType string `json:"job_type"`
	Engine  string `json:"engine"`
	Goal    string `json:"goal"`
	Prompt  string `json:"prompt"`
}

// OpenCode describes the intended future execution engine without invoking it.
type OpenCode struct {
	ExecutionEnabled bool   `json:"execution_enabled"`
	CommandHint      string `json:"command_hint"`
}

// GenerateSampleTask builds a deterministic sample self-build task.
func GenerateSampleTask(cfg config.LocalConfig) Task {
	goal := "Improve Karkhana's local self-build foundation while preserving a local-only, OpenCode-driven execution direction."
	prompt := "You are working in the Karkhana repository. Read graphify-out/GRAPH_REPORT.md first. Implement only the next local self-build foundation improvement requested by the user. Do not add auth, cloud sync, master lease, daemon service, backend API changes, worker-app changes, or OpenCode execution unless explicitly requested. Run relevant Go/CLI checks and graphify update . after code changes."
	return Task{
		SchemaVersion: "karkhana.self_build_task.v1",
		ID:            sampleTaskID,
		Goal:          goal,
		RepoPath:      cfg.RepoPath,
		BaseBranch:    "main",
		WorkBranch:    "karkhana/self-build-foundation-sample",
		ContextFiles: []string{
			"graphify-out/GRAPH_REPORT.md",
			"PROJECT_ANALYSIS.md",
			"package.json",
			"cli/package.json",
			"cli/bin/karkhana.js",
			"node/go.mod",
			"node/cmd/karkhana/main.go",
			"node/internal/config/paths.go",
			"node/internal/doctor/doctor.go",
			"backend/app/repository.py",
			"backend/app/services/project_twin.py",
			"backend/app/services/local_workers.py",
		},
		Requirements: []string{
			"Keep Karkhana local-first: the Go node is the product brain and OpenCode is the future execution engine.",
			"Keep the website as dashboard-only and backend/Lambda as control APIs only.",
			"Emit machine-readable self-build tasks that are deterministic and safe to inspect.",
			"Preserve install modes separately from runtime/config mode.",
		},
		Guardrails: []string{
			"Do not overwrite unrelated user changes.",
			"Do not modify worker-app or backend APIs for this foundation slice unless a later task explicitly requires it.",
			"Do not implement auth, cloud sync, master lease, daemon service, or OpenCode execution in this task.",
			"Run graphify update . after code changes.",
		},
		VerificationCommands: []string{
			"cd node; go test ./...",
			"cd cli; node ./bin/karkhana.js version",
			"graphify update .",
		},
		GraphifyRequired: true,
		Engine:           "opencode",
		Model:            cfg.DefaultModel,
		Payload: Payload{
			JobType: "self_build",
			Engine:  "opencode",
			Goal:    goal,
			Prompt:  prompt,
		},
		OpenCode: OpenCode{
			ExecutionEnabled: false,
			CommandHint:      "OpenCode execution remains local-only via self-build run; this sample task is a local spec only.",
		},
	}
}

// MarshalSampleTask returns stable indented JSON for a sample task.
func MarshalSampleTask(task Task) ([]byte, error) {
	data, err := json.MarshalIndent(task, "", "  ")
	if err != nil {
		return nil, fmt.Errorf("marshal sample self-build task: %w", err)
	}
	return append(data, '\n'), nil
}

// WriteSampleTask writes the sample task to the local state tasks directory.
func WriteSampleTask(cfg config.LocalConfig) ([]byte, string, error) {
	task := GenerateSampleTask(cfg)
	data, err := MarshalSampleTask(task)
	if err != nil {
		return nil, "", err
	}
	path := filepath.Join(config.TaskDir(cfg.StatePath), sampleTaskID+".json")
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return nil, "", fmt.Errorf("create task directory: %w", err)
	}
	if err := os.WriteFile(path, data, 0o600); err != nil {
		return nil, "", fmt.Errorf("write sample self-build task: %w", err)
	}
	return data, path, nil
}
