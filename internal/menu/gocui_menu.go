package menu

import (
	"fmt"
	"log"
	"os"
	"strings"

	"github.com/jroimartin/gocui"
	"golang.org/x/term"
	"opskit/internal/config"
	"opskit/internal/logger"
)

// NavigationLevel represents the current navigation level
type NavigationLevel int

const (
	LevelAll NavigationLevel = iota
	LevelCategory
)

// GocuiMenu represents the gocui-based menu system
type GocuiMenu struct {
	gui            *gocui.Gui
	tools          []config.Tool
	allItems       []UnifiedSearchItem
	filteredItems  []UnifiedSearchItem
	selectedIndex  int
	searchQuery    string
	result         *MenuItem
	shouldQuit     bool
	currentLevel   NavigationLevel
	selectedCategory *CategoryItem
}

// NewGocuiMenu creates a new gocui-based menu
func NewGocuiMenu(tools []config.Tool) *GocuiMenu {
	allItems := createUnifiedSearchItems(tools)
	return &GocuiMenu{
		tools:         tools,
		allItems:      allItems,
		filteredItems: allItems,
		selectedIndex: 0,
		searchQuery:   "",
		currentLevel:  LevelAll,
	}
}

// Run starts the gocui menu interface
func (m *GocuiMenu) Run() (*MenuItem, error) {
	var err error
	m.gui, err = gocui.NewGui(gocui.OutputNormal)
	if err != nil {
		return nil, fmt.Errorf("failed to create GUI: %w", err)
	}
	defer m.gui.Close()

	m.gui.SetManagerFunc(m.layout)
	m.gui.Cursor = true

	// Set keybindings
	if err := m.setKeybindings(); err != nil {
		return nil, fmt.Errorf("failed to set keybindings: %w", err)
	}

	// Start main loop
	if err := m.gui.MainLoop(); err != nil && err != gocui.ErrQuit {
		return nil, fmt.Errorf("GUI error: %w", err)
	}

	return m.result, nil
}

// layout defines the UI layout
func (m *GocuiMenu) layout(g *gocui.Gui) error {
	maxX, maxY := g.Size()

	// Header view
	if v, err := g.SetView("header", 0, 0, maxX-1, 2); err != nil {
		if err != gocui.ErrUnknownView {
			return err
		}
		v.Frame = false
		m.updateHeader(v)
	}

	// Search input view
	if v, err := g.SetView("search", 0, 3, maxX-1, 5); err != nil {
		if err != gocui.ErrUnknownView {
			return err
		}
		v.Title = " Search "
		v.Editable = true
		v.Editor = gocui.EditorFunc(m.searchEditor)
		fmt.Fprintf(v, "%s", m.searchQuery)
	}

	// Results view
	if v, err := g.SetView("results", 0, 6, maxX-1, maxY-1); err != nil {
		if err != gocui.ErrUnknownView {
			return err
		}
		v.Title = " Results "
		v.Highlight = true
		v.SelBgColor = gocui.ColorBlue
		v.SelFgColor = gocui.ColorWhite
		m.updateResults(v)
	}

	// Set initial focus to search
	if _, err := g.SetCurrentView("search"); err != nil {
		return err
	}

	return nil
}

// updateHeader updates the header information based on current navigation level
func (m *GocuiMenu) updateHeader(v *gocui.View) {
	v.Clear()
	switch m.currentLevel {
	case LevelAll:
		fmt.Fprintf(v, "🔍 OpsKit - Search Categories and Tools (Type to search, ↑↓ to navigate, Enter to select, Esc/q to quit)")
	case LevelCategory:
		categoryName := "Unknown"
		if m.selectedCategory != nil {
			categoryName = m.selectedCategory.Name
		}
		fmt.Fprintf(v, "🔍 OpsKit - Tools in %s (Type to search, ↑↓ to navigate, Enter to select, Esc to go back, q to quit)", categoryName)
	}
}

// searchEditor handles search input
func (m *GocuiMenu) searchEditor(v *gocui.View, key gocui.Key, ch rune, mod gocui.Modifier) {
	switch {
	case ch != 0 && mod == 0:
		// Add character to search query
		m.searchQuery += string(ch)
		v.Clear()
		fmt.Fprintf(v, "%s", m.searchQuery)
		m.filterItems()
		m.selectedIndex = 0
		m.updateResultsView()
	case key == gocui.KeySpace:
		// Add space to search query
		m.searchQuery += " "
		v.Clear()
		fmt.Fprintf(v, "%s", m.searchQuery)
		m.filterItems()
		m.selectedIndex = 0
		m.updateResultsView()
	case key == gocui.KeyBackspace || key == gocui.KeyBackspace2:
		// Remove last character from search query
		if len(m.searchQuery) > 0 {
			m.searchQuery = m.searchQuery[:len(m.searchQuery)-1]
			v.Clear()
			fmt.Fprintf(v, "%s", m.searchQuery)
			m.filterItems()
			m.selectedIndex = 0
			m.updateResultsView()
		}
	}
}

// filterItems filters items based on search query and current navigation level
func (m *GocuiMenu) filterItems() {
	var sourceItems []UnifiedSearchItem
	
	switch m.currentLevel {
	case LevelAll:
		sourceItems = m.allItems
	case LevelCategory:
		// Show only tools in the selected category
		sourceItems = []UnifiedSearchItem{}
		if m.selectedCategory != nil {
			for _, item := range m.allItems {
				if item.Type == "tool" && item.Tool != nil {
					toolGroup := item.Tool.Group
					if toolGroup == "" {
						toolGroup = item.Tool.Category
					}
					if toolGroup == "" {
						toolGroup = "other"
					}
					
					if strings.EqualFold(toolGroup, strings.ToLower(m.selectedCategory.Name)) {
						sourceItems = append(sourceItems, item)
					}
				}
			}
		}
	}

	if m.searchQuery == "" {
		m.filteredItems = sourceItems
		return
	}

	m.filteredItems = []UnifiedSearchItem{}
	query := strings.ToLower(m.searchQuery)

	for _, item := range sourceItems {
		// Search in name and description
		if strings.Contains(strings.ToLower(item.Name), query) ||
			strings.Contains(strings.ToLower(item.Description), query) {
			m.filteredItems = append(m.filteredItems, item)
		}
	}
}

// updateResults updates the results view
func (m *GocuiMenu) updateResults(v *gocui.View) {
	v.Clear()
	
	if len(m.filteredItems) == 0 {
		fmt.Fprintf(v, "No items found matching '%s'", m.searchQuery)
		return
	}

	for i, item := range m.filteredItems {
		marker := "  "
		if i == m.selectedIndex {
			marker = "▶ "
		}
		
		// Highlight search terms
		displayName := item.Name
		displayDesc := item.Description
		if m.searchQuery != "" {
			query := strings.ToLower(m.searchQuery)
			// Simple highlighting - replace with color codes would be better
			displayName = strings.ReplaceAll(displayName, query, fmt.Sprintf("[%s]", query))
			displayDesc = strings.ReplaceAll(displayDesc, query, fmt.Sprintf("[%s]", query))
		}
		
		fmt.Fprintf(v, "%s%s\n", marker, displayName)
		fmt.Fprintf(v, "    %s\n\n", displayDesc)
	}
}

// updateResultsView refreshes the results view
func (m *GocuiMenu) updateResultsView() {
	m.gui.Update(func(g *gocui.Gui) error {
		v, err := g.View("results")
		if err != nil {
			return err
		}
		m.updateResults(v)
		return nil
	})
}

// setKeybindings sets up keyboard shortcuts
func (m *GocuiMenu) setKeybindings() error {
	// Global keybindings
	if err := m.gui.SetKeybinding("", gocui.KeyCtrlC, gocui.ModNone, m.quit); err != nil {
		return err
	}
	if err := m.gui.SetKeybinding("", 'q', gocui.ModNone, m.quit); err != nil {
		return err
	}
	if err := m.gui.SetKeybinding("", gocui.KeyEsc, gocui.ModNone, m.goBack); err != nil {
		return err
	}

	// Navigation keybindings (available from any view)
	if err := m.gui.SetKeybinding("", gocui.KeyArrowUp, gocui.ModNone, m.navigateUp); err != nil {
		return err
	}
	if err := m.gui.SetKeybinding("", gocui.KeyArrowDown, gocui.ModNone, m.navigateDown); err != nil {
		return err
	}
	if err := m.gui.SetKeybinding("", gocui.KeyEnter, gocui.ModNone, m.selectItem); err != nil {
		return err
	}

	// Focus switching
	if err := m.gui.SetKeybinding("", gocui.KeyTab, gocui.ModNone, m.switchFocus); err != nil {
		return err
	}

	return nil
}

// navigateUp moves selection up
func (m *GocuiMenu) navigateUp(g *gocui.Gui, v *gocui.View) error {
	if len(m.filteredItems) == 0 {
		return nil
	}
	
	if m.selectedIndex > 0 {
		m.selectedIndex--
	} else {
		m.selectedIndex = len(m.filteredItems) - 1
	}
	m.updateResultsView()
	return nil
}

// navigateDown moves selection down
func (m *GocuiMenu) navigateDown(g *gocui.Gui, v *gocui.View) error {
	if len(m.filteredItems) == 0 {
		return nil
	}
	
	if m.selectedIndex < len(m.filteredItems)-1 {
		m.selectedIndex++
	} else {
		m.selectedIndex = 0
	}
	m.updateResultsView()
	return nil
}

// selectItem selects the current item
func (m *GocuiMenu) selectItem(g *gocui.Gui, v *gocui.View) error {
	if len(m.filteredItems) == 0 {
		return nil
	}

	selected := m.filteredItems[m.selectedIndex]
	
	if selected.Type == "category" {
		// Enter category level
		m.currentLevel = LevelCategory
		m.selectedCategory = selected.Category
		m.selectedIndex = 0
		m.searchQuery = "" // Clear search when drilling down
		
		// Update search view
		g.Update(func(g *gocui.Gui) error {
			searchView, err := g.View("search")
			if err == nil {
				searchView.Clear()
			}
			return nil
		})
		
		// Update all views
		m.filterItems()
		m.updateAllViews()
		return nil
	} else {
		// Tool selected, set result and quit
		m.result = &MenuItem{
			ID:          selected.Tool.ID,
			Name:        selected.Tool.Name,
			Description: selected.Tool.Description,
			Tool:        selected.Tool,
		}
		return gocui.ErrQuit
	}
}

// switchFocus switches focus between search and results
func (m *GocuiMenu) switchFocus(g *gocui.Gui, v *gocui.View) error {
	currentView := g.CurrentView()
	if currentView == nil {
		return nil
	}

	if currentView.Name() == "search" {
		_, err := g.SetCurrentView("results")
		return err
	} else {
		_, err := g.SetCurrentView("search")
		return err
	}
}

// goBack handles back navigation with Esc key
func (m *GocuiMenu) goBack(g *gocui.Gui, v *gocui.View) error {
	switch m.currentLevel {
	case LevelAll:
		// Already at top level, quit
		return gocui.ErrQuit
	case LevelCategory:
		// Go back to all items level
		m.currentLevel = LevelAll
		m.selectedCategory = nil
		m.selectedIndex = 0
		m.searchQuery = "" // Clear search when going back
		
		// Update search view
		g.Update(func(g *gocui.Gui) error {
			searchView, err := g.View("search")
			if err == nil {
				searchView.Clear()
			}
			return nil
		})
		
		// Update all views
		m.filterItems()
		m.updateAllViews()
		return nil
	}
	return nil
}

// updateAllViews updates all GUI views
func (m *GocuiMenu) updateAllViews() {
	m.gui.Update(func(g *gocui.Gui) error {
		// Update header
		if headerView, err := g.View("header"); err == nil {
			m.updateHeader(headerView)
		}
		
		// Update results
		if resultsView, err := g.View("results"); err == nil {
			m.updateResults(resultsView)
		}
		
		return nil
	})
}

// quit quits the application
func (m *GocuiMenu) quit(g *gocui.Gui, v *gocui.View) error {
	return gocui.ErrQuit
}

// ShowGocuiMenu shows the gocui-based menu and returns selected item
func ShowGocuiMenu(tools []config.Tool) (*MenuItem, error) {
	// Check if we're in a proper terminal environment
	if !isTerminalInteractive() {
		logger.Debug("Not in interactive terminal, gocui unavailable")
		return nil, fmt.Errorf("not in interactive terminal")
	}

	// Suppress gocui's default logging to avoid cluttering output
	log.SetOutput(&logger.NullWriter{})
	
	menu := NewGocuiMenu(tools)
	selected, err := menu.Run()
	
	// Restore normal logging
	log.SetOutput(logger.GetLogOutput())
	
	if err != nil {
		logger.Debug("Gocui menu error: %v", err)
		return nil, err
	}
	
	return selected, nil
}

// isTerminalInteractive checks if we're in an interactive terminal
func isTerminalInteractive() bool {
	// Check if stdin is a terminal
	if !term.IsTerminal(int(os.Stdin.Fd())) {
		return false
	}
	
	// Check if stdout is a terminal
	if !term.IsTerminal(int(os.Stdout.Fd())) {
		return false
	}
	
	return true
}