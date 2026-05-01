package config

import (
	"path/filepath"
	"strings"
	"testing"
)

func TestConfigFilePath(t *testing.T) {
	path, err := ConfigFilePath()
	if err != nil {
		t.Fatalf("ConfigFilePath returned error: %v", err)
	}
	if path == "" {
		t.Fatal("ConfigFilePath returned an empty path")
	}
	if !filepath.IsAbs(path) {
		t.Fatalf("ConfigFilePath should be absolute, got %q", path)
	}
	if !strings.Contains(strings.ToLower(path), appDirName) {
		t.Fatalf("ConfigFilePath should contain app dir %q, got %q", appDirName, path)
	}
	if filepath.Base(path) != "config.json" {
		t.Fatalf("ConfigFilePath should end with config.json, got %q", path)
	}
}
