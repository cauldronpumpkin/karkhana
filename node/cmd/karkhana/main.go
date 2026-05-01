package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"strings"
	"time"

	"github.com/idearefinery/karkhana-node/internal/config"
	"github.com/idearefinery/karkhana-node/internal/doctor"
	"github.com/idearefinery/karkhana-node/internal/install"
	"github.com/idearefinery/karkhana-node/internal/opencode"
	"github.com/idearefinery/karkhana-node/internal/selfbuild"
	"github.com/idearefinery/karkhana-node/internal/setup"
	"github.com/idearefinery/karkhana-node/internal/status"
	"github.com/idearefinery/karkhana-node/internal/version"
)

func main() {
	if err := run(os.Args[1:]); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run(args []string) error {
	if len(args) == 0 || args[0] == "help" || args[0] == "--help" || args[0] == "-h" {
		printUsage()
		return nil
	}

	switch args[0] {
	case "version", "--version", "-v":
		fmt.Println(version.Info())
		return nil
	case "doctor":
		return runDoctor(args[1:])
	case "init":
		return runInit(args[1:])
	case "install":
		return runInstall(args[1:])
	case "status":
		return runStatus()
	case "self-build":
		return runSelfBuild(args[1:])
	default:
		return fmt.Errorf("unknown command %q\n\nRun 'karkhana help' for usage.", args[0])
	}
}

func runDoctor(args []string) error {
	if len(args) > 0 && isHelpArg(args[0]) {
		fmt.Println(`Usage:
  karkhana doctor

Inspect the local node environment without executing OpenCode.`)
		return nil
	}
	if len(args) > 0 {
		return fmt.Errorf("unexpected doctor argument(s): %s", strings.Join(args, " "))
	}
	result := doctor.Run(context.Background(), doctor.Options{})
	fmt.Println("Karkhana doctor")
	fmt.Printf("  OS: %s\n", result.OS)
	fmt.Printf("  Architecture: %s\n", result.Arch)
	fmt.Printf("  Current working directory: %s\n", valueOrDash(result.WorkingDir))
	fmt.Printf("  Planned config path: %s\n", valueOrDash(result.ConfigPath))
	if result.ConfigLoaded {
		fmt.Println("  Config: loaded")
		fmt.Printf("  Repo path: %s\n", valueOrDash(result.RepoPath))
		fmt.Printf("  State path: %s\n", valueOrDash(result.StatePath))
	} else {
		fmt.Println("  Config: not initialized")
	}
	if result.OpenCodePath == "" {
		fmt.Println("  OpenCode: not found")
	} else {
		fmt.Printf("  OpenCode path: %s\n", result.OpenCodePath)
		fmt.Printf("  OpenCode version: %s\n", valueOrDash(result.OpenCodeVersion))
	}
	fmt.Printf("  Git path: %s\n", valueOrDash(result.GitPath))
	fmt.Printf("  Graphify path: %s\n", valueOrDash(result.GraphifyPath))
	if len(result.Warnings) > 0 {
		fmt.Println("Warnings:")
		for _, warning := range result.Warnings {
			fmt.Printf("  - %s\n", warning)
		}
	}
	fmt.Println("Doctor completed. Foundation commands do not execute OpenCode.")
	return nil
}

func runInit(args []string) error {
	if len(args) > 0 && isHelpArg(args[0]) {
		fmt.Println(`Usage:
  karkhana init [--repo PATH] [--state PATH] [--machine-name NAME] [--force]

Initialize local Karkhana config for this repository and machine.`)
		return nil
	}
	flags := flag.NewFlagSet("init", flag.ContinueOnError)
	flags.SetOutput(io.Discard)
	repo := flags.String("repo", "", "repository path to manage; defaults to current working directory")
	state := flags.String("state", "", "local state path; defaults to user-level Karkhana state directory")
	machineName := flags.String("machine-name", "", "machine name for this local node; defaults to OS hostname")
	force := flags.Bool("force", false, "overwrite existing local config")
	if err := flags.Parse(args); err != nil {
		return err
	}
	if flags.NArg() > 0 {
		return fmt.Errorf("unexpected init argument(s): %s", strings.Join(flags.Args(), " "))
	}

	result, err := setup.Run(setup.Options{RepoPath: *repo, StatePath: *state, MachineName: *machineName, Force: *force})
	if err != nil {
		return err
	}
	if result.AlreadyInitialized {
		fmt.Println("Karkhana is already initialized.")
	} else {
		fmt.Println("Karkhana initialized.")
	}
	fmt.Printf("  Config path: %s\n", result.ConfigPath)
	fmt.Printf("  Node ID: %s\n", result.Config.NodeID)
	fmt.Printf("  Machine name: %s\n", result.Config.MachineName)
	fmt.Printf("  Mode: %s\n", result.Config.Mode)
	fmt.Printf("  Repo path: %s\n", result.Config.RepoPath)
	fmt.Printf("  State path: %s\n", result.Config.StatePath)
	if len(result.CreatedDirs) > 0 {
		fmt.Println("  State directories ready:")
		for _, dir := range result.CreatedDirs {
			fmt.Printf("    - %s\n", dir)
		}
	}
	return nil
}

func runInstall(args []string) error {
	if len(args) > 0 && isHelpArg(args[0]) {
		fmt.Println(`Usage:
  karkhana install [--mode worker|master|master-worker]

Validate the future node install mode without installing services, credentials,
or a master lease.`)
		return nil
	}
	flags := flag.NewFlagSet("install", flag.ContinueOnError)
	flags.SetOutput(io.Discard)
	mode := flags.String("mode", install.ModeWorker, "future node mode: worker, master, or master-worker")
	if err := flags.Parse(args); err != nil {
		return err
	}
	if flags.NArg() > 0 {
		return fmt.Errorf("unexpected install argument(s): %s", strings.Join(flags.Args(), " "))
	}

	trimmedMode := strings.TrimSpace(*mode)
	if err := install.ValidateMode(trimmedMode); err != nil {
		return err
	}

	fmt.Printf("Karkhana install stub accepted mode: %s\n", trimmedMode)
	fmt.Println("No daemon service, startup entry, credentials, or master lease were installed.")
	fmt.Println("A future slice will install and manage the headless Go node runtime.")
	return nil
}

func runStatus() error {
	result := status.Run(status.Options{})
	fmt.Println("Karkhana status")
	fmt.Printf("  Config path: %s\n", valueOrDash(result.ConfigPath))
	if !result.Initialized {
		fmt.Println("  Initialized: no")
		for _, warning := range result.Warnings {
			fmt.Printf("  Warning: %s\n", warning)
		}
		fmt.Println("  Daemon: not installed/running in this foundation slice")
		return nil
	}
	fmt.Println("  Initialized: yes")
	fmt.Printf("  Node ID: %s\n", result.Config.NodeID)
	fmt.Printf("  Machine name: %s\n", result.Config.MachineName)
	fmt.Printf("  Mode: %s\n", result.Config.Mode)
	fmt.Printf("  Repo path: %s\n", result.Config.RepoPath)
	fmt.Printf("  State path: %s\n", result.Config.StatePath)
	fmt.Printf("  Default model: %s\n", result.Config.DefaultModel)
	fmt.Printf("  Task count: %d\n", result.TaskCount)
	fmt.Printf("  Run count: %d\n", result.RunCount)
	fmt.Println("  State directories:")
	for _, dir := range result.StateDirs {
		state := "ready"
		if !dir.Ready {
			state = "missing"
			if dir.Error != "" {
				state = dir.Error
			}
		}
		fmt.Printf("    - %s: %s\n", dir.Path, state)
	}
	fmt.Println("  Daemon: not installed/running in this foundation slice")
	return nil
}

func runSelfBuild(args []string) error {
	if len(args) == 0 || args[0] == "help" || args[0] == "--help" || args[0] == "-h" {
		fmt.Println(`Usage:
  karkhana self-build sample-task
  karkhana self-build run --task PATH_OR_ID [--model MODEL] [--dry-run] [--timeout DURATION]

Generate a deterministic local self-build task spec for the configured repo.
This command writes the task JSON under state/tasks and prints pure JSON to stdout.`)
		return nil
	}
	if args[0] == "run" {
		return runSelfBuildRun(args[1:])
	}
	if args[0] == "sample-task" && len(args) > 1 && isHelpArg(args[1]) {
		fmt.Println(`Usage:
  karkhana self-build sample-task

Generate a deterministic local self-build task spec and print pure JSON to stdout.
Diagnostics are written to stderr only.`)
		return nil
	}
	if args[0] != "sample-task" {
		return fmt.Errorf("unknown self-build command %q\n\nRun 'karkhana self-build help' for usage.", args[0])
	}
	if len(args) > 1 {
		return fmt.Errorf("unexpected self-build sample-task argument(s): %s", strings.Join(args[1:], " "))
	}
	cfgPath, err := config.ConfigFilePath()
	if err != nil {
		return err
	}
	cfg, err := config.LoadLocalConfig(cfgPath)
	if err != nil {
		return fmt.Errorf("load local config before generating sample task: %w (run 'karkhana init')", err)
	}
	data, path, err := selfbuild.WriteSampleTask(cfg)
	if err != nil {
		return err
	}
	fmt.Fprintf(os.Stderr, "Wrote sample self-build task: %s\n", path)
	_, err = os.Stdout.Write(data)
	return err
}

func runSelfBuildRun(args []string) error {
	flags := flag.NewFlagSet("self-build run", flag.ContinueOnError)
	flags.SetOutput(io.Discard)
	taskRef := flags.String("task", "", "task path or task id")
	model := flags.String("model", "", "OpenCode model override")
	dryRun := flags.Bool("dry-run", false, "prepare run metadata without executing OpenCode")
	timeout := flags.Duration("timeout", 15*time.Minute, "OpenCode execution timeout")
	if err := flags.Parse(args); err != nil {
		return err
	}
	if flags.NArg() > 0 {
		return fmt.Errorf("unexpected self-build run argument(s): %s", strings.Join(flags.Args(), " "))
	}
	if strings.TrimSpace(*taskRef) == "" {
		return fmt.Errorf("--task is required")
	}
	cfgPath, err := config.ConfigFilePath()
	if err != nil {
		return err
	}
	cfg, err := config.LoadLocalConfig(cfgPath)
	if err != nil {
		return fmt.Errorf("load local config before running self-build: %w (run 'karkhana init')", err)
	}
	result, err := selfbuild.RunTask(context.Background(), selfbuild.RunOptions{
		Config:  cfg,
		TaskRef: *taskRef,
		Model:   *model,
		DryRun:  *dryRun,
		Timeout: *timeout,
		Detect:  func(ctx context.Context) opencode.Info { return opencode.Detect(ctx, opencode.Options{}) },
	})
	if err != nil {
		return err
	}
	data, err := json.MarshalIndent(result.Record, "", "  ")
	if err != nil {
		return err
	}
	data = append(data, '\n')
	if _, err := os.Stdout.Write(data); err != nil {
		return err
	}
	if !*dryRun && strings.TrimSpace(result.Record.Error) != "" {
		return errors.New(result.Record.Error)
	}
	return nil
}

func printUsage() {
	fmt.Println(`Karkhana local node runtime

Usage:
	  karkhana version
	  karkhana init [--repo PATH] [--state PATH] [--machine-name NAME] [--force]
	  karkhana doctor
	  karkhana install --mode worker|master|master-worker
	  karkhana status
	  karkhana self-build sample-task
	  karkhana self-build run --task PATH_OR_ID [--model MODEL] [--dry-run] [--timeout DURATION]

This is additive scaffolding only. Real auth, OpenCode execution, daemon service
installation, and master lease behavior are intentionally not implemented yet.`)
}

func valueOrDash(value string) string {
	if strings.TrimSpace(value) == "" {
		return "-"
	}
	return value
}

func isHelpArg(arg string) bool {
	return arg == "help" || arg == "--help" || arg == "-h"
}
