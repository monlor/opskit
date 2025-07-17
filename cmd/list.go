package cmd

import (
	"fmt"
	"strings"

	"github.com/spf13/cobra"
	"opskit/internal/config"
	"opskit/internal/downloader"
	"opskit/internal/logger"
)

// listCmd represents the list command
var listCmd = &cobra.Command{
	Use:   "list",
	Short: "List available tools",
	Long: `List all available tools with their descriptions and categories.

Examples:
  opskit list                    # List all tools
  opskit list --category storage # List tools in storage category
  opskit list --verbose          # List with detailed information`,
	RunE: func(cmd *cobra.Command, args []string) error {
		category, _ := cmd.Flags().GetString("category")
		verbose, _ := cmd.Flags().GetBool("verbose")
		
		return listTools(category, verbose)
	},
}

func init() {
	rootCmd.AddCommand(listCmd)
	
	listCmd.Flags().StringP("category", "c", "", "filter by category")
	listCmd.Flags().Bool("verbose", false, "show detailed information")
}

func listTools(category string, verbose bool) error {
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
	
	// Load dependencies configuration
	depsConfigPath, err := dl.LoadOrDownloadConfig("dependencies.json")
	if err != nil {
		return fmt.Errorf("failed to load dependencies config: %w", err)
	}
	
	depsConfig, err := config.LoadDependenciesConfig(depsConfigPath)
	if err != nil {
		return fmt.Errorf("failed to parse dependencies config: %w", err)
	}
	
	// Filter tools by category if specified
	var filteredTools []config.Tool
	for _, tool := range toolsConfig.Tools {
		if category == "" || tool.Category == category {
			filteredTools = append(filteredTools, tool)
		}
	}
	
	if len(filteredTools) == 0 {
		if category != "" {
			logger.Info("No tools found in category: %s", category)
		} else {
			logger.Info("No tools available")
		}
		return nil
	}
	
	// Group tools by category
	categories := make(map[string][]config.Tool)
	for _, tool := range filteredTools {
		categories[tool.Category] = append(categories[tool.Category], tool)
	}
	
	// Display tools
	for cat, tools := range categories {
		if category == "" {
			fmt.Printf("\n%s:\n", strings.ToUpper(cat))
		}
		
		for _, tool := range tools {
			if verbose {
				fmt.Printf("  %s (v%s)\n", tool.Name, tool.Version)
				fmt.Printf("    ID: %s\n", tool.ID)
				fmt.Printf("    Description: %s\n", tool.Description)
				fmt.Printf("    File: %s\n", tool.File)
				
				if len(tool.Dependencies) > 0 {
					fmt.Printf("    Dependencies: %s\n", strings.Join(tool.Dependencies, ", "))
					
					// Show dependency details
					for _, dep := range tool.Dependencies {
						if depInfo, exists := depsConfig.Dependencies[dep]; exists {
							fmt.Printf("      - %s: %s\n", dep, depInfo.Description)
						}
					}
				}
				fmt.Println()
			} else {
				fmt.Printf("  %-20s %s\n", tool.Name, tool.Description)
			}
		}
	}
	
	return nil
}