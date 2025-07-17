package dynamic

import (
	"fmt"
	"os"
	"os/exec"
	"strconv"
	"strings"

	"github.com/spf13/cobra"
	"github.com/spf13/pflag"
	"opskit/internal/config"
	"opskit/internal/executor"
	"opskit/internal/logger"
)

// CommandGenerator generates dynamic commands from tool configurations
type CommandGenerator struct {
	cfg      *config.Config
	executor *executor.Executor
}

// NewCommandGenerator creates a new command generator
func NewCommandGenerator(cfg *config.Config) *CommandGenerator {
	return &CommandGenerator{
		cfg:      cfg,
		executor: executor.NewExecutor(cfg),
	}
}

// GenerateCommands generates cobra commands for all tools
func (g *CommandGenerator) GenerateCommands() ([]*cobra.Command, error) {
	// Load tools configuration
	toolsConfig, err := g.loadToolsConfig()
	if err != nil {
		return nil, fmt.Errorf("failed to load tools config: %w", err)
	}

	var commands []*cobra.Command
	for _, tool := range toolsConfig.Tools {
		cmd := g.generateToolCommand(&tool)
		commands = append(commands, cmd)
	}

	return commands, nil
}

// loadToolsConfig loads tools configuration from file or remote
func (g *CommandGenerator) loadToolsConfig() (*config.ToolsConfig, error) {
	// Priority 1: Local file
	localPath := "./tools/tools.json"
	if g.fileExists(localPath) {
		logger.Debug("Using local tools config: %s", localPath)
		return config.LoadToolsConfig(localPath)
	}

	// Priority 2: Cached file
	cachedPath := fmt.Sprintf("%s/tools.json", g.cfg.ToolsDir())
	if g.fileExists(cachedPath) && !g.cfg.ShouldUpdate(cachedPath) {
		logger.Debug("Using cached tools config: %s", cachedPath)
		return config.LoadToolsConfig(cachedPath)
	}

	// Priority 3: Download from remote
	logger.Info("Downloading tools configuration...")
	return g.downloadToolsConfig()
}

// downloadToolsConfig downloads tools configuration from remote
func (g *CommandGenerator) downloadToolsConfig() (*config.ToolsConfig, error) {
	url := fmt.Sprintf("%s/tools/tools.json", g.cfg.GithubRepo)
	outputPath := fmt.Sprintf("%s/tools.json", g.cfg.ToolsDir())

	// Use downloader to download the file
	cmd := fmt.Sprintf("curl -sSL -o %s %s", outputPath, url)
	if err := g.runCommand(cmd); err != nil {
		return nil, fmt.Errorf("failed to download tools config: %w", err)
	}

	logger.Success("Downloaded tools configuration")
	return config.LoadToolsConfig(outputPath)
}

// generateToolCommand generates a cobra command for a tool
func (g *CommandGenerator) generateToolCommand(tool *config.Tool) *cobra.Command {
	logger.Debug("Generating tool command: %s", tool.ID)
	
	cmd := &cobra.Command{
		Use:   tool.ID,
		Short: tool.Name,
		Long:  tool.Description,
		RunE: func(cmd *cobra.Command, args []string) error {
			logger.Debug("Executing tool command: %s", tool.ID)
			
			// If no sub-command and no commands defined, execute tool directly
			if len(tool.Commands) == 0 {
				flags := g.extractFlags(cmd)
				return g.executor.ExecuteTool(tool, "", args, flags)
			}
			
			// If sub-commands exist but none specified, show help
			return cmd.Help()
		},
	}

	// Add global flags for the tool (if any)
	if len(tool.Args) > 0 {
		g.addFlags(cmd, tool.Args)
	}

	// Add sub-commands
	for _, subCmd := range tool.Commands {
		subCommand := g.generateSubCommand(tool, &subCmd)
		cmd.AddCommand(subCommand)
	}

	return cmd
}

// generateSubCommand generates a sub-command
func (g *CommandGenerator) generateSubCommand(tool *config.Tool, command *config.Command) *cobra.Command {
	logger.Debug("Generating sub-command: %s.%s", tool.ID, command.Name)
	
	cmd := &cobra.Command{
		Use:   command.Name,
		Short: command.Description,
		RunE: func(cmd *cobra.Command, args []string) error {
			logger.Debug("Executing command: %s.%s", tool.ID, command.Name)
			logger.Debug("Command Args definition: %+v", command.Args)
			
			// Validate required arguments
			if err := g.validateArgs(command.Args, args); err != nil {
				return err
			}

			// Extract flags
			flags := g.extractFlags(cmd)

			// Execute tool with sub-command
			return g.executor.ExecuteTool(tool, command.Name, args, flags)
		},
	}

	// Add arguments usage
	if len(command.Args) > 0 {
		var usageParts []string
		for _, arg := range command.Args {
			if arg.Required {
				usageParts = append(usageParts, fmt.Sprintf("<%s>", arg.Name))
			} else {
				usageParts = append(usageParts, fmt.Sprintf("[%s]", arg.Name))
			}
		}
		cmd.Use += " " + strings.Join(usageParts, " ")
	}

	// Add flags
	for _, flag := range command.Flags {
		g.addFlag(cmd, &flag)
	}

	return cmd
}

// addFlags adds argument flags to command
func (g *CommandGenerator) addFlags(cmd *cobra.Command, args []config.Argument) {
	for _, arg := range args {
		flag := config.Flag{
			Name:        arg.Name,
			Description: arg.Description,
			Type:        "string",
			Default:     arg.Default,
		}
		g.addFlag(cmd, &flag)
	}
}

// addFlag adds a single flag to command
func (g *CommandGenerator) addFlag(cmd *cobra.Command, flag *config.Flag) {
	switch flag.Type {
	case "bool":
		defaultVal := flag.Default == "true"
		if flag.Short != "" {
			cmd.Flags().BoolP(flag.Name, flag.Short, defaultVal, flag.Description)
		} else {
			cmd.Flags().Bool(flag.Name, defaultVal, flag.Description)
		}
	case "int":
		defaultVal := 0
		if flag.Default != "" {
			if val, err := strconv.Atoi(flag.Default); err == nil {
				defaultVal = val
			}
		}
		if flag.Short != "" {
			cmd.Flags().IntP(flag.Name, flag.Short, defaultVal, flag.Description)
		} else {
			cmd.Flags().Int(flag.Name, defaultVal, flag.Description)
		}
	default: // string
		if flag.Short != "" {
			cmd.Flags().StringP(flag.Name, flag.Short, flag.Default, flag.Description)
		} else {
			cmd.Flags().String(flag.Name, flag.Default, flag.Description)
		}
	}
}

// extractFlags extracts flag values from command
func (g *CommandGenerator) extractFlags(cmd *cobra.Command) map[string]interface{} {
	flags := make(map[string]interface{})
	
	cmd.Flags().VisitAll(func(flag *pflag.Flag) {
		if flag.Changed {
			switch flag.Value.Type() {
			case "bool":
				if val, err := strconv.ParseBool(flag.Value.String()); err == nil {
					flags[flag.Name] = val
				}
			case "int":
				if val, err := strconv.Atoi(flag.Value.String()); err == nil {
					flags[flag.Name] = val
				}
			default:
				flags[flag.Name] = flag.Value.String()
			}
		}
	})
	
	return flags
}

// validateArgs validates required arguments
func (g *CommandGenerator) validateArgs(argDefs []config.Argument, args []string) error {
	requiredCount := 0
	for _, arg := range argDefs {
		if arg.Required {
			requiredCount++
		}
	}

	logger.Debug("validateArgs: argDefs=%d, requiredCount=%d, args=%d", len(argDefs), requiredCount, len(args))

	if len(args) < requiredCount {
		return fmt.Errorf("insufficient arguments: expected at least %d, got %d", requiredCount, len(args))
	}

	return nil
}

// fileExists checks if a file exists
func (g *CommandGenerator) fileExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}

// runCommand runs a shell command
func (g *CommandGenerator) runCommand(cmdStr string) error {
	cmd := exec.Command("sh", "-c", cmdStr)
	return cmd.Run()
}