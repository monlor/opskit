package executor

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"opskit/internal/config"
	"opskit/internal/logger"
)

// Executor handles dynamic tool execution
type Executor struct {
	cfg *config.Config
}

// NewExecutor creates a new executor
func NewExecutor(cfg *config.Config) *Executor {
	return &Executor{cfg: cfg}
}

// ExecuteTool executes a tool with given command and arguments
func (e *Executor) ExecuteTool(tool *config.Tool, command string, args []string, flags map[string]interface{}) error {
	logger.Debug("Executing tool: %s, command: %s", tool.ID, command)

	// Find the tool file
	toolPath, err := e.findToolFile(tool)
	if err != nil {
		return fmt.Errorf("failed to find tool file: %w", err)
	}

	// Build command arguments
	cmdArgs, err := e.buildCommandArgs(tool, command, args, flags)
	if err != nil {
		return fmt.Errorf("failed to build command arguments: %w", err)
	}

	// Execute based on tool type
	switch tool.Type {
	case "shell":
		return e.executeShell(toolPath, cmdArgs)
	case "python":
		return e.executePython(toolPath, cmdArgs)
	case "go":
		return e.executeGo(toolPath, cmdArgs)
	case "binary":
		return e.executeBinary(toolPath, cmdArgs)
	default:
		return fmt.Errorf("unsupported tool type: %s", tool.Type)
	}
}

// findToolFile finds the tool file in various locations
func (e *Executor) findToolFile(tool *config.Tool) (string, error) {
	// Priority 1: Current directory (development mode)
	if currentPath := filepath.Join(".", "tools", tool.File); e.fileExists(currentPath) {
		logger.Debug("Using local tool file: %s", currentPath)
		return currentPath, nil
	}

	// Priority 2: Cached file
	cachedPath := filepath.Join(e.cfg.ToolsDir(), tool.File)
	if e.fileExists(cachedPath) && !e.cfg.ShouldUpdate(cachedPath) {
		logger.Debug("Using cached tool file: %s", cachedPath)
		return cachedPath, nil
	}

	// Priority 3: Download from remote
	logger.Info("Downloading tool file: %s", tool.File)
	return e.downloadToolFile(tool)
}

// downloadToolFile downloads a tool file from remote repository
func (e *Executor) downloadToolFile(tool *config.Tool) (string, error) {
	url := fmt.Sprintf("%s/tools/%s", e.cfg.GithubRepo, tool.File)
	outputPath := filepath.Join(e.cfg.ToolsDir(), tool.File)

	// Create directory if it doesn't exist
	if err := os.MkdirAll(filepath.Dir(outputPath), 0755); err != nil {
		return "", fmt.Errorf("failed to create directory: %w", err)
	}

	// Download file
	cmd := exec.Command("curl", "-sSL", "-o", outputPath, url)
	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("failed to download tool file: %w", err)
	}

	// Make executable if it's a script
	if tool.Type == "shell" || tool.Type == "python" {
		if err := os.Chmod(outputPath, 0755); err != nil {
			return "", fmt.Errorf("failed to make file executable: %w", err)
		}
	}

	logger.Success("Downloaded tool file: %s", outputPath)
	return outputPath, nil
}

// buildCommandArgs builds command arguments based on tool configuration
func (e *Executor) buildCommandArgs(tool *config.Tool, command string, args []string, flags map[string]interface{}) ([]string, error) {
	var cmdArgs []string

	// Add command if specified
	if command != "" {
		cmdArgs = append(cmdArgs, command)
	}

	// Add arguments
	cmdArgs = append(cmdArgs, args...)

	// Add flags (only tool-specific flags, not global ones)
	for flagName, flagValue := range flags {
		// Skip global flags that shouldn't be passed to tools
		if flagName == "debug" || flagName == "config" || flagName == "version" {
			continue
		}
		
		switch v := flagValue.(type) {
		case bool:
			if v {
				if len(flagName) == 1 {
					cmdArgs = append(cmdArgs, fmt.Sprintf("-%s", flagName))
				} else {
					cmdArgs = append(cmdArgs, fmt.Sprintf("--%s", flagName))
				}
			}
		case string:
			if v != "" {
				if len(flagName) == 1 {
					cmdArgs = append(cmdArgs, fmt.Sprintf("-%s", flagName), v)
				} else {
					cmdArgs = append(cmdArgs, fmt.Sprintf("--%s", flagName), v)
				}
			}
		}
	}

	return cmdArgs, nil
}

// executeShell executes a shell script
func (e *Executor) executeShell(scriptPath string, args []string) error {
	logger.Debug("Executing shell script: %s with args: %v", scriptPath, args)
	
	cmd := exec.Command("bash", append([]string{scriptPath}, args...)...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin
	
	// Set environment variables
	cmd.Env = append(os.Environ(),
		fmt.Sprintf("OPSKIT_DIR=%s", e.cfg.Dir),
		fmt.Sprintf("OPSKIT_DEBUG=%t", e.cfg.Debug),
		fmt.Sprintf("OPSKIT_RELEASE=%s", e.cfg.Release),
	)
	
	return cmd.Run()
}

// executePython executes a Python script
func (e *Executor) executePython(scriptPath string, args []string) error {
	logger.Debug("Executing Python script: %s with args: %v", scriptPath, args)
	
	cmd := exec.Command("python3", append([]string{scriptPath}, args...)...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin
	
	// Set environment variables
	cmd.Env = append(os.Environ(),
		fmt.Sprintf("OPSKIT_DIR=%s", e.cfg.Dir),
		fmt.Sprintf("OPSKIT_DEBUG=%t", e.cfg.Debug),
		fmt.Sprintf("OPSKIT_RELEASE=%s", e.cfg.Release),
	)
	
	return cmd.Run()
}

// executeGo executes a Go program
func (e *Executor) executeGo(scriptPath string, args []string) error {
	logger.Debug("Executing Go program: %s with args: %v", scriptPath, args)
	
	// For Go files, we need to run them with 'go run'
	if strings.HasSuffix(scriptPath, ".go") {
		cmd := exec.Command("go", append([]string{"run", scriptPath}, args...)...)
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		cmd.Stdin = os.Stdin
		
		// Set environment variables
		cmd.Env = append(os.Environ(),
			fmt.Sprintf("OPSKIT_DIR=%s", e.cfg.Dir),
			fmt.Sprintf("OPSKIT_DEBUG=%t", e.cfg.Debug),
			fmt.Sprintf("OPSKIT_RELEASE=%s", e.cfg.Release),
		)
		
		return cmd.Run()
	}
	
	// For compiled binaries
	return e.executeBinary(scriptPath, args)
}

// executeBinary executes a binary file
func (e *Executor) executeBinary(binaryPath string, args []string) error {
	logger.Debug("Executing binary: %s with args: %v", binaryPath, args)
	
	cmd := exec.Command(binaryPath, args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin
	
	// Set environment variables
	cmd.Env = append(os.Environ(),
		fmt.Sprintf("OPSKIT_DIR=%s", e.cfg.Dir),
		fmt.Sprintf("OPSKIT_DEBUG=%t", e.cfg.Debug),
		fmt.Sprintf("OPSKIT_RELEASE=%s", e.cfg.Release),
	)
	
	return cmd.Run()
}

// fileExists checks if a file exists
func (e *Executor) fileExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}