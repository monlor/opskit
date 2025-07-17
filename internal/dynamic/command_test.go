package dynamic

import (
	"testing"

	"github.com/spf13/cobra"
	"opskit/internal/config"
)

func TestNewCommandGenerator(t *testing.T) {
	cfg := &config.Config{
		Dir:     "/tmp/test",
		Release: "main",
	}
	
	generator := NewCommandGenerator(cfg)
	if generator == nil {
		t.Fatal("Expected generator to be created")
	}
	
	if generator.cfg != cfg {
		t.Error("Expected generator to have correct config")
	}
}

func TestValidateArgs(t *testing.T) {
	cfg := &config.Config{}
	generator := NewCommandGenerator(cfg)
	
	tests := []struct {
		name     string
		argDefs  []config.Argument
		args     []string
		hasError bool
	}{
		{
			name:     "no args required, none provided",
			argDefs:  []config.Argument{},
			args:     []string{},
			hasError: false,
		},
		{
			name: "one required arg, provided",
			argDefs: []config.Argument{
				{Name: "input", Required: true},
			},
			args:     []string{"test.txt"},
			hasError: false,
		},
		{
			name: "one required arg, not provided",
			argDefs: []config.Argument{
				{Name: "input", Required: true},
			},
			args:     []string{},
			hasError: true,
		},
		{
			name: "mixed required and optional args",
			argDefs: []config.Argument{
				{Name: "input", Required: true},
				{Name: "output", Required: false},
			},
			args:     []string{"input.txt"},
			hasError: false,
		},
		{
			name: "more args than required",
			argDefs: []config.Argument{
				{Name: "input", Required: true},
			},
			args:     []string{"input.txt", "extra.txt"},
			hasError: false,
		},
		{
			name: "multiple required args",
			argDefs: []config.Argument{
				{Name: "source", Required: true},
				{Name: "target", Required: true},
			},
			args:     []string{"src.txt", "dest.txt"},
			hasError: false,
		},
		{
			name: "multiple required args, insufficient",
			argDefs: []config.Argument{
				{Name: "source", Required: true},
				{Name: "target", Required: true},
			},
			args:     []string{"src.txt"},
			hasError: true,
		},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := generator.validateArgs(tt.argDefs, tt.args)
			
			if tt.hasError && err == nil {
				t.Error("Expected error but got none")
			}
			
			if !tt.hasError && err != nil {
				t.Errorf("Expected no error but got: %v", err)
			}
		})
	}
}

func TestFileExists(t *testing.T) {
	cfg := &config.Config{}
	generator := NewCommandGenerator(cfg)
	
	// Test with existing file
	if !generator.fileExists("command_test.go") {
		t.Error("Expected true for existing file")
	}
	
	// Test with non-existing file
	if generator.fileExists("nonexistent.go") {
		t.Error("Expected false for non-existing file")
	}
}

func TestGenerateToolCommand(t *testing.T) {
	cfg := &config.Config{
		Dir:     "/tmp/test",
		Release: "main",
	}
	generator := NewCommandGenerator(cfg)
	
	// Test tool with sub-commands
	tool := &config.Tool{
		ID:          "test-tool",
		Name:        "Test Tool",
		Description: "A test tool",
		File:        "test.sh",
		Type:        "shell",
		Commands: []config.Command{
			{
				Name:        "run",
				Description: "Run the tool",
				Args: []config.Argument{
					{Name: "input", Required: true},
				},
				Flags: []config.Flag{
					{Name: "dry-run", Type: "bool"},
				},
			},
		},
	}
	
	cmd := generator.generateToolCommand(tool)
	if cmd == nil {
		t.Fatal("Expected command to be generated")
	}
	
	if cmd.Use != "test-tool" {
		t.Errorf("Expected Use='test-tool', got %s", cmd.Use)
	}
	
	if cmd.Short != "Test Tool" {
		t.Errorf("Expected Short='Test Tool', got %s", cmd.Short)
	}
	
	if cmd.Long != "A test tool" {
		t.Errorf("Expected Long='A test tool', got %s", cmd.Long)
	}
	
	// Check if sub-commands were added
	if len(cmd.Commands()) == 0 {
		t.Error("Expected sub-commands to be added")
	}
	
	// Find the 'run' sub-command
	var runCmd *cobra.Command
	for _, subCmd := range cmd.Commands() {
		if subCmd.Use == "run <input>" {
			runCmd = subCmd
			break
		}
	}
	
	if runCmd == nil {
		t.Error("Expected 'run' sub-command to be found")
	}
}

func TestGenerateSubCommand(t *testing.T) {
	cfg := &config.Config{}
	generator := NewCommandGenerator(cfg)
	
	tool := &config.Tool{
		ID:   "test-tool",
		Type: "shell",
	}
	
	command := &config.Command{
		Name:        "sync",
		Description: "Synchronize data",
		Args: []config.Argument{
			{Name: "source", Required: true},
			{Name: "target", Required: true},
		},
		Flags: []config.Flag{
			{Name: "dry-run", Short: "n", Type: "bool"},
			{Name: "verbose", Short: "v", Type: "bool"},
		},
	}
	
	cmd := generator.generateSubCommand(tool, command)
	if cmd == nil {
		t.Fatal("Expected sub-command to be generated")
	}
	
	if cmd.Use != "sync <source> <target>" {
		t.Errorf("Expected Use='sync <source> <target>', got %s", cmd.Use)
	}
	
	if cmd.Short != "Synchronize data" {
		t.Errorf("Expected Short='Synchronize data', got %s", cmd.Short)
	}
	
	// Check if flags were added
	if cmd.Flags().ShorthandLookup("n") == nil {
		t.Error("Expected short flag 'n' to be added")
	}
	
	if cmd.Flags().ShorthandLookup("v") == nil {
		t.Error("Expected short flag 'v' to be added")
	}
}