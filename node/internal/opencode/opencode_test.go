package opencode

import (
	"context"
	"errors"
	"strings"
	"testing"
)

func TestDetectMissingOpencode(t *testing.T) {
	info := Detect(context.Background(), Options{
		LookPath: func(string) (string, error) { return "", errors.New("not found") },
	})

	if info.Found {
		t.Fatalf("expected not found, got %#v", info)
	}
	if info.Error == "" {
		t.Fatal("expected error message for missing opencode")
	}
}

func TestDetectCapturesVersion(t *testing.T) {
	info := Detect(context.Background(), Options{
		LookPath: func(string) (string, error) { return "/usr/bin/opencode", nil },
		CommandVersion: func(context.Context, string) (string, error) {
			return "opencode 1.2.3", nil
		},
	})

	if !info.Found || info.Path != "/usr/bin/opencode" {
		t.Fatalf("unexpected info: %#v", info)
	}
	if !strings.Contains(info.Version, "1.2.3") {
		t.Fatalf("unexpected version: %q", info.Version)
	}
	if info.Error != "" {
		t.Fatalf("expected no error, got %q", info.Error)
	}
}

func TestDetectReturnsVersionErrorWithoutFailingLookup(t *testing.T) {
	info := Detect(context.Background(), Options{
		LookPath: func(name string) (string, error) {
			if name != "opencode" {
				t.Fatalf("unexpected lookup: %s", name)
			}
			return "/usr/bin/opencode", nil
		},
		CommandVersion: func(context.Context, string) (string, error) {
			return "", errors.New("version failed")
		},
	})

	if !info.Found || info.Path != "/usr/bin/opencode" {
		t.Fatalf("unexpected info: %#v", info)
	}
	if info.Version != "" {
		t.Fatalf("expected empty version, got %q", info.Version)
	}
	if !strings.Contains(info.Error, "version failed") {
		t.Fatalf("unexpected error: %q", info.Error)
	}
}
