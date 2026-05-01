package install

import "testing"

func TestValidateMode(t *testing.T) {
	tests := []struct {
		name    string
		mode    string
		wantErr bool
	}{
		{name: "worker", mode: ModeWorker},
		{name: "master", mode: ModeMaster},
		{name: "master worker", mode: ModeMasterWorker},
		{name: "empty", mode: "", wantErr: true},
		{name: "unknown", mode: "daemon", wantErr: true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := ValidateMode(tt.mode)
			if tt.wantErr && err == nil {
				t.Fatal("expected error, got nil")
			}
			if !tt.wantErr && err != nil {
				t.Fatalf("expected nil error, got %v", err)
			}
		})
	}
}
