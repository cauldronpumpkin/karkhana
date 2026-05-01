// Package install contains safe install-mode validation and stubs.
package install

import "fmt"

// Supported node runtime modes.
const (
	ModeWorker       = "worker"
	ModeMaster       = "master"
	ModeMasterWorker = "master-worker"
)

// ValidateMode checks whether mode is a supported future node mode.
func ValidateMode(mode string) error {
	switch mode {
	case ModeWorker, ModeMaster, ModeMasterWorker:
		return nil
	default:
		return fmt.Errorf("invalid mode %q: expected one of %s, %s, %s", mode, ModeWorker, ModeMaster, ModeMasterWorker)
	}
}
