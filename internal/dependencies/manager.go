package dependencies

import (
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"strings"

	"opskit/internal/config"
	"opskit/internal/logger"
)

// Manager handles dependency checking and installation
type Manager struct {
	config *config.Config
	deps   *config.DependenciesConfig
}

// NewManager creates a new dependency manager
func NewManager(cfg *config.Config, deps *config.DependenciesConfig) *Manager {
	return &Manager{
		config: cfg,
		deps:   deps,
	}
}

// CheckDependencies checks multiple dependencies
func (m *Manager) CheckDependencies(depNames []string) error {
	missing := []string{}
	
	for _, depName := range depNames {
		if !m.CheckDependency(depName) {
			missing = append(missing, depName)
		}
	}
	
	if len(missing) > 0 {
		return m.InstallDependencies(missing)
	}
	
	return nil
}

// CheckDependency checks if a single dependency is available
func (m *Manager) CheckDependency(depName string) bool {
	dep, exists := m.deps.Dependencies[depName]
	if !exists {
		logger.Warning("Unknown dependency: %s", depName)
		return false
	}
	
	// Check if command exists
	cmd := exec.Command("which", dep.Check)
	if runtime.GOOS == "windows" {
		cmd = exec.Command("where", dep.Check)
	}
	
	err := cmd.Run()
	return err == nil
}

// InstallDependencies installs missing dependencies
func (m *Manager) InstallDependencies(depNames []string) error {
	logger.Info("Missing dependencies: %s", strings.Join(depNames, ", "))
	
	if !m.confirmInstallation(depNames) {
		return fmt.Errorf("dependency installation cancelled")
	}
	
	packageManager := m.detectPackageManager()
	if packageManager == "" {
		return m.showManualInstallation(depNames)
	}
	
	for _, depName := range depNames {
		if err := m.installDependency(depName, packageManager); err != nil {
			logger.Error("Failed to install %s: %v", depName, err)
			return m.showManualInstallation([]string{depName})
		}
	}
	
	// Verify installation
	for _, depName := range depNames {
		if !m.CheckDependency(depName) {
			logger.Error("Dependency %s still not available after installation", depName)
			return m.showManualInstallation([]string{depName})
		}
	}
	
	logger.Success("All dependencies installed successfully")
	return nil
}

// confirmInstallation prompts user for installation confirmation
func (m *Manager) confirmInstallation(depNames []string) bool {
	fmt.Printf("The following dependencies will be installed:\n")
	for _, depName := range depNames {
		if dep, exists := m.deps.Dependencies[depName]; exists {
			fmt.Printf("  - %s: %s\n", depName, dep.Description)
		}
	}
	
	fmt.Print("Continue with installation? (y/N): ")
	var response string
	fmt.Scanln(&response)
	
	return strings.ToLower(response) == "y" || strings.ToLower(response) == "yes"
}

// detectPackageManager detects the system package manager
func (m *Manager) detectPackageManager() string {
	managers := []string{"brew", "apt", "yum", "dnf", "pacman", "zypper"}
	
	for _, manager := range managers {
		if _, err := exec.LookPath(manager); err == nil {
			logger.Debug("Detected package manager: %s", manager)
			return manager
		}
	}
	
	logger.Debug("No supported package manager found")
	return ""
}

// installDependency installs a single dependency
func (m *Manager) installDependency(depName, packageManager string) error {
	dep, exists := m.deps.Dependencies[depName]
	if !exists {
		return fmt.Errorf("unknown dependency: %s", depName)
	}
	
	var packageName string
	if dep.Packages != nil {
		if name, exists := dep.Packages[packageManager]; exists {
			packageName = name
		} else {
			return fmt.Errorf("no package defined for %s", packageManager)
		}
	} else {
		packageName = dep.Package
	}
	
	if packageName == "" {
		return fmt.Errorf("no package name defined for %s", depName)
	}
	
	logger.Info("Installing %s using %s...", depName, packageManager)
	
	var cmd *exec.Cmd
	switch packageManager {
	case "brew":
		cmd = exec.Command("brew", "install", packageName)
	case "apt":
		cmd = exec.Command("sudo", "apt", "install", "-y", packageName)
	case "yum":
		cmd = exec.Command("sudo", "yum", "install", "-y", packageName)
	case "dnf":
		cmd = exec.Command("sudo", "dnf", "install", "-y", packageName)
	case "pacman":
		cmd = exec.Command("sudo", "pacman", "-S", "--noconfirm", packageName)
	case "zypper":
		cmd = exec.Command("sudo", "zypper", "install", "-y", packageName)
	default:
		return fmt.Errorf("unsupported package manager: %s", packageManager)
	}
	
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	
	return cmd.Run()
}

// showManualInstallation shows manual installation instructions
func (m *Manager) showManualInstallation(depNames []string) error {
	logger.Error("Automatic installation failed. Please install manually:")
	
	for _, depName := range depNames {
		if dep, exists := m.deps.Dependencies[depName]; exists {
			fmt.Printf("\n%s (%s):\n", depName, dep.Description)
			
			if dep.Packages != nil {
				fmt.Printf("Package names by system:\n")
				for manager, pkg := range dep.Packages {
					fmt.Printf("  %s: %s\n", manager, pkg)
				}
			} else if dep.Package != "" {
				fmt.Printf("Package: %s\n", dep.Package)
			}
			
			if dep.Docs != "" {
				fmt.Printf("Documentation: %s\n", dep.Docs)
			}
		}
	}
	
	return fmt.Errorf("manual installation required")
}