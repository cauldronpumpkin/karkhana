package selfbuild

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
	"unicode/utf8"

	"github.com/idearefinery/karkhana-node/internal/config"
	"github.com/idearefinery/karkhana-node/internal/opencode"
)

type stubRunner struct{ result CommandResult }

func (s stubRunner) Run(ctx context.Context, req CommandRequest) CommandResult { return s.result }

func TestLoadTaskByPathAndID(t *testing.T) {
	tmp := t.TempDir()
	cfg := config.LocalConfig{StatePath: tmp, DefaultModel: "demo-model"}
	task := Task{SchemaVersion: "karkhana.self_build_task.v1", ID: "demo-task", Goal: "goal", Model: "demo-model"}
	data, err := json.Marshal(task)
	if err != nil {
		t.Fatal(err)
	}
	data = append(data, '\n')
	path := filepath.Join(config.TaskDir(cfg.StatePath), task.ID+".json")
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, data, 0o600); err != nil {
		t.Fatal(err)
	}

	loaded, loadedPath, err := LoadTask(cfg, task.ID)
	if err != nil {
		t.Fatalf("LoadTask by id: %v", err)
	}
	if loaded.ID != task.ID || loadedPath != path {
		t.Fatalf("unexpected load result: %#v %s", loaded, loadedPath)
	}

	loaded2, loadedPath2, err := LoadTask(cfg, path)
	if err != nil {
		t.Fatalf("LoadTask by path: %v", err)
	}
	if loaded2.ID != task.ID || loadedPath2 != path {
		t.Fatalf("unexpected path load result: %#v %s", loaded2, loadedPath2)
	}
}

func TestRunTaskDryRunPersistsRecord(t *testing.T) {
	tmp := t.TempDir()
	repo := filepath.Join(tmp, "repo")
	if err := os.MkdirAll(repo, 0o700); err != nil {
		t.Fatal(err)
	}
	cfg := config.LocalConfig{StatePath: tmp, RepoPath: repo, DefaultModel: "demo-model"}
	task := Task{SchemaVersion: "karkhana.self_build_task.v1", ID: "demo-task", Goal: "goal", Model: "demo-model"}
	writeTask(t, cfg, task)
	start := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	res, err := RunTask(context.Background(), RunOptions{Config: cfg, TaskRef: task.ID, DryRun: true, Now: func() time.Time { return start }})
	if err != nil {
		t.Fatalf("RunTask dry-run: %v", err)
	}
	if !res.Record.DryRun || res.Record.ExitCode != 0 || res.Record.CompletedAt == "" || res.Record.Status != "dry_run" {
		t.Fatalf("unexpected dry-run result: %#v", res)
	}
	if _, err := os.Stat(res.RecordPath); err != nil {
		t.Fatalf("missing run record: %v", err)
	}
	if _, err := os.Stat(res.LogPath); err != nil {
		t.Fatalf("missing log file: %v", err)
	}
}

func TestRunTaskCapturesRunnerOutput(t *testing.T) {
	tmp := t.TempDir()
	repo := filepath.Join(tmp, "repo")
	if err := os.MkdirAll(repo, 0o700); err != nil {
		t.Fatal(err)
	}
	cfg := config.LocalConfig{StatePath: tmp, RepoPath: repo, DefaultModel: "demo-model"}
	task := Task{SchemaVersion: "karkhana.self_build_task.v1", ID: "demo-task", Goal: "goal", Model: "demo-model"}
	writeTask(t, cfg, task)
	start := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	boom := errors.New("boom")
	nowCalls := 0
	res, err := RunTask(context.Background(), RunOptions{Config: cfg, TaskRef: task.ID, Now: func() time.Time {
		nowCalls++
		if nowCalls == 1 {
			return start
		}
		return start.Add(2 * time.Second)
	}, Runner: stubRunner{result: CommandResult{ExitCode: 7, Stdout: "out", Stderr: "err", Err: boom}}})
	if err != nil {
		t.Fatalf("RunTask: %v", err)
	}
	if res.Record.ExitCode != 7 || res.Record.Stdout != "out" || res.Record.Stderr != "err" || !strings.Contains(res.Record.Error, "boom") || res.Record.Status != "failed" {
		t.Fatalf("unexpected result: %#v", res)
	}
	if res.Record.DurationMS != 2000 {
		t.Fatalf("unexpected duration: %d", res.Record.DurationMS)
	}
}

func TestRunTaskRejectsMissingRepoPath(t *testing.T) {
	tmp := t.TempDir()
	cfg := config.LocalConfig{StatePath: tmp, RepoPath: filepath.Join(tmp, "missing"), DefaultModel: "demo-model"}
	task := Task{SchemaVersion: "karkhana.self_build_task.v1", ID: "demo-task", Goal: "goal", Model: "demo-model"}
	writeTask(t, cfg, task)
	_, err := RunTask(context.Background(), RunOptions{Config: cfg, TaskRef: task.ID, DryRun: false, Runner: stubRunner{result: CommandResult{ExitCode: 0}}})
	if err == nil || !strings.Contains(err.Error(), "repo path") {
		t.Fatalf("expected repo path error, got %v", err)
	}
}

func TestRunTaskRejectsEmptyRepoPath(t *testing.T) {
	tmp := t.TempDir()
	cfg := config.LocalConfig{StatePath: tmp, RepoPath: "", DefaultModel: "demo-model"}
	task := Task{SchemaVersion: "karkhana.self_build_task.v1", ID: "demo-task", Goal: "goal", Model: "demo-model"}
	writeTask(t, cfg, task)
	_, err := RunTask(context.Background(), RunOptions{Config: cfg, TaskRef: task.ID, DryRun: true})
	if err == nil || !strings.Contains(err.Error(), "repo path is required") {
		t.Fatalf("expected repo path required error, got %v", err)
	}
}

func TestRunTaskRejectsEmptyModel(t *testing.T) {
	tmp := t.TempDir()
	repo := filepath.Join(tmp, "repo")
	if err := os.MkdirAll(repo, 0o700); err != nil {
		t.Fatal(err)
	}
	cfg := config.LocalConfig{StatePath: tmp, RepoPath: repo}
	task := Task{SchemaVersion: "karkhana.self_build_task.v1", ID: "demo-task", Goal: "goal"}
	writeTask(t, cfg, task)
	_, err := RunTask(context.Background(), RunOptions{Config: cfg, TaskRef: task.ID, DryRun: false, Detect: func(context.Context) opencode.Info { return opencode.Info{Found: true, Path: "/usr/bin/opencode"} }})
	if err == nil || !strings.Contains(err.Error(), "real model") {
		t.Fatalf("expected model error, got %v", err)
	}
}

func TestRunTaskRejectsWhitespaceModel(t *testing.T) {
	tmp := t.TempDir()
	repo := filepath.Join(tmp, "repo")
	if err := os.MkdirAll(repo, 0o700); err != nil {
		t.Fatal(err)
	}
	cfg := config.LocalConfig{StatePath: tmp, RepoPath: repo}
	task := Task{SchemaVersion: "karkhana.self_build_task.v1", ID: "demo-task", Goal: "goal"}
	writeTask(t, cfg, task)
	_, err := RunTask(context.Background(), RunOptions{Config: cfg, TaskRef: task.ID, DryRun: false, Model: "   ", Detect: func(context.Context) opencode.Info { return opencode.Info{Found: true, Path: "/usr/bin/opencode"} }})
	if err == nil || !strings.Contains(err.Error(), "real model") {
		t.Fatalf("expected model error, got %v", err)
	}
}

func TestBuildLogsTailIsUtf8Safe(t *testing.T) {
	tail := buildLogsTail("opencode run", "hello ✅ world", opencode.Info{Path: "/usr/bin/opencode", Version: "1.0"}, &CommandResult{ExitCode: 0, Stdout: strings.Repeat("é", 3000)})
	if !utf8.ValidString(tail) {
		t.Fatalf("expected valid utf8 tail")
	}
}

func TestSelectModel(t *testing.T) {
	tests := []struct {
		name       string
		override   string
		taskModel  string
		configMode string
		want       string
	}{
		{name: "override wins", override: "  gpt-4.1  ", taskModel: "task", configMode: "config", want: "gpt-4.1"},
		{name: "task wins", override: "", taskModel: " task-model ", configMode: "config", want: "task-model"},
		{name: "config fallback", override: "", taskModel: "", configMode: " config-model ", want: "config-model"},
		{name: "empty", override: "", taskModel: "", configMode: "", want: ""},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := selectModel(tt.override, tt.taskModel, tt.configMode); got != tt.want {
				t.Fatalf("selectModel() = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestBuildCommand(t *testing.T) {
	tests := []struct {
		name  string
		model string
		want  string
	}{
		{name: "empty", model: "", want: "opencode run --dangerously-skip-permissions"},
		{name: "trimmed", model: "  model-x  ", want: "opencode run --dangerously-skip-permissions --model model-x"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := buildCommand(tt.model); got != tt.want {
				t.Fatalf("buildCommand() = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestBuildPrompt(t *testing.T) {
	tests := []struct {
		name string
		task Task
		want string
	}{
		{name: "payload prompt", task: Task{Payload: Payload{Prompt: "  prompt  ", Goal: "goal"}, Goal: "task goal"}, want: "prompt"},
		{name: "payload goal", task: Task{Payload: Payload{Goal: "  prompt goal  "}, Goal: "task goal"}, want: "prompt goal"},
		{name: "task goal", task: Task{Goal: "  task goal  "}, want: "task goal"},
		{name: "empty", task: Task{}, want: ""},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := buildPrompt(tt.task); got != tt.want {
				t.Fatalf("buildPrompt() = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestValidateRepoPath(t *testing.T) {
	tmp := t.TempDir()
	file := filepath.Join(tmp, "file.txt")
	if err := os.WriteFile(file, []byte("x"), 0o600); err != nil {
		t.Fatal(err)
	}
	tests := []struct {
		name string
		path string
		want string
	}{
		{name: "empty", path: "   ", want: "repo path is required"},
		{name: "missing", path: filepath.Join(tmp, "missing"), want: "not accessible"},
		{name: "file", path: file, want: "not a directory"},
		{name: "dir", path: tmp, want: ""},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validateRepoPath(tt.path)
			if tt.want == "" {
				if err != nil {
					t.Fatalf("validateRepoPath() unexpected error: %v", err)
				}
				return
			}
			if err == nil || !strings.Contains(err.Error(), tt.want) {
				t.Fatalf("validateRepoPath() error = %v, want %q", err, tt.want)
			}
		})
	}
}

func TestUniqueRunIDIsUnique(t *testing.T) {
	start := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	id1, err := uniqueRunID(start)
	if err != nil {
		t.Fatal(err)
	}
	id2, err := uniqueRunID(start)
	if err != nil {
		t.Fatal(err)
	}
	if id1 == id2 {
		t.Fatalf("expected unique ids, got %q", id1)
	}
}

func TestIsRunRecordName(t *testing.T) {
	tests := []struct {
		name string
		in   string
		want bool
	}{
		{name: "lowercase json", in: "run-123.json", want: true},
		{name: "uppercase extension", in: "run-123.JSON", want: true},
		{name: "wrong prefix", in: "task-123.json", want: false},
		{name: "wrong suffix", in: "run-123.txt", want: false},
		{name: "trimmed", in: "  run-123.json  ", want: false},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := isRunRecordName(tt.in); got != tt.want {
				t.Fatalf("isRunRecordName() = %v, want %v", got, tt.want)
			}
		})
	}
}

func writeTask(t *testing.T, cfg config.LocalConfig, task Task) {
	t.Helper()
	data, err := json.Marshal(task)
	if err != nil {
		t.Fatal(err)
	}
	data = append(data, '\n')
	path := filepath.Join(config.TaskDir(cfg.StatePath), task.ID+".json")
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, data, 0o600); err != nil {
		t.Fatal(err)
	}
}
