package config

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestDefaultConfig(t *testing.T) {
	cfg := DefaultConfig()
	
	if cfg.Version != "1.0.0" {
		t.Errorf("Expected version 1.0.0, got %s", cfg.Version)
	}
	
	if cfg.Release != "main" {
		t.Errorf("Expected release main, got %s", cfg.Release)
	}
	
	if cfg.UpdateInterval != 1 {
		t.Errorf("Expected update interval 1, got %d", cfg.UpdateInterval)
	}
}

func TestLoadConfig(t *testing.T) {
	cfg, err := Load()
	if err != nil {
		t.Fatalf("Failed to load config: %v", err)
	}
	
	if cfg == nil {
		t.Fatal("Config is nil")
	}
	
	// Check if tools directory was created
	if _, err := os.Stat(cfg.ToolsDir()); os.IsNotExist(err) {
		t.Errorf("Tools directory was not created: %s", cfg.ToolsDir())
	}
}

func TestShouldUpdate(t *testing.T) {
	cfg := DefaultConfig()
	
	// Non-existent file should always update
	if !cfg.ShouldUpdate("/non/existent/file") {
		t.Error("Expected true for non-existent file")
	}
	
	// Create temporary file
	tmpDir := t.TempDir()
	tmpFile := filepath.Join(tmpDir, "test.json")
	if err := os.WriteFile(tmpFile, []byte("{}"), 0644); err != nil {
		t.Fatalf("Failed to create temp file: %v", err)
	}
	
	// For release versions, should not update
	cfg.Release = "v1.0.0"
	if cfg.ShouldUpdate(tmpFile) {
		t.Error("Expected false for release version")
	}
	
	// For main with NoAutoUpdate, should not update
	cfg.Release = "main"
	cfg.NoAutoUpdate = true
	if cfg.ShouldUpdate(tmpFile) {
		t.Error("Expected false when NoAutoUpdate is true")
	}
}

func TestLoadToolsConfig(t *testing.T) {
	tmpDir := t.TempDir()
	configFile := filepath.Join(tmpDir, "tools.json")
	
	// Create test config
	testConfig := ToolsConfig{
		Version: "1.0.0",
		Tools: []Tool{
			{
				ID:          "test-tool",
				Name:        "Test Tool",
				Description: "A test tool",
				File:        "test.sh",
				Type:        "shell",
				Category:    "testing",
				Version:     "1.0.0",
			},
		},
	}
	
	data, err := json.MarshalIndent(testConfig, "", "  ")
	if err != nil {
		t.Fatalf("Failed to marshal config: %v", err)
	}
	
	if err := os.WriteFile(configFile, data, 0644); err != nil {
		t.Fatalf("Failed to write config file: %v", err)
	}
	
	// Load config
	config, err := LoadToolsConfig(configFile)
	if err != nil {
		t.Fatalf("Failed to load tools config: %v", err)
	}
	
	if config.Version != "1.0.0" {
		t.Errorf("Expected version 1.0.0, got %s", config.Version)
	}
	
	if len(config.Tools) != 1 {
		t.Errorf("Expected 1 tool, got %d", len(config.Tools))
	}
	
	tool := config.Tools[0]
	if tool.ID != "test-tool" {
		t.Errorf("Expected tool ID test-tool, got %s", tool.ID)
	}
}

func TestLoadDependenciesConfig(t *testing.T) {
	tmpDir := t.TempDir()
	configFile := filepath.Join(tmpDir, "deps.json")
	
	// Create test config
	testConfig := DependenciesConfig{
		Version: "1.0.0",
		Dependencies: map[string]Dependency{
			"curl": {
				Description: "HTTP client",
				Check:       "curl --version",
				Package:     "curl",
			},
			"mysql": {
				Description: "MySQL client",
				Check:       "mysql --version",
				Packages: map[string]string{
					"apt":  "mysql-client",
					"brew": "mysql-client",
				},
			},
		},
	}
	
	data, err := json.MarshalIndent(testConfig, "", "  ")
	if err != nil {
		t.Fatalf("Failed to marshal config: %v", err)
	}
	
	if err := os.WriteFile(configFile, data, 0644); err != nil {
		t.Fatalf("Failed to write config file: %v", err)
	}
	
	// Load config
	config, err := LoadDependenciesConfig(configFile)
	if err != nil {
		t.Fatalf("Failed to load dependencies config: %v", err)
	}
	
	if config.Version != "1.0.0" {
		t.Errorf("Expected version 1.0.0, got %s", config.Version)
	}
	
	if len(config.Dependencies) != 2 {
		t.Errorf("Expected 2 dependencies, got %d", len(config.Dependencies))
	}
	
	// Check curl dependency
	curl, exists := config.Dependencies["curl"]
	if !exists {
		t.Error("Expected curl dependency to exist")
	}
	if curl.Package != "curl" {
		t.Errorf("Expected curl package name curl, got %s", curl.Package)
	}
	
	// Check mysql dependency
	mysql, exists := config.Dependencies["mysql"]
	if !exists {
		t.Error("Expected mysql dependency to exist")
	}
	if mysql.Packages["apt"] != "mysql-client" {
		t.Errorf("Expected mysql apt package mysql-client, got %s", mysql.Packages["apt"])
	}
}