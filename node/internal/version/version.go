// Package version contains build-time version metadata for the Karkhana CLI.
package version

import "fmt"

var (
	// AppName is the user-facing command name.
	AppName = "karkhana"
	// Version is the semantic version for this foundation scaffold.
	Version = "0.1.0"
	// Commit can be injected at build time with -ldflags "-X ...Commit=<sha>".
	Commit = "dev"
	// Date can be injected at build time with -ldflags "-X ...Date=<date>".
	Date = "unknown"
)

// Info returns the printable version string.
func Info() string {
	return fmt.Sprintf("%s version %s (commit %s, built %s)", AppName, Version, Commit, Date)
}
