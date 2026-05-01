package doctor

import (
	"context"
	"errors"
	"strings"
	"testing"
)

func TestRunWarnsWhenOpenCodeMissing(t *testing.T) {
	result := Run(context.Background(), Options{
		LookPath:   func(string) (string, error) { return "", errors.New("not found") },
		WorkingDir: func() (string, error) { return "/tmp/project", nil },
	})

	if result.OS == "" || result.Arch == "" {
		t.Fatalf("expected OS and Arch, got %#v", result)
	}
	if result.OpenCodePath != "" {
		t.Fatalf("expected empty OpenCodePath, got %q", result.OpenCodePath)
	}
	if len(result.Warnings) == 0 {
		t.Fatal("expected warning for missing opencode")
	}
}

func TestRunCapturesOpenCodeVersion(t *testing.T) {
	result := Run(context.Background(), Options{
		LookPath: func(string) (string, error) { return "/usr/bin/opencode", nil },
		CommandVersion: func(context.Context, string) (string, error) {
			return "opencode 1.2.3", nil
		},
		WorkingDir: func() (string, error) { return "/tmp/project", nil },
	})

	if result.OpenCodePath != "/usr/bin/opencode" {
		t.Fatalf("unexpected OpenCodePath: %q", result.OpenCodePath)
	}
	if !strings.Contains(result.OpenCodeVersion, "1.2.3") {
		t.Fatalf("unexpected OpenCodeVersion: %q", result.OpenCodeVersion)
	}
}

func TestRunWarnsWhenOpenCodeVersionFailsButContinues(t *testing.T) {
	result := Run(context.Background(), Options{
		LookPath: func(name string) (string, error) {
			switch name {
			case "opencode":
				return "/usr/bin/opencode", nil
			case "git":
				return "/usr/bin/git", nil
			case "graphify":
				return "/usr/bin/graphify", nil
			default:
				return "", errors.New("unexpected lookup")
			}
		},
		CommandVersion: func(context.Context, string) (string, error) {
			return "", errors.New("version failed")
		},
		WorkingDir: func() (string, error) { return "/tmp/project", nil },
	})

	if result.OpenCodePath != "/usr/bin/opencode" {
		t.Fatalf("unexpected OpenCodePath: %q", result.OpenCodePath)
	}
	if result.GitPath != "/usr/bin/git" || result.GraphifyPath != "/usr/bin/graphify" {
		t.Fatalf("expected git and graphify checks to run, got %#v", result)
	}
	if result.OpenCodeVersion != "" {
		t.Fatalf("expected empty OpenCodeVersion, got %q", result.OpenCodeVersion)
	}
	if len(result.Warnings) == 0 {
		t.Fatal("expected warning when opencode version check fails")
	}
	if !strings.Contains(strings.Join(result.Warnings, "\n"), "version check failed") {
		t.Fatalf("expected version failure warning, got %#v", result.Warnings)
	}
}

func TestRunWarnsWhenWorkingDirFails(t *testing.T) {
	result := Run(context.Background(), Options{
		LookPath: func(string) (string, error) { return "", errors.New("not found") },
		WorkingDir: func() (string, error) {
			return "", errors.New("cwd failed")
		},
	})

	if result.WorkingDir != "" {
		t.Fatalf("expected empty WorkingDir, got %q", result.WorkingDir)
	}
	if len(result.Warnings) == 0 {
		t.Fatal("expected warning when working dir lookup fails")
	}
	if !strings.Contains(strings.Join(result.Warnings, "\n"), "current working directory") {
		t.Fatalf("expected working dir warning, got %#v", result.Warnings)
	}
}
