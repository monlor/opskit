package config

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"
)

// Config represents the application configuration
type Config struct {
	Version           string `json:"version"`
	Dir               string `json:"dir"`
	Release           string `json:"release"`
	GithubRepo        string `json:"github_repo"`
	NoAutoUpdate      bool   `json:"no_auto_update"`
	UpdateInterval    int    `json:"update_interval"`
	Debug             bool   `json:"debug"`
	ForceRefresh      bool   `json:"force_refresh"`
	ToolsConfig       *ToolsConfig `json:"tools_config,omitempty"`
	DependenciesConfig *DependenciesConfig `json:"dependencies_config,omitempty"`
}

// ToolsConfig represents the tools configuration
type ToolsConfig struct {
	Version string `json:"version"`
	Tools   []Tool `json:"tools"`
}

// Tool represents a single tool configuration
type Tool struct {
	ID           string      `json:"id"`
	Name         string      `json:"name"`
	Description  string      `json:"description"`
	File         string      `json:"file"`
	Type         string      `json:"type"`        // "shell", "python", "go", "binary"
	Dependencies []string    `json:"dependencies"`
	Category     string      `json:"category"`
	Group        string      `json:"group"`       // Group for display organization
	Version      string      `json:"version"`
	Commands     []Command   `json:"commands"`   // Sub-commands
	Args         []Argument  `json:"args"`       // Global arguments
}

// Command represents a sub-command
type Command struct {
	Name        string     `json:"name"`
	Description string     `json:"description"`
	Args        []Argument `json:"args"`
	Flags       []Flag     `json:"flags"`
}

// Argument represents a command argument
type Argument struct {
	Name        string `json:"name"`
	Description string `json:"description"`
	Required    bool   `json:"required"`
	Default     string `json:"default"`
}

// Flag represents a command flag
type Flag struct {
	Name        string `json:"name"`
	Short       string `json:"short"`
	Description string `json:"description"`
	Type        string `json:"type"`    // "bool", "string", "int"
	Default     string `json:"default"`
}

// DependenciesConfig represents the dependencies configuration
type DependenciesConfig struct {
	Version      string                 `json:"version"`
	Dependencies map[string]Dependency `json:"dependencies"`
}

// Dependency represents a single dependency configuration
type Dependency struct {
	Description string            `json:"description"`
	Check       string            `json:"check"`
	Package     string            `json:"package,omitempty"`
	Packages    map[string]string `json:"packages,omitempty"`
	Docs        string            `json:"docs,omitempty"`
}

// DefaultConfig returns a default configuration
func DefaultConfig() *Config {
	homeDir, _ := os.UserHomeDir()
	return &Config{
		Version:        "1.0.0",
		Dir:            filepath.Join(homeDir, ".opskit"),
		Release:        getEnv("OPSKIT_RELEASE", "main"),
		GithubRepo:     getEnv("GITHUB_REPO", "https://raw.githubusercontent.com/monlor/opskit/main"),
		NoAutoUpdate:   getEnv("OPSKIT_NO_AUTO_UPDATE", "0") == "1",
		UpdateInterval: getEnvInt("OPSKIT_UPDATE_INTERVAL", 1),
		Debug:          getEnv("OPSKIT_DEBUG", "0") == "1",
		ForceRefresh:   getEnv("OPSKIT_FORCE_REFRESH", "0") == "1",
	}
}

// Load loads configuration from environment and files
func Load() (*Config, error) {
	cfg := DefaultConfig()
	
	// Ensure tools directory exists
	toolsDir := filepath.Join(cfg.Dir, "tools", cfg.Release)
	if err := os.MkdirAll(toolsDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create tools directory: %w", err)
	}
	
	return cfg, nil
}

// ToolsDir returns the tools directory path
func (c *Config) ToolsDir() string {
	return filepath.Join(c.Dir, "tools", c.Release)
}

// ShouldUpdate determines if a file should be updated based on version and age
func (c *Config) ShouldUpdate(filePath string) bool {
	// Always update if file doesn't exist
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		return true
	}

	// For release versions, don't auto-update
	if c.Release != "main" {
		return false
	}

	// For main version, check update settings
	if c.NoAutoUpdate {
		return false
	}

	// Check file age for main version
	if stat, err := os.Stat(filePath); err == nil {
		fileAge := time.Since(stat.ModTime())
		maxAge := time.Duration(c.UpdateInterval) * time.Hour
		return fileAge > maxAge
	}

	return false
}

// getEnv gets environment variable with default value
func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

// getEnvInt gets environment variable as integer with default value
func getEnvInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intValue, err := parseIntSafe(value); err == nil {
			return intValue
		}
	}
	return defaultValue
}

// parseIntSafe parses integer safely
func parseIntSafe(s string) (int, error) {
	var result int
	for _, r := range s {
		if r < '0' || r > '9' {
			return 0, fmt.Errorf("invalid integer: %s", s)
		}
		result = result*10 + int(r-'0')
	}
	return result, nil
}

// LoadToolsConfig loads tools configuration from JSON file
func LoadToolsConfig(filePath string) (*ToolsConfig, error) {
	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("failed to read tools config: %w", err)
	}

	var config ToolsConfig
	if err := json.Unmarshal(data, &config); err != nil {
		return nil, fmt.Errorf("failed to parse tools config: %w", err)
	}

	return &config, nil
}

// LoadDependenciesConfig loads dependencies configuration from JSON file
func LoadDependenciesConfig(filePath string) (*DependenciesConfig, error) {
	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("failed to read dependencies config: %w", err)
	}

	var config DependenciesConfig
	if err := json.Unmarshal(data, &config); err != nil {
		return nil, fmt.Errorf("failed to parse dependencies config: %w", err)
	}

	return &config, nil
}