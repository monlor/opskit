package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
	"opskit/internal/config"
	"opskit/internal/dynamic"
	"opskit/internal/logger"
	"opskit/internal/menu"
)

var (
	cfg *config.Config
	cfgFile string
	debug bool
)

// rootCmd represents the base command when called without any subcommands
var rootCmd = &cobra.Command{
	Use:   "opskit",
	Short: "Remote Operations Toolkit",
	Long: `OpsKit is a lightweight remote operations toolkit that provides
interactive menu operations and intelligent dependency management.

Features:
- Dynamic tool loading with lightweight main script
- Modular design with independent tool maintenance
- Intelligent dependency management with user confirmation
- Secure operations with multiple confirmation mechanisms`,
	RunE: func(cmd *cobra.Command, args []string) error {
		// If no subcommand is provided, run interactive menu
		return menu.RunInteractiveMenu(cfg)
	},
}

// Execute adds all child commands to the root command and sets flags appropriately.
func Execute(config *config.Config) error {
	cfg = config
	
	// Generate dynamic commands from tools configuration
	generator := dynamic.NewCommandGenerator(cfg)
	dynamicCommands, err := generator.GenerateCommands()
	if err != nil {
		logger.Warning("Failed to generate dynamic commands: %v", err)
		logger.Info("Continuing with basic functionality...")
	} else {
		// Add dynamic commands to root
		for _, cmd := range dynamicCommands {
			rootCmd.AddCommand(cmd)
		}
	}
	
	return rootCmd.Execute()
}

func init() {
	cobra.OnInitialize(initConfig)

	// Global flags
	rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "", "config file (default is $HOME/.opskit/config.yaml)")
	rootCmd.PersistentFlags().BoolVar(&debug, "debug", false, "enable debug mode")
	rootCmd.PersistentFlags().BoolP("version", "v", false, "show version information")
	
	// Bind version flag
	rootCmd.Flags().BoolP("version-info", "", false, "show detailed version information")
}

// initConfig reads in config file and ENV variables if set.
func initConfig() {
	if debug {
		os.Setenv("OPSKIT_DEBUG", "1")
		logger.Init()
	}
	
	// Handle version flag
	if versionFlag, _ := rootCmd.Flags().GetBool("version"); versionFlag {
		fmt.Printf("OpsKit version %s\n", cfg.Version)
		os.Exit(0)
	}
	
	// Handle version-info flag
	if versionInfoFlag, _ := rootCmd.Flags().GetBool("version-info"); versionInfoFlag {
		showVersionInfo()
		os.Exit(0)
	}
}

// showVersionInfo displays detailed version information
func showVersionInfo() {
	fmt.Printf("OpsKit - Remote Operations Toolkit\n")
	fmt.Printf("Version: %s\n", cfg.Version)
	fmt.Printf("Release: %s\n", cfg.Release)
	fmt.Printf("Config Dir: %s\n", cfg.Dir)
	fmt.Printf("Tools Dir: %s\n", cfg.ToolsDir())
	fmt.Printf("GitHub Repo: %s\n", cfg.GithubRepo)
	fmt.Printf("Auto Update: %t\n", !cfg.NoAutoUpdate)
	fmt.Printf("Update Interval: %d hours\n", cfg.UpdateInterval)
	fmt.Printf("Debug Mode: %t\n", cfg.Debug)
}