package main

import (
	"bytes"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
)

func TestMainHelp(t *testing.T) {
	// Build the binary
	cmd := exec.Command("go", "build", "-o", "opskit-test", ".")
	if err := cmd.Run(); err != nil {
		t.Fatalf("Failed to build binary: %v", err)
	}
	defer os.Remove("opskit-test")

	// Run with --help
	cmd = exec.Command("./opskit-test", "--help")
	var stdout bytes.Buffer
	cmd.Stdout = &stdout
	
	if err := cmd.Run(); err != nil {
		t.Fatalf("Failed to run binary with --help: %v", err)
	}
	
	output := stdout.String()
	if !bytes.Contains([]byte(output), []byte("OpsKit is a lightweight remote operations toolkit")) {
		t.Error("Expected help output to contain description")
	}
	
	if !bytes.Contains([]byte(output), []byte("Available Commands:")) {
		t.Error("Expected help output to contain available commands")
	}
}

func TestMainVersion(t *testing.T) {
	// Build the binary
	cmd := exec.Command("go", "build", "-o", "opskit-test", ".")
	if err := cmd.Run(); err != nil {
		t.Fatalf("Failed to build binary: %v", err)
	}
	defer os.Remove("opskit-test")

	// Run with --version-info
	cmd = exec.Command("./opskit-test", "--version-info")
	var stdout bytes.Buffer
	cmd.Stdout = &stdout
	
	if err := cmd.Run(); err != nil {
		t.Fatalf("Failed to run binary with --version-info: %v", err)
	}
	
	output := stdout.String()
	if !bytes.Contains([]byte(output), []byte("OpsKit - Remote Operations Toolkit")) {
		t.Error("Expected version output to contain toolkit name")
	}
	
	if !bytes.Contains([]byte(output), []byte("Version:")) {
		t.Error("Expected version output to contain version info")
	}
}

func TestMainListTools(t *testing.T) {
	// Build the binary
	cmd := exec.Command("go", "build", "-o", "opskit-test", ".")
	if err := cmd.Run(); err != nil {
		t.Fatalf("Failed to build binary: %v", err)
	}
	defer os.Remove("opskit-test")

	// Run with list command
	cmd = exec.Command("./opskit-test", "list")
	var stdout bytes.Buffer
	cmd.Stdout = &stdout
	
	if err := cmd.Run(); err != nil {
		t.Fatalf("Failed to run binary with list: %v", err)
	}
	
	output := stdout.String()
	// Should contain at least some tools from our config
	if !bytes.Contains([]byte(output), []byte("DATABASE:")) && !bytes.Contains([]byte(output), []byte("STORAGE:")) && !bytes.Contains([]byte(output), []byte("TESTING:")) {
		t.Error("Expected list output to contain tool categories")
	}
}

func TestMainWithLocalConfig(t *testing.T) {
	// Create temporary directory for test
	tmpDir := t.TempDir()
	oldWd, _ := os.Getwd()
	defer os.Chdir(oldWd)
	
	// Copy binary to temp directory
	cmd := exec.Command("go", "build", "-o", filepath.Join(tmpDir, "opskit-test"), ".")
	if err := cmd.Run(); err != nil {
		t.Fatalf("Failed to build binary: %v", err)
	}
	
	// Copy tools config to temp directory  
	toolsDir := filepath.Join(tmpDir, "tools")
	if err := os.MkdirAll(toolsDir, 0755); err != nil {
		t.Fatalf("Failed to create tools directory: %v", err)
	}
	
	// Copy tools.json
	if err := copyFile("tools/tools.json", filepath.Join(toolsDir, "tools.json")); err != nil {
		t.Fatalf("Failed to copy tools.json: %v", err)
	}
	
	// Create a simple test script
	testScript := `#!/bin/bash
echo "Test script executed successfully"
echo "Command: $1"
echo "Args: $@"
`
	if err := os.WriteFile(filepath.Join(toolsDir, "test.sh"), []byte(testScript), 0755); err != nil {
		t.Fatalf("Failed to create test script: %v", err)
	}
	
	// Change to temp directory and run binary
	os.Chdir(tmpDir)
	cmd = exec.Command("./opskit-test", "--help")
	var stdout bytes.Buffer
	cmd.Stdout = &stdout
	
	if err := cmd.Run(); err != nil {
		t.Fatalf("Failed to run binary in temp directory: %v", err)
	}
	
	output := stdout.String()
	if !bytes.Contains([]byte(output), []byte("Available Commands:")) {
		t.Error("Expected help output to contain available commands")
	}
}

// Helper function to copy files
func copyFile(src, dst string) error {
	data, err := os.ReadFile(src)
	if err != nil {
		return err
	}
	return os.WriteFile(dst, data, 0644)
}