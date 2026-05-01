// Package status reports local Karkhana node readiness.
package status

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/idearefinery/karkhana-node/internal/config"
)

// Options controls status inspection.
type Options struct {
	ConfigPath string
}

// DirStatus reports whether a required state directory exists.
type DirStatus struct {
	Path  string
	Ready bool
	Error string
}

// Result contains local initialization and state readiness facts.
type Result struct {
	Initialized bool
	ConfigPath  string
	Config      config.LocalConfig
	StateDirs   []DirStatus
	TaskCount   int
	RunCount    int
	Warnings    []string
}

// Run inspects local config and state without starting any daemon.
func Run(opts Options) Result {
	configPath := strings.TrimSpace(opts.ConfigPath)
	if configPath == "" {
		path, err := config.ConfigFilePath()
		if err != nil {
			return Result{Warnings: []string{fmt.Sprintf("could not resolve config path: %v", err)}}
		}
		configPath = path
	}

	result := Result{ConfigPath: configPath}
	cfg, err := config.LoadLocalConfig(configPath)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			result.Warnings = append(result.Warnings, "Karkhana is not initialized; run 'karkhana init'.")
		} else {
			result.Warnings = append(result.Warnings, fmt.Sprintf("could not load config: %v", err))
		}
		return result
	}

	result.Initialized = true
	result.Config = cfg
	for _, dir := range config.StateDirs(cfg.StatePath) {
		result.StateDirs = append(result.StateDirs, inspectDir(dir))
	}
	result.TaskCount = countFiles(config.TaskDir(cfg.StatePath), ".json")
	result.RunCount = countRunFiles(config.RunDir(cfg.StatePath))
	return result
}

func inspectDir(path string) DirStatus {
	info, err := os.Stat(path)
	if err != nil {
		return DirStatus{Path: path, Error: err.Error()}
	}
	if !info.IsDir() {
		return DirStatus{Path: path, Error: "not a directory"}
	}
	return DirStatus{Path: path, Ready: true}
}

func countFiles(dir string, suffix string) int {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return 0
	}
	count := 0
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		if suffix == "" || strings.HasSuffix(strings.ToLower(entry.Name()), suffix) || filepath.Ext(entry.Name()) == suffix {
			count++
		}
	}
	return count
}

func countRunFiles(dir string) int {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return 0
	}
	count := 0
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		if isRunRecordName(entry.Name()) {
			count++
		}
	}
	return count
}

func isRunRecordName(name string) bool {
	name = strings.TrimSpace(name)
	return strings.HasPrefix(name, "run-") && strings.HasSuffix(strings.ToLower(name), ".json")
}
