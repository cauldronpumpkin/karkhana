// Package doctor performs safe local diagnostic checks for the Karkhana CLI.
package doctor

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"strings"
	"time"

	"github.com/idearefinery/karkhana-node/internal/config"
)

// Result contains safe local diagnostic facts.
type Result struct {
	OS              string
	Arch            string
	WorkingDir      string
	ConfigPath      string
	ConfigLoaded    bool
	RepoPath        string
	StatePath       string
	OpenCodePath    string
	OpenCodeVersion string
	GitPath         string
	GraphifyPath    string
	Warnings        []string
}

// Options injects dependencies for testing.
type Options struct {
	LookPath       func(string) (string, error)
	CommandVersion func(context.Context, string) (string, error)
	WorkingDir     func() (string, error)
}

// Run checks local facts without requiring network access or credentials.
func Run(ctx context.Context, opts Options) Result {
	if opts.LookPath == nil {
		opts.LookPath = exec.LookPath
	}
	if opts.CommandVersion == nil {
		opts.CommandVersion = commandVersion
	}
	if opts.WorkingDir == nil {
		opts.WorkingDir = os.Getwd
	}

	result := Result{
		OS:   runtime.GOOS,
		Arch: runtime.GOARCH,
	}

	wd, err := opts.WorkingDir()
	if err != nil {
		result.Warnings = append(result.Warnings, fmt.Sprintf("could not determine current working directory: %v", err))
	} else {
		result.WorkingDir = wd
	}

	configPath, err := config.ConfigFilePath()
	if err != nil {
		result.Warnings = append(result.Warnings, fmt.Sprintf("could not determine config path: %v", err))
	} else {
		result.ConfigPath = configPath
		localConfig, err := config.LoadLocalConfig(configPath)
		if err != nil {
			if !errors.Is(err, os.ErrNotExist) {
				result.Warnings = append(result.Warnings, fmt.Sprintf("could not load config: %v", err))
			}
		} else {
			result.ConfigLoaded = true
			result.RepoPath = localConfig.RepoPath
			result.StatePath = localConfig.StatePath
			if info, err := os.Stat(localConfig.RepoPath); err != nil {
				result.Warnings = append(result.Warnings, fmt.Sprintf("configured repo path is not readable: %v", err))
			} else if !info.IsDir() {
				result.Warnings = append(result.Warnings, "configured repo path is not a directory")
			}
			for _, dir := range config.StateDirs(localConfig.StatePath) {
				if info, err := os.Stat(dir); err != nil {
					result.Warnings = append(result.Warnings, fmt.Sprintf("state directory missing or unreadable %s: %v", dir, err))
				} else if !info.IsDir() {
					result.Warnings = append(result.Warnings, fmt.Sprintf("state path is not a directory: %s", dir))
				}
			}
		}
	}

	opencodePath, err := opts.LookPath("opencode")
	if err != nil {
		result.Warnings = append(result.Warnings, "opencode was not found in PATH; install OpenCode before enabling real job execution")
	} else {
		result.OpenCodePath = opencodePath
		version, err := opts.CommandVersion(ctx, opencodePath)
		if err != nil {
			result.Warnings = append(result.Warnings, fmt.Sprintf("opencode exists but version check failed: %v", err))
		} else {
			result.OpenCodeVersion = version
		}
	}

	gitPath, err := opts.LookPath("git")
	if err != nil {
		result.Warnings = append(result.Warnings, "git was not found in PATH; branch-aware self-build tasks need git")
	} else {
		result.GitPath = gitPath
	}

	graphifyPath, err := opts.LookPath("graphify")
	if err != nil {
		result.Warnings = append(result.Warnings, "graphify was not found in PATH; run graphify update . manually when available")
	} else {
		result.GraphifyPath = graphifyPath
	}

	return result
}

func commandVersion(ctx context.Context, path string) (string, error) {
	versionCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	cmd := exec.CommandContext(versionCtx, path, "--version")
	var stdout bytes.Buffer
	var stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		message := strings.TrimSpace(stderr.String())
		if message == "" {
			message = err.Error()
		}
		return "", errors.New(message)
	}

	output := strings.TrimSpace(stdout.String())
	if output == "" {
		output = strings.TrimSpace(stderr.String())
	}
	if output == "" {
		return "", fmt.Errorf("empty version output")
	}
	return output, nil
}
