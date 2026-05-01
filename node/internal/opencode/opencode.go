// Package opencode provides local-only detection helpers for the OpenCode CLI.
package opencode

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os/exec"
	"strings"
	"time"
)

// Info contains the local OpenCode installation facts.
type Info struct {
	Path    string
	Version string
	Found   bool
	Error   string
}

// Options injects dependencies for unit tests.
type Options struct {
	LookPath       func(string) (string, error)
	CommandVersion func(context.Context, string) (string, error)
}

// Detect finds OpenCode on PATH and captures its version if available.
func Detect(ctx context.Context, opts Options) Info {
	if opts.LookPath == nil {
		opts.LookPath = exec.LookPath
	}
	if opts.CommandVersion == nil {
		opts.CommandVersion = commandVersion
	}
	path, err := opts.LookPath("opencode")
	if err != nil {
		return Info{Error: "opencode was not found in PATH"}
	}

	version, err := opts.CommandVersion(ctx, path)
	if err != nil {
		return Info{Path: path, Found: true, Error: err.Error()}
	}

	return Info{Path: path, Version: version, Found: true}
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
