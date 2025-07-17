package cmd

import (
	"fmt"
	"os"
	"os/exec"

	"github.com/spf13/cobra"
	"opskit/internal/config"
	"opskit/internal/dependencies"
	"opskit/internal/downloader"
	"opskit/internal/logger"
)

// runCmd represents the run command
var runCmd = &cobra.Command{
	Use:   "run <tool-id>",
	Short: "Run a specific tool",
	Long: `Run a specific tool by its ID.

Examples:
  opskit run mysql-sync    # Run MySQL sync tool
  opskit run s3-sync       # Run S3 sync tool
  opskit run --list        # List available tools`,
	Args: cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		listFlag, _ := cmd.Flags().GetBool("list")
		if listFlag {
			return listTools("", false)
		}
		
		if len(args) == 0 {
			return fmt.Errorf("tool ID is required")
		}
		
		return runTool(args[0])
	},
}

func init() {
	rootCmd.AddCommand(runCmd)
	
	runCmd.Flags().Bool("list", false, "list available tools")
}

func runTool(toolID string) error {
	logger.Info("Running tool: %s", toolID)
	
	// Load tools configuration
	dl := downloader.NewDownloader(cfg)
	toolsConfigPath, err := dl.LoadOrDownloadConfig("tools.json")
	if err != nil {
		return fmt.Errorf("failed to load tools config: %w", err)
	}
	
	toolsConfig, err := config.LoadToolsConfig(toolsConfigPath)
	if err != nil {
		return fmt.Errorf("failed to parse tools config: %w", err)
	}
	
	// Find tool
	var tool *config.Tool
	for _, t := range toolsConfig.Tools {
		if t.ID == toolID {
			tool = &t
			break
		}
	}
	
	if tool == nil {
		return fmt.Errorf("tool not found: %s", toolID)
	}
	
	// Load dependencies configuration
	depsConfigPath, err := dl.LoadOrDownloadConfig("dependencies.json")
	if err != nil {
		return fmt.Errorf("failed to load dependencies config: %w", err)
	}
	
	depsConfig, err := config.LoadDependenciesConfig(depsConfigPath)
	if err != nil {
		return fmt.Errorf("failed to parse dependencies config: %w", err)
	}
	
	// Check dependencies
	if len(tool.Dependencies) > 0 {
		depManager := dependencies.NewManager(cfg, depsConfig)
		if err := depManager.CheckDependencies(tool.Dependencies); err != nil {
			return fmt.Errorf("dependency check failed: %w", err)
		}
	}
	
	// Download tool
	toolPath, err := dl.LoadOrDownloadTool(tool.File)
	if err != nil {
		return fmt.Errorf("failed to load tool: %w", err)
	}
	
	// Execute tool
	logger.Info("Executing %s...", tool.Name)
	cmd := exec.Command("/bin/bash", toolPath)
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	
	// Set environment variables
	cmd.Env = append(os.Environ(),
		fmt.Sprintf("OPSKIT_VERSION=%s", cfg.Version),
		fmt.Sprintf("OPSKIT_DIR=%s", cfg.Dir),
		fmt.Sprintf("OPSKIT_TOOLS_DIR=%s", cfg.ToolsDir()),
		fmt.Sprintf("GITHUB_REPO=%s", cfg.GithubRepo),
		fmt.Sprintf("OPSKIT_RELEASE=%s", cfg.Release),
	)
	
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("tool execution failed: %w", err)
	}
	
	logger.Success("Tool %s completed successfully", tool.Name)
	return nil
}