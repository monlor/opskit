package menu

import (
	"fmt"
	"os"
	"os/exec"
	"strconv"
	"strings"

	"github.com/manifoldco/promptui"
	"opskit/internal/config"
	"opskit/internal/dependencies"
	"opskit/internal/downloader"
	"opskit/internal/logger"
)

// MenuItem represents a menu item
type MenuItem struct {
	ID          string
	Name        string
	Description string
	Tool        *config.Tool
}

// RunInteractiveMenu runs the interactive menu system
func RunInteractiveMenu(cfg *config.Config) error {
	logger.Info("Starting OpsKit Interactive Menu")
	
	// Load configurations
	dl := downloader.NewDownloader(cfg)
	
	toolsConfigPath, err := dl.LoadOrDownloadConfig("tools.json")
	if err != nil {
		return fmt.Errorf("failed to load tools config: %w", err)
	}
	
	toolsConfig, err := config.LoadToolsConfig(toolsConfigPath)
	if err != nil {
		return fmt.Errorf("failed to parse tools config: %w", err)
	}
	
	depsConfigPath, err := dl.LoadOrDownloadConfig("dependencies.json")
	if err != nil {
		return fmt.Errorf("failed to load dependencies config: %w", err)
	}
	
	depsConfig, err := config.LoadDependenciesConfig(depsConfigPath)
	if err != nil {
		return fmt.Errorf("failed to parse dependencies config: %w", err)
	}
	
	// Create menu items
	menuItems := createMenuItems(toolsConfig.Tools)
	
	for {
		// Show main menu
		selectedItem, err := showMainMenu(menuItems)
		if err != nil {
			return err
		}
		
		if selectedItem == nil {
			logger.Info("Goodbye!")
			return nil
		}
		
		// Execute selected tool
		if err := executeToolFromMenu(selectedItem, cfg, depsConfig, dl); err != nil {
			logger.Error("Tool execution failed: %v", err)
			
			// Ask if user wants to continue
			if !confirmContinue() {
				return nil
			}
		}
	}
}

// createMenuItems creates menu items from tools
func createMenuItems(tools []config.Tool) []MenuItem {
	var items []MenuItem
	
	// Group tools by category
	categories := make(map[string][]config.Tool)
	for _, tool := range tools {
		categories[tool.Category] = append(categories[tool.Category], tool)
	}
	
	// Create menu items
	for category, categoryTools := range categories {
		for _, tool := range categoryTools {
			items = append(items, MenuItem{
				ID:          tool.ID,
				Name:        tool.Name,
				Description: fmt.Sprintf("[%s] %s", strings.ToUpper(category), tool.Description),
				Tool:        &tool,
			})
		}
	}
	
	return items
}

// showMainMenu displays the main menu and returns selected item
func showMainMenu(items []MenuItem) (*MenuItem, error) {
	// Create menu options
	options := make([]string, 0, len(items)+1)
	for i, item := range items {
		options = append(options, fmt.Sprintf("%d. %s", i+1, item.Name))
	}
	options = append(options, "q. Quit")
	
	// Show menu
	fmt.Printf("\n" + strings.Repeat("=", 60) + "\n")
	fmt.Printf("OpsKit - Remote Operations Toolkit\n")
	fmt.Printf(strings.Repeat("=", 60) + "\n\n")
	
	fmt.Printf("Available Tools:\n\n")
	for i, item := range items {
		fmt.Printf("%d. %s\n", i+1, item.Name)
		fmt.Printf("   %s\n\n", item.Description)
	}
	
	// Get user input
	prompt := promptui.Prompt{
		Label: "Select a tool (1-" + strconv.Itoa(len(items)) + " or q to quit)",
		Validate: func(input string) error {
			if input == "q" || input == "Q" {
				return nil
			}
			
			num, err := strconv.Atoi(input)
			if err != nil {
				return fmt.Errorf("invalid input: please enter a number or 'q'")
			}
			
			if num < 1 || num > len(items) {
				return fmt.Errorf("invalid selection: please enter a number between 1 and %d", len(items))
			}
			
			return nil
		},
	}
	
	result, err := prompt.Run()
	if err != nil {
		return nil, fmt.Errorf("prompt failed: %w", err)
	}
	
	// Handle quit
	if result == "q" || result == "Q" {
		return nil, nil
	}
	
	// Get selected item
	num, _ := strconv.Atoi(result)
	return &items[num-1], nil
}

// executeToolFromMenu executes a tool selected from the menu
func executeToolFromMenu(item *MenuItem, cfg *config.Config, depsConfig *config.DependenciesConfig, dl *downloader.Downloader) error {
	logger.Info("Selected: %s", item.Name)
	
	// Check dependencies
	if len(item.Tool.Dependencies) > 0 {
		depManager := dependencies.NewManager(cfg, depsConfig)
		if err := depManager.CheckDependencies(item.Tool.Dependencies); err != nil {
			return fmt.Errorf("dependency check failed: %w", err)
		}
	}
	
	// Download tool
	toolPath, err := dl.LoadOrDownloadTool(item.Tool.File)
	if err != nil {
		return fmt.Errorf("failed to load tool: %w", err)
	}
	
	// Execute tool
	logger.Info("Executing %s...", item.Tool.Name)
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
	
	logger.Success("Tool %s completed successfully", item.Tool.Name)
	return nil
}

// confirmContinue asks user if they want to continue
func confirmContinue() bool {
	prompt := promptui.Prompt{
		Label:     "Continue with another tool? (y/N)",
		Default:   "N",
		IsConfirm: true,
	}
	
	result, err := prompt.Run()
	if err != nil {
		return false
	}
	
	return strings.ToLower(result) == "y"
}