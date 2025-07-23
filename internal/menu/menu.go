package menu

import (
	"fmt"
	"os"
	"os/exec"
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
	
	for {
		// Show two-level menu: category -> tool
		selectedItem, err := showTwoLevelMenu(toolsConfig.Tools)
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

// CategoryItem represents a category in the menu
type CategoryItem struct {
	Name        string
	Description string
	ToolCount   int
	Tools       []config.Tool
}

// groupToolsByCategory groups tools by their category/group
func groupToolsByCategory(tools []config.Tool) map[string][]config.Tool {
	groups := make(map[string][]config.Tool)
	for _, tool := range tools {
		groupName := tool.Group
		if groupName == "" {
			groupName = tool.Category
		}
		if groupName == "" {
			groupName = "other"
		}
		groups[groupName] = append(groups[groupName], tool)
	}
	return groups
}

// createCategoryItems creates category items from tools
func createCategoryItems(tools []config.Tool) []CategoryItem {
	groups := groupToolsByCategory(tools)
	var categories []CategoryItem
	
	for groupName, groupTools := range groups {
		categories = append(categories, CategoryItem{
			Name:        strings.Title(groupName),
			Description: fmt.Sprintf("%d tools available", len(groupTools)),
			ToolCount:   len(groupTools),
			Tools:       groupTools,
		})
	}
	
	return categories
}

// createMenuItems creates menu items from tools
func createMenuItems(tools []config.Tool) []MenuItem {
	var items []MenuItem
	
	for _, tool := range tools {
		groupName := tool.Group
		if groupName == "" {
			groupName = tool.Category
		}
		if groupName == "" {
			groupName = "other"
		}
		
		items = append(items, MenuItem{
			ID:          tool.ID,
			Name:        tool.Name,
			Description: tool.Description,
			Tool:        &tool,
		})
	}
	
	return items
}

// showTwoLevelMenu displays gocui-based interactive menu
func showTwoLevelMenu(tools []config.Tool) (*MenuItem, error) {
	return ShowGocuiMenu(tools)
}

// UnifiedSearchItem represents an item in the unified search
type UnifiedSearchItem struct {
	ID          string
	Name        string
	Description string
	Type        string // "category" or "tool"
	Tool        *config.Tool // nil for categories
	Category    *CategoryItem // nil for tools
}

// createUnifiedSearchItems creates search items including both categories and tools
func createUnifiedSearchItems(tools []config.Tool) []UnifiedSearchItem {
	var items []UnifiedSearchItem
	
	// Add categories
	categories := createCategoryItems(tools)
	for _, cat := range categories {
		items = append(items, UnifiedSearchItem{
			ID:          strings.ToLower(cat.Name),
			Name:        fmt.Sprintf("📁 %s", cat.Name),
			Description: cat.Description,
			Type:        "category",
			Category:    &cat,
		})
	}
	
	// Add all tools with category prefix
	for _, tool := range tools {
		groupName := tool.Group
		if groupName == "" {
			groupName = tool.Category
		}
		if groupName == "" {
			groupName = "other"
		}
		
		items = append(items, UnifiedSearchItem{
			ID:          tool.ID,
			Name:        fmt.Sprintf("🔧 %s", tool.Name),
			Description: fmt.Sprintf("[%s] %s", strings.Title(groupName), tool.Description),
			Type:        "tool",
			Tool:        &tool,
		})
	}
	
	return items
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