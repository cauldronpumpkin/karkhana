package selfbuild

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/idearefinery/karkhana-node/internal/config"
	"github.com/idearefinery/karkhana-node/internal/opencode"
)

var runIDs = map[string]struct{}{}

const (
	runSchemaVersion = "karkhana.self_build_run.v1"
	defaultTimeout   = 15 * time.Minute
	logsTailLimit    = 4000
)

type RunOptions struct {
	Config  config.LocalConfig
	TaskRef string
	Model   string
	DryRun  bool
	Timeout time.Duration
	Now     func() time.Time
	Detect  func(context.Context) opencode.Info
	Runner  CommandRunner
}

type CommandRunner interface {
	Run(ctx context.Context, req CommandRequest) CommandResult
}

type CommandRequest struct {
	Path       string
	Args       []string
	Stdin      string
	WorkingDir string
	Timeout    time.Duration
}

type CommandResult struct {
	ExitCode int
	Stdout   string
	Stderr   string
	Duration time.Duration
	Err      error
}

type RunRecord struct {
	SchemaVersion string         `json:"schema_version"`
	ID            string         `json:"id"`
	TaskID        string         `json:"task_id"`
	TaskPath      string         `json:"task_path"`
	Status        string         `json:"status"`
	Engine        string         `json:"engine"`
	Model         string         `json:"model"`
	Command       string         `json:"command"`
	RepoPath      string         `json:"repo_path"`
	BranchName    string         `json:"branch_name,omitempty"`
	DryRun        bool           `json:"dry_run"`
	StartedAt     string         `json:"started_at"`
	CompletedAt   string         `json:"completed_at,omitempty"`
	DurationMS    int64          `json:"duration_ms"`
	ExitCode      int            `json:"exit_code"`
	Stdout        string         `json:"stdout,omitempty"`
	Stderr        string         `json:"stderr,omitempty"`
	StdoutPath    string         `json:"stdout_path,omitempty"`
	StderrPath    string         `json:"stderr_path,omitempty"`
	LogsPath      string         `json:"logs_path"`
	LogsTail      string         `json:"logs_tail"`
	Result        map[string]any `json:"result,omitempty"`
	Error         string         `json:"error,omitempty"`
	OpenCode      opencode.Info  `json:"opencode"`
	Task          Task           `json:"task"`
}

type RunResult struct {
	RecordPath string
	LogPath    string
	Record     RunRecord
}

func LoadTask(cfg config.LocalConfig, ref string) (Task, string, error) {
	ref = strings.TrimSpace(ref)
	if ref == "" {
		return Task{}, "", fmt.Errorf("task reference is required")
	}
	if info, err := os.Stat(ref); err == nil && !info.IsDir() {
		return loadTaskFile(ref)
	}
	if filepath.IsAbs(ref) {
		return loadTaskFile(ref)
	}
	taskPath := filepath.Join(config.TaskDir(cfg.StatePath), ref)
	if !strings.HasSuffix(strings.ToLower(taskPath), ".json") {
		taskPath += ".json"
	}
	return loadTaskFile(taskPath)
}

func RunTask(ctx context.Context, opts RunOptions) (RunResult, error) {
	if opts.Now == nil {
		opts.Now = time.Now
	}
	if opts.Detect == nil {
		opts.Detect = func(ctx context.Context) opencode.Info { return opencode.Detect(ctx, opencode.Options{}) }
	}
	if opts.Timeout <= 0 {
		opts.Timeout = defaultTimeout
	}
	task, taskPath, err := LoadTask(opts.Config, opts.TaskRef)
	if err != nil {
		return RunResult{}, err
	}
	if err := validateRepoPath(opts.Config.RepoPath); err != nil {
		return RunResult{}, err
	}
	started := opts.Now().UTC()
	runID, err := uniqueRunID(started)
	if err != nil {
		return RunResult{}, err
	}
	open := opts.Detect(ctx)
	model := selectModel(opts.Model, task.Model, opts.Config.DefaultModel)
	prompt := buildPrompt(task)
	command := buildCommand(model)
	record := RunRecord{
		SchemaVersion: runSchemaVersion,
		ID:            runID,
		TaskID:        task.ID,
		TaskPath:      taskPath,
		Status:        "running",
		Engine:        valueOrDefault(task.Engine, "opencode"),
		Model:         model,
		Command:       command,
		RepoPath:      opts.Config.RepoPath,
		BranchName:    task.WorkBranch,
		DryRun:        opts.DryRun,
		StartedAt:     started.Format(time.RFC3339Nano),
		OpenCode:      open,
		Task:          task,
		Result: map[string]any{
			"has_prompt":     prompt != "",
			"prompt_preview": promptPreview(prompt),
		},
	}
	if opts.DryRun {
		record.Status = "dry_run"
		record.CompletedAt = started.Format(time.RFC3339Nano)
		record.LogsTail = buildLogsTail(command, prompt, open, nil)
		return persistRecord(opts.Config, record)
	}
	if strings.TrimSpace(model) == "" || model == config.DefaultModelPlaceholder {
		return RunResult{}, fmt.Errorf("a real model is required; pass --model or update the local config")
	}
	if !open.Found || strings.TrimSpace(open.Path) == "" {
		return RunResult{}, fmt.Errorf("opencode was not found in PATH")
	}
	if opts.Runner == nil {
		opts.Runner = execRunner{}
	}
	commandCtx, cancel := context.WithTimeout(ctx, opts.Timeout)
	defer cancel()
	result := opts.Runner.Run(commandCtx, CommandRequest{
		Path:       open.Path,
		Args:       []string{"run", "--dangerously-skip-permissions", "--model", model},
		Stdin:      prompt,
		WorkingDir: opts.Config.RepoPath,
		Timeout:    opts.Timeout,
	})
	finished := opts.Now().UTC()
	if finished.Before(started) {
		finished = started
	}
	record.CompletedAt = finished.Format(time.RFC3339Nano)
	record.DurationMS = finished.Sub(started).Milliseconds()
	record.ExitCode = result.ExitCode
	record.Stdout = result.Stdout
	record.Stderr = result.Stderr
	record.LogsTail = buildLogsTail(command, prompt, open, &result)
	record.Result["opencode_exit_code"] = result.ExitCode
	record.Result["summary"] = summaryFor(result)
	if result.Err != nil {
		record.Status = "failed"
		record.Error = result.Err.Error()
	} else if result.ExitCode != 0 {
		record.Status = "failed"
		record.Error = fmt.Sprintf("opencode exited with code %d", result.ExitCode)
	} else {
		record.Status = "completed"
	}
	return persistRecord(opts.Config, record)
}

func loadTaskFile(path string) (Task, string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return Task{}, "", fmt.Errorf("load self-build task %s: %w", path, err)
	}
	var task Task
	if err := json.Unmarshal(data, &task); err != nil {
		return Task{}, "", fmt.Errorf("parse self-build task %s: %w", path, err)
	}
	return task, path, nil
}

func uniqueRunID(started time.Time) (string, error) {
	var salt [4]byte
	for i := 0; i < 8; i++ {
		if _, err := rand.Read(salt[:]); err != nil {
			return "", fmt.Errorf("generate run id: %w", err)
		}
		id := fmt.Sprintf("run-%s-%s", started.UTC().Format("20060102T150405.000000000Z"), hex.EncodeToString(salt[:]))
		if _, exists := runIDs[id]; !exists {
			runIDs[id] = struct{}{}
			return id, nil
		}
	}
	return "", fmt.Errorf("generate unique run id: exhausted attempts")
}

func selectModel(override, taskModel, configModel string) string {
	for _, candidate := range []string{override, taskModel, configModel} {
		if strings.TrimSpace(candidate) != "" {
			return strings.TrimSpace(candidate)
		}
	}
	return ""
}

func buildCommand(model string) string {
	model = strings.TrimSpace(model)
	if model == "" {
		return "opencode run --dangerously-skip-permissions"
	}
	return fmt.Sprintf("opencode run --dangerously-skip-permissions --model %s", model)
}

func buildPrompt(task Task) string {
	for _, candidate := range []string{task.Payload.Prompt, task.Payload.Goal, task.Goal} {
		if strings.TrimSpace(candidate) != "" {
			return strings.TrimSpace(candidate)
		}
	}
	return ""
}

func promptPreview(prompt string) string {
	prompt = strings.TrimSpace(prompt)
	if len(prompt) > 500 {
		return prompt[:500]
	}
	return prompt
}

func cfgLogsDir(cfg config.LocalConfig, runID string) string {
	return filepath.Join(cfg.StatePath, "logs", runID)
}

func persistRecord(cfg config.LocalConfig, record RunRecord) (RunResult, error) {
	runDir := config.RunDir(cfg.StatePath)
	logsDir := cfgLogsDir(cfg, record.ID)
	if err := os.MkdirAll(runDir, 0o700); err != nil {
		return RunResult{}, fmt.Errorf("create run directory: %w", err)
	}
	if err := os.MkdirAll(logsDir, 0o700); err != nil {
		return RunResult{}, fmt.Errorf("create log directory: %w", err)
	}
	record.StdoutPath = filepath.Join(logsDir, "stdout.log")
	record.StderrPath = filepath.Join(logsDir, "stderr.log")
	record.LogsPath = filepath.Join(logsDir, "combined.log")
	if err := os.WriteFile(record.StdoutPath, []byte(record.Stdout), 0o600); err != nil {
		return RunResult{}, fmt.Errorf("write stdout log: %w", err)
	}
	if err := os.WriteFile(record.StderrPath, []byte(record.Stderr), 0o600); err != nil {
		return RunResult{}, fmt.Errorf("write stderr log: %w", err)
	}
	if err := os.WriteFile(record.LogsPath, []byte(buildCombinedLog(record)), 0o600); err != nil {
		return RunResult{}, fmt.Errorf("write combined log: %w", err)
	}
	data, err := json.MarshalIndent(record, "", "  ")
	if err != nil {
		return RunResult{}, fmt.Errorf("marshal run record: %w", err)
	}
	data = append(data, '\n')
	recordPath := filepath.Join(runDir, record.ID+".json")
	if err := os.WriteFile(recordPath, data, 0o600); err != nil {
		return RunResult{}, fmt.Errorf("write run record: %w", err)
	}
	return RunResult{RecordPath: recordPath, LogPath: record.LogsPath, Record: record}, nil
}

func buildLogsTail(command, prompt string, open opencode.Info, result *CommandResult) string {
	var b strings.Builder
	b.WriteString("$ ")
	b.WriteString(command)
	b.WriteString("\n")
	if prompt != "" {
		b.WriteString(prompt)
		b.WriteString("\n")
	}
	if open.Path != "" {
		b.WriteString("opencode: ")
		b.WriteString(open.Path)
		if strings.TrimSpace(open.Version) != "" {
			b.WriteString(" (")
			b.WriteString(open.Version)
			b.WriteString(")")
		}
		b.WriteString("\n")
	}
	if result != nil {
		if result.Stdout != "" {
			b.WriteString(result.Stdout)
			b.WriteString("\n")
		}
		if result.Stderr != "" {
			b.WriteString(result.Stderr)
			b.WriteString("\n")
		}
		b.WriteString(fmt.Sprintf("exit code: %d\n", result.ExitCode))
	}
	tail := b.String()
	tail = truncateUTF8(tail, logsTailLimit)
	return tail
}

func truncateUTF8(value string, limit int) string {
	if limit <= 0 || value == "" {
		return ""
	}
	if len(value) <= limit && utf8.ValidString(value) {
		return value
	}
	if len(value) > limit {
		value = value[len(value)-limit:]
	}
	for len(value) > 0 && !utf8.ValidString(value) {
		value = value[1:]
	}
	return value
}

func buildCombinedLog(record RunRecord) string {
	if record.LogsTail != "" {
		return record.LogsTail
	}
	return strings.TrimSpace(strings.Join([]string{record.Stdout, record.Stderr}, "\n"))
}

func summaryFor(result CommandResult) string {
	if result.Err != nil {
		return result.Err.Error()
	}
	if result.ExitCode != 0 {
		return fmt.Sprintf("opencode exited with code %d", result.ExitCode)
	}
	return "OpenCode process completed."
}

func valueOrDefault(value, fallback string) string {
	if strings.TrimSpace(value) == "" {
		return fallback
	}
	return value
}

func validateRepoPath(path string) error {
	path = strings.TrimSpace(path)
	if path == "" {
		return fmt.Errorf("repo path is required")
	}
	info, err := os.Stat(path)
	if err != nil {
		return fmt.Errorf("repo path %s is not accessible: %w", path, err)
	}
	if !info.IsDir() {
		return fmt.Errorf("repo path %s is not a directory", path)
	}
	return nil
}

func isRunRecordName(name string) bool {
	return strings.HasPrefix(name, "run-") && strings.HasSuffix(strings.ToLower(name), ".json")
}

type execRunner struct{}

func (execRunner) Run(ctx context.Context, req CommandRequest) CommandResult {
	start := time.Now()
	cmd := exec.CommandContext(ctx, req.Path, req.Args...)
	cmd.Dir = req.WorkingDir
	cmd.Stdin = strings.NewReader(req.Stdin)
	var stdout, stderr strings.Builder
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	err := cmd.Run()
	result := CommandResult{Stdout: stdout.String(), Stderr: stderr.String(), Duration: time.Since(start), Err: err}
	if cmd.ProcessState != nil {
		result.ExitCode = cmd.ProcessState.ExitCode()
	}
	if err != nil && result.ExitCode == 0 {
		var exitErr *exec.ExitError
		if errors.As(err, &exitErr) && exitErr.ProcessState != nil {
			result.ExitCode = exitErr.ProcessState.ExitCode()
		}
	}
	return result
}
