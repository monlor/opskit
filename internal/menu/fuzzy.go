package menu

import (
	"fmt"
	"os"
	"sort"
	"strconv"
	"strings"
	"golang.org/x/sys/unix"
	"opskit/internal/config"
	"opskit/internal/logger"
)

// FuzzyMenuItem represents an item in the fuzzy finder
type FuzzyMenuItem struct {
	ID          string
	Name        string
	Description string
	Group       string
	Tool        *config.Tool
	Score       float64 // Matching score for fuzzy search
}

// FuzzySelector provides fzf-like interactive selection
type FuzzySelector struct {
	items         []FuzzyMenuItem
	filteredItems []FuzzyMenuItem
	query         string
	selectedIndex int
	maxDisplay    int
	termHeight    int
	termWidth     int
}

// Terminal control sequences
const (
	clearScreen     = "\033[2J"
	hideCursor      = "\033[?25l"
	showCursor      = "\033[?25h"
	moveCursorUp    = "\033[A"
	moveCursorDown  = "\033[B"
	moveCursorHome  = "\033[H"
	clearLine       = "\033[2K"
	resetAttributes = "\033[0m"
	boldText        = "\033[1m"
	dimText         = "\033[2m"
	colorReset      = "\033[0m"
	colorRed        = "\033[31m"
	colorGreen      = "\033[32m"
	colorYellow     = "\033[33m"
	colorBlue       = "\033[34m"
	colorMagenta    = "\033[35m"
	colorCyan       = "\033[36m"
	colorWhite      = "\033[37m"
)

// Key codes
const (
	keyEsc       = 27
	keyEnter     = 13
	keyBackspace = 127
	keyTab       = 9
	keyCtrlC     = 3
	keyCtrlU     = 21
)

// NewFuzzySelector creates a new fuzzy selector
func NewFuzzySelector(items []MenuItem) *FuzzySelector {
	fuzzyItems := make([]FuzzyMenuItem, len(items))
	for i, item := range items {
		group := item.Tool.Group
		if group == "" {
			group = item.Tool.Category
		}
		
		fuzzyItems[i] = FuzzyMenuItem{
			ID:          item.ID,
			Name:        item.Name,
			Description: item.Description,
			Group:       group,
			Tool:        item.Tool,
			Score:       1.0,
		}
	}

	selector := &FuzzySelector{
		items:         fuzzyItems,
		filteredItems: fuzzyItems,
		query:         "",
		selectedIndex: 0,
		maxDisplay:    10,
	}

	selector.updateTerminalSize()
	return selector
}

// updateTerminalSize gets current terminal dimensions
func (f *FuzzySelector) updateTerminalSize() {
	// Simple fallback values for now
	f.termHeight = 24
	f.termWidth = 80
	f.maxDisplay = 10
	
	// Try to get actual terminal size if possible
	if size, err := unix.IoctlGetWinsize(int(os.Stdin.Fd()), unix.TIOCGWINSZ); err == nil {
		f.termHeight = int(size.Row)
		f.termWidth = int(size.Col)
		f.maxDisplay = f.termHeight - 6 // Leave space for header and input
		if f.maxDisplay < 5 {
			f.maxDisplay = 5
		}
	}
}

// fuzzyScore calculates fuzzy matching score
func fuzzyScore(query, target string) float64 {
	if query == "" {
		return 1.0
	}

	query = strings.ToLower(strings.TrimSpace(query))
	target = strings.ToLower(strings.TrimSpace(target))

	// Exact match gets highest score
	if target == query {
		return 5.0
	}

	// Exact substring match gets high score
	if strings.Contains(target, query) {
		// Score higher if match is at the beginning
		if strings.HasPrefix(target, query) {
			return 4.0 + float64(len(query))/float64(len(target))
		}
		return 3.0 + float64(len(query))/float64(len(target))
	}

	// Fuzzy match: check if all characters in query exist in target (in order)
	targetRunes := []rune(target)
	queryRunes := []rune(query)
	
	if len(queryRunes) > len(targetRunes) {
		return 0.0
	}

	matchCount := 0
	targetIndex := 0
	lastMatchIndex := -1
	
	for _, queryChar := range queryRunes {
		found := false
		for i := targetIndex; i < len(targetRunes); i++ {
			if targetRunes[i] == queryChar {
				matchCount++
				targetIndex = i + 1
				lastMatchIndex = i
				found = true
				break
			}
		}
		if !found {
			return 0.0 // No match for this character
		}
	}

	// All characters found, calculate score
	if matchCount == len(queryRunes) {
		// Score based on:
		// 1. Match ratio
		// 2. How compact the matches are (closer together = better)
		matchRatio := float64(matchCount) / float64(len(queryRunes))
		compactness := 1.0 - float64(lastMatchIndex-targetIndex+len(queryRunes))/float64(len(targetRunes))
		return matchRatio * 0.6 * (1.0 + compactness)
	}

	return 0.0
}

// filterItems filters items based on current query
func (f *FuzzySelector) filterItems() {
	// Create a new slice to avoid any issues with reusing the old one
	f.filteredItems = make([]FuzzyMenuItem, 0, len(f.items))

	for _, item := range f.items {
		// Calculate score for name and ID
		nameScore := fuzzyScore(f.query, item.Name)
		idScore := fuzzyScore(f.query, item.ID)
		descScore := fuzzyScore(f.query, item.Description) * 0.5 // Lower weight for description
		
		// Use the highest score from any field
		maxScore := nameScore
		if idScore > maxScore {
			maxScore = idScore
		}
		if descScore > maxScore {
			maxScore = descScore
		}

		// Only include items that have some match
		if maxScore > 0 {
			// Create a copy of the item with the score
			itemCopy := item
			itemCopy.Score = maxScore
			f.filteredItems = append(f.filteredItems, itemCopy)
		}
	}

	// Sort by score (descending)
	sort.Slice(f.filteredItems, func(i, j int) bool {
		return f.filteredItems[i].Score > f.filteredItems[j].Score
	})

	// Reset selection if out of range
	if f.selectedIndex >= len(f.filteredItems) {
		f.selectedIndex = 0
	}
}

// highlightMatch highlights matching characters in text
func highlightMatch(text, query string) string {
	if query == "" {
		return text
	}

	lower := strings.ToLower(text)
	lowerQuery := strings.ToLower(query)
	
	// For exact substring matches, highlight the matched portion
	if idx := strings.Index(lower, lowerQuery); idx != -1 {
		before := text[:idx]
		match := text[idx : idx+len(query)]
		after := text[idx+len(query):]
		return before + colorYellow + boldText + match + resetAttributes + after
	}

	return text
}

// drawScreen renders the current state
func (f *FuzzySelector) drawScreen() {
	// Clear screen and hide cursor
	fmt.Print(clearScreen + moveCursorHome + hideCursor)

	// Header
	fmt.Printf("%s%sOpsKit - Tool Selector%s\n", boldText, colorCyan, resetAttributes)
	fmt.Printf("%sType to search, ↑/↓ to navigate, Enter to select, Esc to quit%s\n\n", 
		dimText, resetAttributes)

	// Search input
	fmt.Printf("%s> %s%s%s\n", colorBlue, colorWhite, f.query, resetAttributes)
	fmt.Printf("\n")

	// Results info
	total := len(f.items)
	filtered := len(f.filteredItems)
	fmt.Printf("%s[%d/%d]%s\n\n", dimText, filtered, total, resetAttributes)

	// Display filtered items
	displayCount := f.maxDisplay
	if displayCount > len(f.filteredItems) {
		displayCount = len(f.filteredItems)
	}

	for i := 0; i < displayCount; i++ {
		item := f.filteredItems[i]
		
		// Selection indicator and styling
		if i == f.selectedIndex {
			fmt.Printf("%s%s▶ %s", colorGreen, boldText, resetAttributes)
		} else {
			fmt.Printf("  ")
		}

		// Group indicator
		groupColor := getGroupColor(item.Group)
		fmt.Printf("%s[%s]%s ", groupColor, strings.ToUpper(item.Group), resetAttributes)

		// Tool name with highlighting
		nameHighlighted := highlightMatch(item.Name, f.query)
		if i == f.selectedIndex {
			fmt.Printf("%s%s%s", boldText, nameHighlighted, resetAttributes)
		} else {
			fmt.Printf("%s", nameHighlighted)
		}

		// Tool ID in parentheses if different from name
		if !strings.Contains(strings.ToLower(item.Name), strings.ToLower(item.ID)) {
			idHighlighted := highlightMatch(item.ID, f.query)
			fmt.Printf(" %s(%s)%s", dimText, idHighlighted, resetAttributes)
		}

		fmt.Println()

		// Description on next line with indent
		if i == f.selectedIndex || len(f.filteredItems) <= 5 {
			desc := item.Description
			if len(desc) > f.termWidth-4 {
				desc = desc[:f.termWidth-7] + "..."
			}
			descHighlighted := highlightMatch(desc, f.query)
			fmt.Printf("    %s%s%s\n", dimText, descHighlighted, resetAttributes)
		}
	}

	// Show cursor at input position
	fmt.Printf("\033[4;%dH", len(f.query)+3) // Line 4, after "> " and query
	fmt.Print(showCursor)
}

// drawCategoryScreen renders the category selection interface
func (f *FuzzySelector) drawCategoryScreen(title string) {
	// Clear screen and hide cursor
	fmt.Print(clearScreen + moveCursorHome + hideCursor)

	// Header
	fmt.Printf("%s%s%s%s\n", boldText, colorCyan, title, resetAttributes)
	fmt.Printf("%sType to search, ↑/↓ to navigate, Enter to select, Esc to quit%s\n\n", 
		dimText, resetAttributes)

	// Search input
	fmt.Printf("%s> %s%s%s\n", colorBlue, colorWhite, f.query, resetAttributes)
	fmt.Printf("\n")

	// Results info
	total := len(f.items)
	filtered := len(f.filteredItems)
	fmt.Printf("%s[%d/%d categories]%s\n\n", dimText, filtered, total, resetAttributes)

	// Display filtered categories
	displayCount := f.maxDisplay
	if displayCount > len(f.filteredItems) {
		displayCount = len(f.filteredItems)
	}

	for i := 0; i < displayCount; i++ {
		item := f.filteredItems[i]
		
		// Selection indicator and styling
		if i == f.selectedIndex {
			fmt.Printf("%s%s▶ %s", colorGreen, boldText, resetAttributes)
		} else {
			fmt.Printf("  ")
		}

		// Category name with highlighting
		nameHighlighted := highlightMatch(item.Name, f.query)
		if i == f.selectedIndex {
			fmt.Printf("%s%s%s", boldText, nameHighlighted, resetAttributes)
		} else {
			fmt.Printf("%s", nameHighlighted)
		}

		fmt.Println()

		// Description on next line with indent
		if i == f.selectedIndex || len(f.filteredItems) <= 5 {
			desc := item.Description
			if len(desc) > f.termWidth-4 {
				desc = desc[:f.termWidth-7] + "..."
			}
			descHighlighted := highlightMatch(desc, f.query)
			fmt.Printf("    %s%s%s\n", dimText, descHighlighted, resetAttributes)
		}
	}

	// Show cursor at input position
	fmt.Printf("\033[4;%dH", len(f.query)+3) // Line 4, after "> " and query
	fmt.Print(showCursor)
}

// drawToolScreen renders the tool selection interface with back navigation
func (f *FuzzySelector) drawToolScreen(title string) {
	// Clear screen and hide cursor
	fmt.Print(clearScreen + moveCursorHome + hideCursor)

	// Header
	fmt.Printf("%s%s%s%s\n", boldText, colorCyan, title, resetAttributes)
	fmt.Printf("%sType to search, ↑/↓ to navigate, Enter to select, 'b' to go back, Esc to quit%s\n\n", 
		dimText, resetAttributes)

	// Search input
	fmt.Printf("%s> %s%s%s\n", colorBlue, colorWhite, f.query, resetAttributes)
	fmt.Printf("\n")

	// Results info
	total := len(f.items)
	filtered := len(f.filteredItems)
	fmt.Printf("%s[%d/%d tools]%s\n\n", dimText, filtered, total, resetAttributes)

	// Display filtered items
	displayCount := f.maxDisplay
	if displayCount > len(f.filteredItems) {
		displayCount = len(f.filteredItems)
	}

	for i := 0; i < displayCount; i++ {
		item := f.filteredItems[i]
		
		// Selection indicator and styling
		if i == f.selectedIndex {
			fmt.Printf("%s%s▶ %s", colorGreen, boldText, resetAttributes)
		} else {
			fmt.Printf("  ")
		}

		// Tool name with highlighting
		nameHighlighted := highlightMatch(item.Name, f.query)
		if i == f.selectedIndex {
			fmt.Printf("%s%s%s", boldText, nameHighlighted, resetAttributes)
		} else {
			fmt.Printf("%s", nameHighlighted)
		}

		// Tool ID in parentheses if different from name
		if !strings.Contains(strings.ToLower(item.Name), strings.ToLower(item.ID)) {
			idHighlighted := highlightMatch(item.ID, f.query)
			fmt.Printf(" %s(%s)%s", dimText, idHighlighted, resetAttributes)
		}

		fmt.Println()

		// Description on next line with indent
		if i == f.selectedIndex || len(f.filteredItems) <= 5 {
			desc := item.Description
			if len(desc) > f.termWidth-4 {
				desc = desc[:f.termWidth-7] + "..."
			}
			descHighlighted := highlightMatch(desc, f.query)
			fmt.Printf("    %s%s%s\n", dimText, descHighlighted, resetAttributes)
		}
	}

	// Show cursor at input position
	fmt.Printf("\033[4;%dH", len(f.query)+3) // Line 4, after "> " and query
	fmt.Print(showCursor)
}

// drawUnifiedSearchScreen renders the unified search interface
func (f *FuzzySelector) drawUnifiedSearchScreen(title string) {
	// Clear screen and hide cursor
	fmt.Print(clearScreen + moveCursorHome + hideCursor)

	// Header
	fmt.Printf("%s%s%s%s\n", boldText, colorCyan, title, resetAttributes)
	fmt.Printf("%sType to search categories and tools, ↑/↓ to navigate, Enter to select, Esc to quit%s\n\n", 
		dimText, resetAttributes)

	// Search input
	fmt.Printf("%s> %s%s%s\n", colorBlue, colorWhite, f.query, resetAttributes)
	fmt.Printf("\n")

	// Results info
	total := len(f.items)
	filtered := len(f.filteredItems)
	fmt.Printf("%s[%d/%d items]%s\n\n", dimText, filtered, total, resetAttributes)

	// Display filtered items
	displayCount := f.maxDisplay
	if displayCount > len(f.filteredItems) {
		displayCount = len(f.filteredItems)
	}

	for i := 0; i < displayCount; i++ {
		item := f.filteredItems[i]
		
		// Selection indicator and styling
		if i == f.selectedIndex {
			fmt.Printf("%s%s▶ %s", colorGreen, boldText, resetAttributes)
		} else {
			fmt.Printf("  ")
		}

		// Item name with highlighting and type indicator
		nameHighlighted := highlightMatch(item.Name, f.query)
		if i == f.selectedIndex {
			fmt.Printf("%s%s%s", boldText, nameHighlighted, resetAttributes)
		} else {
			fmt.Printf("%s", nameHighlighted)
		}

		fmt.Println()

		// Description on next line with indent
		if i == f.selectedIndex || len(f.filteredItems) <= 8 {
			desc := item.Description
			if len(desc) > f.termWidth-4 {
				desc = desc[:f.termWidth-7] + "..."
			}
			descHighlighted := highlightMatch(desc, f.query)
			fmt.Printf("    %s%s%s\n", dimText, descHighlighted, resetAttributes)
		}
	}

	// Show cursor at input position
	fmt.Printf("\033[4;%dH", len(f.query)+3) // Line 4, after "> " and query
	fmt.Print(showCursor)
}

// getGroupColor returns color for group
func getGroupColor(group string) string {
	switch strings.ToLower(group) {
	case "database":
		return colorRed
	case "cloud", "storage":
		return colorBlue
	case "kubernetes", "k8s":
		return colorMagenta
	case "development", "testing":
		return colorGreen
	default:
		return colorWhite
	}
}

// handleInput processes a single character input
func (f *FuzzySelector) handleInput(ch byte) (bool, *FuzzyMenuItem) {
	switch ch {
	case keyEsc, keyCtrlC:
		return false, nil // Quit
		
	case keyEnter:
		if len(f.filteredItems) > 0 && f.selectedIndex < len(f.filteredItems) {
			selected := f.filteredItems[f.selectedIndex]
			return false, &selected
		}
		return true, nil

	case keyBackspace:
		if len(f.query) > 0 {
			f.query = f.query[:len(f.query)-1]
			f.filterItems()
		}
		return true, nil

	case keyCtrlU:
		f.query = ""
		f.filterItems()
		return true, nil

	default:
		// Regular character input
		if ch >= 32 && ch < 127 { // Printable ASCII
			f.query += string(ch)
			f.filterItems()
		}
		return true, nil
	}
}

// handleEscapeSequence handles arrow key sequences
func (f *FuzzySelector) handleEscapeSequence() (bool, *FuzzyMenuItem) {
	// Try to read the escape sequence
	buf := make([]byte, 2)
	n, err := os.Stdin.Read(buf)
	if err != nil || n < 2 {
		return false, nil // Treat as ESC key
	}

	if buf[0] == '[' {
		switch buf[1] {
		case 'A': // Up arrow
			if f.selectedIndex > 0 {
				f.selectedIndex--
			}
		case 'B': // Down arrow
			if f.selectedIndex < len(f.filteredItems)-1 {
				f.selectedIndex++
			}
		}
	}

	return true, nil
}

// Run starts the fuzzy selector interface
func (f *FuzzySelector) Run() *MenuItem {
	if len(f.items) == 0 {
		return nil
	}

	// Set terminal to raw mode
	if err := setRawMode(); err != nil {
		logger.Error("Failed to set terminal to raw mode: %v", err)
		// Fallback to simple input without raw mode
		return f.runSimpleInput()
	}
	defer restoreTerminalMode()

	// Initial draw
	f.drawScreen()

	// Input loop
	buf := make([]byte, 3) // Buffer for escape sequences
	for {
		n, err := os.Stdin.Read(buf)
		if err != nil {
			continue
		}

		if n == 1 {
			continueLoop, selectedItem := f.handleInput(buf[0])
			if !continueLoop {
				// Clear screen and restore cursor
				fmt.Print(clearScreen + moveCursorHome + showCursor)
				
				if selectedItem != nil {
					// Convert back to MenuItem
					return &MenuItem{
						ID:          selectedItem.ID,
						Name:        selectedItem.Name,
						Description: selectedItem.Description,
						Tool:        selectedItem.Tool,
					}
				}
				return nil
			}
		} else if n == 3 && buf[0] == keyEsc && buf[1] == '[' {
			// Handle arrow keys
			switch buf[2] {
			case 'A': // Up arrow
				if f.selectedIndex > 0 {
					f.selectedIndex--
				}
			case 'B': // Down arrow
				if f.selectedIndex < len(f.filteredItems)-1 {
					f.selectedIndex++
				}
			}
		}

		f.drawScreen()
	}
}

// runCategoryMode runs the fuzzy selector for category selection
func (f *FuzzySelector) runCategoryMode(title string) *FuzzyMenuItem {
	if len(f.items) == 0 {
		return nil
	}

	// Set terminal to raw mode
	if err := setRawMode(); err != nil {
		logger.Error("Failed to set terminal to raw mode: %v", err)
		// Fallback to simple input without raw mode
		return f.runSimpleCategoryInput(title)
	}
	defer restoreTerminalMode()

	// Initial draw
	f.drawCategoryScreen(title)

	// Input loop
	buf := make([]byte, 3) // Buffer for escape sequences
	for {
		n, err := os.Stdin.Read(buf)
		if err != nil {
			continue
		}

		if n == 1 {
			continueLoop, selectedItem := f.handleInput(buf[0])
			if !continueLoop {
				// Clear screen and restore cursor
				fmt.Print(clearScreen + moveCursorHome + showCursor)
				return selectedItem
			}
		} else if n == 3 && buf[0] == keyEsc && buf[1] == '[' {
			// Handle arrow keys
			switch buf[2] {
			case 'A': // Up arrow
				if f.selectedIndex > 0 {
					f.selectedIndex--
				}
			case 'B': // Down arrow
				if f.selectedIndex < len(f.filteredItems)-1 {
					f.selectedIndex++
				}
			}
		}

		f.drawCategoryScreen(title)
	}
}

// runToolMode runs the fuzzy selector for tool selection with back navigation
func (f *FuzzySelector) runToolMode(title string) *FuzzyMenuItem {
	if len(f.items) == 0 {
		return nil
	}

	// Set terminal to raw mode
	if err := setRawMode(); err != nil {
		logger.Error("Failed to set terminal to raw mode: %v", err)
		// Fallback to simple input without raw mode
		return f.runSimpleToolInput(title)
	}
	defer restoreTerminalMode()

	// Initial draw
	f.drawToolScreen(title)

	// Input loop
	buf := make([]byte, 3) // Buffer for escape sequences
	for {
		n, err := os.Stdin.Read(buf)
		if err != nil {
			continue
		}

		if n == 1 {
			// Handle 'b' for back navigation
			if buf[0] == 'b' || buf[0] == 'B' {
				// Clear screen and restore cursor
				fmt.Print(clearScreen + moveCursorHome + showCursor)
				return nil // Signal to go back
			}
			
			continueLoop, selectedItem := f.handleInput(buf[0])
			if !continueLoop {
				// Clear screen and restore cursor
				fmt.Print(clearScreen + moveCursorHome + showCursor)
				return selectedItem
			}
		} else if n == 3 && buf[0] == keyEsc && buf[1] == '[' {
			// Handle arrow keys
			switch buf[2] {
			case 'A': // Up arrow
				if f.selectedIndex > 0 {
					f.selectedIndex--
				}
			case 'B': // Down arrow
				if f.selectedIndex < len(f.filteredItems)-1 {
					f.selectedIndex++
				}
			}
		}

		f.drawToolScreen(title)
	}
}

// runToolModeWithAction runs the fuzzy selector for tool selection with action tracking
func (f *FuzzySelector) runToolModeWithAction(title string) FuzzyResult {
	if len(f.items) == 0 {
		return FuzzyResult{Item: nil, Action: ActionQuit}
	}

	// Set terminal to raw mode
	if err := setRawMode(); err != nil {
		logger.Error("Failed to set terminal to raw mode: %v", err)
		// Fallback to simple input without raw mode
		selected := f.runSimpleToolInput(title)
		if selected == nil {
			return FuzzyResult{Item: nil, Action: ActionQuit}
		}
		return FuzzyResult{Item: selected, Action: ActionSelect}
	}
	defer restoreTerminalMode()

	// Initial draw
	f.drawToolScreen(title)

	// Input loop
	buf := make([]byte, 3) // Buffer for escape sequences
	for {
		n, err := os.Stdin.Read(buf)
		if err != nil {
			continue
		}

		if n == 1 {
			// Handle 'b' for back navigation
			if buf[0] == 'b' || buf[0] == 'B' {
				// Clear screen and restore cursor
				fmt.Print(clearScreen + moveCursorHome + showCursor)
				return FuzzyResult{Item: nil, Action: ActionBack}
			}
			
			continueLoop, selectedItem := f.handleInput(buf[0])
			if !continueLoop {
				// Clear screen and restore cursor
				fmt.Print(clearScreen + moveCursorHome + showCursor)
				if selectedItem == nil {
					return FuzzyResult{Item: nil, Action: ActionQuit}
				}
				return FuzzyResult{Item: selectedItem, Action: ActionSelect}
			}
		} else if n == 3 && buf[0] == keyEsc && buf[1] == '[' {
			// Handle arrow keys
			switch buf[2] {
			case 'A': // Up arrow
				if f.selectedIndex > 0 {
					f.selectedIndex--
				}
			case 'B': // Down arrow
				if f.selectedIndex < len(f.filteredItems)-1 {
					f.selectedIndex++
				}
			}
		}

		f.drawToolScreen(title)
	}
}

// runSimpleInput runs a simple input mode without raw terminal
func (f *FuzzySelector) runSimpleInput() *MenuItem {
	for {
		fmt.Printf("\n" + strings.Repeat("=", 60) + "\n")
		fmt.Printf("OpsKit - Fuzzy Tool Selector (Simple Mode)\n")
		fmt.Printf(strings.Repeat("=", 60) + "\n\n")
		
		if f.query != "" {
			fmt.Printf("Filter: %s\n\n", f.query)
		}
		
		// Show filtered items
		displayCount := 10
		if displayCount > len(f.filteredItems) {
			displayCount = len(f.filteredItems)
		}
		
		for i := 0; i < displayCount; i++ {
			item := f.filteredItems[i]
			fmt.Printf("%d. [%s] %s\n", i+1, strings.ToUpper(item.Group), item.Name)
			fmt.Printf("   %s\n\n", item.Description)
		}
		
		fmt.Printf("Type to search, number to select, 'c' to clear filter, 'q' to quit: ")
		var input string
		fmt.Scanln(&input)
		
		if input == "q" || input == "Q" {
			return nil
		}
		
		if input == "c" || input == "C" {
			f.query = ""
			f.filterItems()
			continue
		}
		
		// Try to parse as number
		if num, err := strconv.Atoi(input); err == nil && num >= 1 && num <= len(f.filteredItems) {
			selected := f.filteredItems[num-1]
			return &MenuItem{
				ID:          selected.ID,
				Name:        selected.Name,
				Description: selected.Description,
				Tool:        selected.Tool,
			}
		}
		
		// Add to query
		f.query += input
		f.filterItems()
	}
}

// runSimpleCategoryInput runs simple category selection without raw terminal
func (f *FuzzySelector) runSimpleCategoryInput(title string) *FuzzyMenuItem {
	for {
		fmt.Printf("\n" + strings.Repeat("=", 60) + "\n")
		fmt.Printf("%s (Simple Mode)\n", title)
		fmt.Printf(strings.Repeat("=", 60) + "\n\n")
		
		if f.query != "" {
			fmt.Printf("Filter: %s\n\n", f.query)
		}
		
		// Show filtered categories
		displayCount := 10
		if displayCount > len(f.filteredItems) {
			displayCount = len(f.filteredItems)
		}
		
		for i := 0; i < displayCount; i++ {
			item := f.filteredItems[i]
			fmt.Printf("%d. %s\n", i+1, item.Name)
			fmt.Printf("   %s\n\n", item.Description)
		}
		
		fmt.Printf("Type to search, number to select, 'c' to clear filter, 'q' to quit: ")
		var input string
		fmt.Scanln(&input)
		
		if input == "q" || input == "Q" {
			return nil
		}
		
		if input == "c" || input == "C" {
			f.query = ""
			f.filterItems()
			continue
		}
		
		// Try to parse as number
		if num, err := strconv.Atoi(input); err == nil && num >= 1 && num <= len(f.filteredItems) {
			selected := f.filteredItems[num-1]
			return &selected
		}
		
		// Add to query
		f.query += input
		f.filterItems()
	}
}

// runSimpleToolInput runs simple tool selection without raw terminal
func (f *FuzzySelector) runSimpleToolInput(title string) *FuzzyMenuItem {
	for {
		fmt.Printf("\n" + strings.Repeat("=", 60) + "\n")
		fmt.Printf("%s (Simple Mode)\n", title)
		fmt.Printf(strings.Repeat("=", 60) + "\n\n")
		
		if f.query != "" {
			fmt.Printf("Filter: %s\n\n", f.query)
		}
		
		// Show filtered tools
		displayCount := 10
		if displayCount > len(f.filteredItems) {
			displayCount = len(f.filteredItems)
		}
		
		for i := 0; i < displayCount; i++ {
			item := f.filteredItems[i]
			fmt.Printf("%d. %s\n", i+1, item.Name)
			fmt.Printf("   %s\n\n", item.Description)
		}
		
		fmt.Printf("Type to search, number to select, 'b' to go back, 'c' to clear filter, 'q' to quit: ")
		var input string
		fmt.Scanln(&input)
		
		if input == "q" || input == "Q" {
			return nil
		}
		
		if input == "b" || input == "B" {
			return nil // Signal to go back
		}
		
		if input == "c" || input == "C" {
			f.query = ""
			f.filterItems()
			continue
		}
		
		// Try to parse as number
		if num, err := strconv.Atoi(input); err == nil && num >= 1 && num <= len(f.filteredItems) {
			selected := f.filteredItems[num-1]
			return &selected
		}
		
		// Add to query
		f.query += input
		f.filterItems()
	}
}

// Terminal mode handling
var originalTermios unix.Termios

func setRawMode() error {
	// Get current terminal attributes
	if err := unix.IoctlSetTermios(int(os.Stdin.Fd()), unix.TCGETS, &originalTermios); err != nil {
		return err
	}

	// Create a copy and modify it
	raw := originalTermios
	raw.Lflag &^= unix.ECHO | unix.ICANON | unix.ISIG
	raw.Iflag &^= unix.IXON
	raw.Cc[unix.VMIN] = 1
	raw.Cc[unix.VTIME] = 0

	// Apply raw mode
	return unix.IoctlSetTermios(int(os.Stdin.Fd()), unix.TCSETS, &raw)
}

func restoreTerminalMode() {
	unix.IoctlSetTermios(int(os.Stdin.Fd()), unix.TCSETS, &originalTermios)
	fmt.Print(showCursor)
}

// ShowFuzzyMenu displays the fuzzy selector interface
func ShowFuzzyMenu(items []MenuItem) (*MenuItem, error) {
	if len(items) == 0 {
		return nil, fmt.Errorf("no items to display")
	}

	selector := NewFuzzySelector(items)
	selected := selector.Run()
	
	return selected, nil
}

// ShowFuzzyCategoryMenu displays the fuzzy selector for categories
func ShowFuzzyCategoryMenu(items []FuzzyMenuItem, title string) (*FuzzyMenuItem, error) {
	if len(items) == 0 {
		return nil, fmt.Errorf("no categories to display")
	}

	selector := &FuzzySelector{
		items:         items,
		filteredItems: items,
		query:         "",
		selectedIndex: 0,
		maxDisplay:    10,
	}
	
	selector.updateTerminalSize()
	selected := selector.runCategoryMode(title)
	
	return selected, nil
}

// FuzzyResult represents the result from fuzzy selector
type FuzzyResult struct {
	Item   *FuzzyMenuItem
	Action MenuAction
}

// ShowFuzzyToolMenu displays the fuzzy selector for tools with back navigation
func ShowFuzzyToolMenu(tools []MenuItem, title string) (*MenuItem, error) {
	if len(tools) == 0 {
		return nil, fmt.Errorf("no tools to display")
	}

	// Convert MenuItem to FuzzyMenuItem
	var fuzzyItems []FuzzyMenuItem
	for _, tool := range tools {
		group := tool.Tool.Group
		if group == "" {
			group = tool.Tool.Category
		}
		
		fuzzyItems = append(fuzzyItems, FuzzyMenuItem{
			ID:          tool.ID,
			Name:        tool.Name,
			Description: tool.Description,
			Group:       group,
			Tool:        tool.Tool,
			Score:       1.0,
		})
	}

	selector := &FuzzySelector{
		items:         fuzzyItems,
		filteredItems: fuzzyItems,
		query:         "",
		selectedIndex: 0,
		maxDisplay:    10,
	}
	
	selector.updateTerminalSize()
	selected := selector.runToolMode(title)
	
	if selected == nil {
		return nil, nil
	}
	
	// Convert back to MenuItem
	return &MenuItem{
		ID:          selected.ID,
		Name:        selected.Name,
		Description: selected.Description,
		Tool:        selected.Tool,
	}, nil
}

// ShowFuzzyToolMenuWithAction displays the fuzzy selector for tools with action tracking
func ShowFuzzyToolMenuWithAction(tools []MenuItem, title string) (*MenuItem, MenuAction, error) {
	if len(tools) == 0 {
		return nil, ActionQuit, fmt.Errorf("no tools to display")
	}

	// Convert MenuItem to FuzzyMenuItem
	var fuzzyItems []FuzzyMenuItem
	for _, tool := range tools {
		group := tool.Tool.Group
		if group == "" {
			group = tool.Tool.Category
		}
		
		fuzzyItems = append(fuzzyItems, FuzzyMenuItem{
			ID:          tool.ID,
			Name:        tool.Name,
			Description: tool.Description,
			Group:       group,
			Tool:        tool.Tool,
			Score:       1.0,
		})
	}

	selector := &FuzzySelector{
		items:         fuzzyItems,
		filteredItems: fuzzyItems,
		query:         "",
		selectedIndex: 0,
		maxDisplay:    10,
	}
	
	selector.updateTerminalSize()
	result := selector.runToolModeWithAction(title)
	
	if result.Item == nil {
		return nil, result.Action, nil
	}
	
	// Convert back to MenuItem
	return &MenuItem{
		ID:          result.Item.ID,
		Name:        result.Item.Name,
		Description: result.Item.Description,
		Tool:        result.Item.Tool,
	}, result.Action, nil
}

// ShowUnifiedSearchMenu displays the unified search interface
func ShowUnifiedSearchMenu(items []UnifiedSearchItem, title string) (*UnifiedSearchItem, error) {
	if len(items) == 0 {
		return nil, fmt.Errorf("no items to display")
	}

	// Convert UnifiedSearchItem to FuzzyMenuItem
	var fuzzyItems []FuzzyMenuItem
	for _, item := range items {
		fuzzyItems = append(fuzzyItems, FuzzyMenuItem{
			ID:          item.ID,
			Name:        item.Name,
			Description: item.Description,
			Group:       item.Type,
			Tool:        item.Tool,
			Score:       1.0,
		})
	}

	selector := &FuzzySelector{
		items:         fuzzyItems,
		filteredItems: fuzzyItems,
		query:         "",
		selectedIndex: 0,
		maxDisplay:    15, // Show more items for unified search
	}
	
	selector.updateTerminalSize()
	
	// Set terminal to raw mode
	if err := setRawMode(); err != nil {
		logger.Error("Failed to set terminal to raw mode: %v", err)
		// Fallback to simple unified input
		return showSimpleUnifiedFuzzyInput(items, title)
	}
	defer restoreTerminalMode()

	// Initial draw
	selector.drawUnifiedSearchScreen(title)

	// Input loop
	buf := make([]byte, 3) // Buffer for escape sequences
	for {
		n, err := os.Stdin.Read(buf)
		if err != nil {
			continue
		}

		if n == 1 {
			continueLoop, selectedItem := selector.handleInput(buf[0])
			if !continueLoop {
				// Clear screen and restore cursor
				fmt.Print(clearScreen + moveCursorHome + showCursor)
				
				if selectedItem == nil {
					return nil, nil
				}
				
				// Find the corresponding UnifiedSearchItem
				for _, item := range items {
					if item.ID == selectedItem.ID {
						return &item, nil
					}
				}
				return nil, nil
			}
		} else if n == 3 && buf[0] == keyEsc && buf[1] == '[' {
			// Handle arrow keys
			switch buf[2] {
			case 'A': // Up arrow
				if selector.selectedIndex > 0 {
					selector.selectedIndex--
				}
			case 'B': // Down arrow
				if selector.selectedIndex < len(selector.filteredItems)-1 {
					selector.selectedIndex++
				}
			}
		}

		selector.drawUnifiedSearchScreen(title)
	}
}

// showSimpleUnifiedFuzzyInput runs simple unified search without raw terminal
func showSimpleUnifiedFuzzyInput(items []UnifiedSearchItem, title string) (*UnifiedSearchItem, error) {
	fmt.Printf("\n" + strings.Repeat("=", 60) + "\n")
	fmt.Printf("%s (Simple Mode)\n", title)
	fmt.Printf(strings.Repeat("=", 60) + "\n\n")
	
	fmt.Printf("Available Items:\n\n")
	for i, item := range items {
		fmt.Printf("%d. %s\n", i+1, item.Name)
		fmt.Printf("   %s\n\n", item.Description)
	}
	
	fmt.Printf("Type number to select, 'q' to quit: ")
	var input string
	fmt.Scanln(&input)
	
	if input == "q" || input == "Q" {
		return nil, nil
	}
	
	// Try to parse as number
	if num, err := strconv.Atoi(input); err == nil && num >= 1 && num <= len(items) {
		return &items[num-1], nil
	}
	
	fmt.Printf("Invalid selection, please try again.\n")
	return showSimpleUnifiedFuzzyInput(items, title)
}