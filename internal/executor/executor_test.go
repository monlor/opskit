package executor

import (
	"os"
	"path/filepath"
	"testing"

	"opskit/internal/config"
)

func TestNewExecutor(t *testing.T) {
	cfg := &config.Config{
		Dir:     "/tmp/test",
		Release: "main",
		Debug:   true,
	}
	
	executor := NewExecutor(cfg)
	if executor == nil {
		t.Fatal("Expected executor to be created")
	}
	
	if executor.cfg != cfg {
		t.Error("Expected executor to have correct config")
	}
}

func TestBuildCommandArgs(t *testing.T) {
	cfg := &config.Config{}
	executor := NewExecutor(cfg)
	
	tool := &config.Tool{
		ID:   "test-tool",
		Type: "shell",
	}
	
	tests := []struct {
		name     string
		command  string
		args     []string
		flags    map[string]interface{}
		expected []string
	}{
		{
			name:     "simple command",
			command:  "test",
			args:     []string{"arg1", "arg2"},
			flags:    map[string]interface{}{},
			expected: []string{"test", "arg1", "arg2"},
		},
		{
			name:    "with bool flag",
			command: "test",
			args:    []string{},
			flags: map[string]interface{}{
				"dry-run": true,
				"verbose": false,
			},
			expected: []string{"test", "--dry-run"},
		},
		{
			name:    "with string flag",
			command: "test",
			args:    []string{},
			flags: map[string]interface{}{
				"output": "file.txt",
			},
			expected: []string{"test", "--output", "file.txt"},
		},
		{
			name:    "skip global flags",
			command: "test",
			args:    []string{},
			flags: map[string]interface{}{
				"debug":   true,
				"config":  "config.yaml",
				"version": true,
				"dry-run": true,
			},
			expected: []string{"test", "--dry-run"},
		},
		{
			name:    "short flags",
			command: "test",
			args:    []string{},
			flags: map[string]interface{}{
				"v": true,
				"f": "file.txt",
			},
			expected: []string{"test", "-v", "-f", "file.txt"},
		},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := executor.buildCommandArgs(tool, tt.command, tt.args, tt.flags)
			if err != nil {
				t.Fatalf("buildCommandArgs failed: %v", err)
			}
			
			if len(result) != len(tt.expected) {
				t.Errorf("Expected %d args, got %d. Expected: %v, Got: %v", 
					len(tt.expected), len(result), tt.expected, result)
				return
			}
			
			for i, arg := range result {
				if arg != tt.expected[i] {
					t.Errorf("Expected arg[%d] = %s, got %s", i, tt.expected[i], arg)
				}
			}
		})
	}
}

func TestFileExists(t *testing.T) {
	cfg := &config.Config{}
	executor := NewExecutor(cfg)
	
	// Create temporary file
	tmpDir := t.TempDir()
	tmpFile := filepath.Join(tmpDir, "test.txt")
	if err := os.WriteFile(tmpFile, []byte("test"), 0644); err != nil {
		t.Fatalf("Failed to create temp file: %v", err)
	}
	
	// Test existing file
	if !executor.fileExists(tmpFile) {
		t.Error("Expected true for existing file")
	}
	
	// Test non-existing file
	if executor.fileExists(filepath.Join(tmpDir, "nonexistent.txt")) {
		t.Error("Expected false for non-existing file")
	}
}

func TestFindToolFile(t *testing.T) {
	// Change to temp directory for test
	oldWd, _ := os.Getwd()
	tmpDir := t.TempDir()
	os.Chdir(tmpDir)
	defer os.Chdir(oldWd)
	
	cfg := &config.Config{
		Dir:          tmpDir,
		Release:      "main",
		NoAutoUpdate: true, // Prevent network requests during tests
	}
	executor := NewExecutor(cfg)
	
	// Create tools directory
	toolsDir := cfg.ToolsDir()
	if err := os.MkdirAll(toolsDir, 0755); err != nil {
		t.Fatalf("Failed to create tools directory: %v", err)
	}
	
	tool := &config.Tool{
		ID:   "test-tool",
		File: "test.sh",
		Type: "shell",
	}
	
	// Test 1: Local file exists (priority 1)
	localFile := filepath.Join("tools", tool.File)
	if err := os.MkdirAll(filepath.Dir(localFile), 0755); err != nil {
		t.Fatalf("Failed to create local tools directory: %v", err)
	}
	if err := os.WriteFile(localFile, []byte("#!/bin/bash\necho local"), 0755); err != nil {
		t.Fatalf("Failed to create local file: %v", err)
	}
	
	result, err := executor.findToolFile(tool)
	if err != nil {
		t.Fatalf("findToolFile failed: %v", err)
	}
	
	if result != localFile {
		t.Errorf("Expected local file %s, got %s", localFile, result)
	}
	
	// Test 2: Remove local file, create cached file (should use cached since no network)
	if err := os.Remove(localFile); err != nil {
		t.Fatalf("Failed to remove local file: %v", err)
	}
	
	cachedFile := filepath.Join(toolsDir, tool.File)
	if err := os.WriteFile(cachedFile, []byte("#!/bin/bash\necho cached"), 0755); err != nil {
		t.Fatalf("Failed to create cached file: %v", err)
	}
	
	result, err = executor.findToolFile(tool)
	if err != nil {
		t.Fatalf("findToolFile failed: %v", err)
	}
	
	if result != cachedFile {
		t.Errorf("Expected cached file %s, got %s", cachedFile, result)
	}
	
	// Test 3: Both files missing - should attempt download and fail (expected for test)
	if err := os.Remove(cachedFile); err != nil {
		t.Fatalf("Failed to remove cached file: %v", err)
	}
	
	_, err = executor.findToolFile(tool)
	if err == nil {
		t.Error("Expected error when file download fails")
	}
}