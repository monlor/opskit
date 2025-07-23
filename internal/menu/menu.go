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

// MenuAction represents the action taken by user
type MenuAction int

const (
	ActionSelect MenuAction = iota
	ActionBack
	ActionQuit
)

// MenuResult represents the result of a menu operation
type MenuResult struct {
	Action MenuAction
	Item   *MenuItem
}

// showTwoLevelMenu displays unified search that includes both categories and tools
func showTwoLevelMenu(tools []config.Tool) (*MenuItem, error) {
	// Create unified search items: categories + all tools
	unifiedItems := createUnifiedSearchItems(tools)
	
	// Show unified search menu
	selectedItem, err := showUnifiedSearchMenu(unifiedItems, tools)
	if err != nil {
		return nil, err
	}
	
	return selectedItem, nil
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

// showUnifiedSearchMenu displays the unified search interface
func showUnifiedSearchMenu(items []UnifiedSearchItem, allTools []config.Tool) (*MenuItem, error) {
	// Use fuzzy selector for unified search
	selected, err := ShowUnifiedSearchMenu(items, "Search Categories and Tools")
	if err != nil {
		logger.Error("Failed to show unified search menu: %v", err)
		// Fallback to simple unified menu
		return showSimpleUnifiedMenu(items, allTools)
	}
	
	if selected == nil {
		return nil, nil // User quit
	}
	
	// Handle selection based on type
	if selected.Type == "category" {
		// Show tools in selected category
		categoryTools := createMenuItems(selected.Category.Tools)
		return showCategoryToolsMenu(categoryTools, selected.Category.Name, allTools)
	} else {
		// Direct tool selection
		return &MenuItem{
			ID:          selected.Tool.ID,
			Name:        selected.Tool.Name,
			Description: selected.Tool.Description,
			Tool:        selected.Tool,
		}, nil
	}
}

// showCategoryToolsMenu shows tools in a specific category with back navigation
func showCategoryToolsMenu(tools []MenuItem, categoryName string, allTools []config.Tool) (*MenuItem, error) {
	for {
		selectedTool, action, err := showToolMenuWithAction(tools, categoryName)
		if err != nil {
			return nil, err
		}
		
		switch action {
		case ActionSelect:
			return selectedTool, nil
		case ActionBack:
			// Go back to unified search
			return showTwoLevelMenu(allTools)
		case ActionQuit:
			return nil, nil // User quit
		}
	}
}

// showCategoryMenu displays the category selection menu
func showCategoryMenu(categories []CategoryItem) (*CategoryItem, error) {
	// Convert categories to fuzzy menu items for selection
	var menuItems []FuzzyMenuItem
	for _, cat := range categories {
		menuItems = append(menuItems, FuzzyMenuItem{
			ID:          strings.ToLower(cat.Name),
			Name:        cat.Name,
			Description: cat.Description,
			Group:       "category",
			Score:       1.0,
		})
	}
	
	// Use fuzzy selector for categories
	selected, err := ShowFuzzyCategoryMenu(menuItems, "Select Category")
	if err != nil {
		logger.Error("Failed to show category menu: %v", err)
		// Fallback to simple category menu
		return showSimpleCategoryMenu(categories)
	}
	
	if selected == nil {
		return nil, nil
	}
	
	// Find the selected category
	for _, cat := range categories {
		if strings.ToLower(cat.Name) == selected.ID {
			return &cat, nil
		}
	}
	
	return nil, fmt.Errorf("category not found")
}

// showToolMenu displays tools in a category
func showToolMenu(tools []MenuItem, categoryName string) (*MenuItem, error) {
	// Use fuzzy selector for tools
	selected, err := ShowFuzzyToolMenu(tools, fmt.Sprintf("Select Tool in %s", categoryName))
	if err != nil {
		logger.Error("Failed to show tool menu: %v", err)
		// Fallback to simple tool menu
		return showSimpleToolMenu(tools, categoryName)
	}
	
	return selected, nil
}

// showToolMenuWithAction displays tools in a category and returns the action taken
func showToolMenuWithAction(tools []MenuItem, categoryName string) (*MenuItem, MenuAction, error) {
	// Use fuzzy selector for tools
	selected, action, err := ShowFuzzyToolMenuWithAction(tools, fmt.Sprintf("Select Tool in %s", categoryName))
	if err != nil {
		logger.Error("Failed to show tool menu: %v", err)
		// Fallback to simple tool menu
		return showSimpleToolMenuWithAction(tools, categoryName)
	}
	
	return selected, action, nil
}

// showSimpleCategoryMenu is a fallback simple category menu
func showSimpleCategoryMenu(categories []CategoryItem) (*CategoryItem, error) {
	fmt.Printf("\n" + strings.Repeat("=", 60) + "\n")
	fmt.Printf("OpsKit - Select Category\n")
	fmt.Printf(strings.Repeat("=", 60) + "\n\n")
	
	fmt.Printf("Available Categories:\n\n")
	for i, cat := range categories {
		fmt.Printf("%d. %s\n", i+1, cat.Name)
		fmt.Printf("   %s\n\n", cat.Description)
	}
	
	// Get user input
	prompt := promptui.Prompt{
		Label: "Select a category (1-" + strconv.Itoa(len(categories)) + " or q to quit)",
		Validate: func(input string) error {
			if input == "q" || input == "Q" {
				return nil
			}
			
			num, err := strconv.Atoi(input)
			if err != nil {
				return fmt.Errorf("invalid input: please enter a number or 'q'")
			}
			
			if num < 1 || num > len(categories) {
				return fmt.Errorf("invalid selection: please enter a number between 1 and %d", len(categories))
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
	
	// Get selected category by number
	num, _ := strconv.Atoi(result)
	return &categories[num-1], nil
}

// showSimpleToolMenu is a fallback simple tool menu
func showSimpleToolMenu(tools []MenuItem, categoryName string) (*MenuItem, error) {
	tool, action, err := showSimpleToolMenuWithAction(tools, categoryName)
	if err != nil {
		return nil, err
	}
	
	if action == ActionBack {
		return nil, nil // Signal to go back
	}
	
	return tool, nil
}

// showSimpleToolMenuWithAction is a fallback simple tool menu with action tracking
func showSimpleToolMenuWithAction(tools []MenuItem, categoryName string) (*MenuItem, MenuAction, error) {
	fmt.Printf("\n" + strings.Repeat("=", 60) + "\n")
	fmt.Printf("OpsKit - Tools in %s\n", categoryName)
	fmt.Printf(strings.Repeat("=", 60) + "\n\n")
	
	fmt.Printf("Available Tools:\n\n")
	for i, tool := range tools {
		fmt.Printf("%d. %s\n", i+1, tool.Name)
		fmt.Printf("   %s\n\n", tool.Description)
	}
	
	// Get user input
	prompt := promptui.Prompt{
		Label: "Select a tool (1-" + strconv.Itoa(len(tools)) + ", b to go back, or q to quit)",
		Validate: func(input string) error {
			if input == "q" || input == "Q" || input == "b" || input == "B" {
				return nil
			}
			
			num, err := strconv.Atoi(input)
			if err != nil {
				return fmt.Errorf("invalid input: please enter a number, 'b' to go back, or 'q' to quit")
			}
			
			if num < 1 || num > len(tools) {
				return fmt.Errorf("invalid selection: please enter a number between 1 and %d", len(tools))
			}
			
			return nil
		},
	}
	
	result, err := prompt.Run()
	if err != nil {
		return nil, ActionQuit, fmt.Errorf("prompt failed: %w", err)
	}
	
	// Handle quit
	if result == "q" || result == "Q" {
		return nil, ActionQuit, nil
	}
	
	// Handle back
	if result == "b" || result == "B" {
		return nil, ActionBack, nil
	}
	
	// Get selected tool by number
	num, _ := strconv.Atoi(result)
	return &tools[num-1], ActionSelect, nil
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

// showSimpleUnifiedMenu is a fallback simple unified menu
func showSimpleUnifiedMenu(items []UnifiedSearchItem, allTools []config.Tool) (*MenuItem, error) {
	fmt.Printf("\n" + strings.Repeat("=", 60) + "\n")
	fmt.Printf("OpsKit - Search Categories and Tools (Simple Mode)\n")
	fmt.Printf(strings.Repeat("=", 60) + "\n\n")
	
	fmt.Printf("Available Items:\n\n")
	for i, item := range items {
		fmt.Printf("%d. %s\n", i+1, item.Name)
		fmt.Printf("   %s\n\n", item.Description)
	}
	
	// Get user input
	prompt := promptui.Prompt{
		Label: "Select an item (1-" + strconv.Itoa(len(items)) + " or q to quit)",
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
	
	// Get selected item by number
	num, _ := strconv.Atoi(result)
	selected := items[num-1]
	
	// Handle selection based on type
	if selected.Type == "category" {
		// Show tools in selected category
		categoryTools := createMenuItems(selected.Category.Tools)
		return showCategoryToolsMenu(categoryTools, selected.Category.Name, allTools)
	} else {
		// Direct tool selection
		return &MenuItem{
			ID:          selected.Tool.ID,
			Name:        selected.Tool.Name,
			Description: selected.Tool.Description,
			Tool:        selected.Tool,
		}, nil
	}
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