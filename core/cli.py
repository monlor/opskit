"""
CLI Module

Simple command line interface for OpsKit providing:
- Tool discovery and listing
- Basic tool execution
- Configuration management
- System updates
"""

import os
import sys
import subprocess
from typing import Dict, List, Optional
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.align import Align
    rich_available = True
except ImportError:
    rich_available = False

from .env import env, get_tool_temp_dir, load_tool_env, get_config_summary, is_first_run, initialize_env_file
from .platform_utils import PlatformUtils
from .dependency_manager import DependencyManager
import yaml


class OpsKitCLI:
    """Simple command line interface for OpsKit"""
    
    def __init__(self):
        """Initialize CLI interface"""
        self.console = Console() if rich_available else None
        
        # Get OpsKit root directory
        current_file = Path(__file__).resolve()
        self.opskit_root = current_file.parent.parent
        self.tools_dir = self.opskit_root / 'tools'
        
        # Tool cache
        self._tool_cache = None
        
        # Initialize managers
        self.platform_utils = PlatformUtils()
        self.dependency_manager = DependencyManager(self.opskit_root)
    
    def _print(self, message: str, style: Optional[str] = None) -> None:
        """Print message with optional styling"""
        if self.console and rich_available:
            if style:
                self.console.print(message, style=style)
            else:
                self.console.print(message)
        else:
            print(message)
    
    def _print_panel(self, content: str, title: str, style: str = "blue") -> None:
        """Print content in a panel"""
        if self.console and rich_available:
            panel = Panel(content, title=title, border_style=style)
            self.console.print(panel)
        else:
            print(f"\n=== {title} ===")
            print(content)
            print("=" * (len(title) + 8))
    
    def _input(self, prompt: str, default: Optional[str] = None) -> str:
        """Get user input with optional default"""
        if rich_available and self.console:
            return Prompt.ask(prompt, default=default) if default else Prompt.ask(prompt)
        else:
            full_prompt = f"{prompt}"
            if default:
                full_prompt += f" [{default}]"
            full_prompt += ": "
            result = input(full_prompt).strip()
            return result if result else (default or "")
    
    def _confirm(self, prompt: str, default: bool = False) -> bool:
        """Get yes/no confirmation from user"""
        if rich_available and self.console:
            return Confirm.ask(prompt, default=default)
        else:
            full_prompt = f"{prompt} ({'Y/n' if default else 'y/N'}): "
            result = input(full_prompt).strip().lower()
            if not result:
                return default
            return result in ['y', 'yes', '1', 'true']
    
    def _print_tool_header(self, tool_name: str, version: str, description: str, tool_type: str, category: str) -> None:
        """Print a standardized tool header"""
        if self.console and rich_available:
            # Rich formatted header
            # Create header content with tool information
            header_content = f"[bold blue]{tool_name}[/bold blue] [dim]v{version}[/dim]\n"
            header_content += f"[dim]{description}[/dim]\n"
            header_content += f"[yellow]Category:[/yellow] {category.title()}  [yellow]Type:[/yellow] {tool_type.upper()}"
            
            # Create panel with header
            panel = Panel(
                Align.center(header_content),
                title="🚀 OpsKit Tool",
                title_align="left",
                border_style="green",
                padding=(1, 2)
            )
            self.console.print(panel)
            self.console.print()  # Add spacing after header
        else:
            # Plain text header for non-rich environments
            separator = "=" * 60
            self._print(separator)
            self._print(f"🚀 OpsKit Tool: {tool_name} v{version}")
            self._print(f"Description: {description}")
            self._print(f"Category: {category.title()}  |  Type: {tool_type.upper()}")
            self._print(separator)
            self._print("")  # Add spacing after header
    
    def discover_tools(self, force_refresh: bool = False) -> Dict[str, List[Dict[str, str]]]:
        """
        Discover all available tools
        
        Returns:
            Dictionary of categories with tool information
        """
        if self._tool_cache is not None and not force_refresh:
            return self._tool_cache
        
        tools = {}
        
        if not self.tools_dir.exists():
            self._tool_cache = {}
            return {}
        
        # Scan tool categories
        for category_dir in self.tools_dir.iterdir():
            if not category_dir.is_dir() or category_dir.name.startswith('.'):
                continue
            
            category_name = category_dir.name
            category_tools = []
            
            # Scan tools in category
            for tool_dir in category_dir.iterdir():
                if not tool_dir.is_dir() or tool_dir.name.startswith('.'):
                    continue
                
                tool_info = self._parse_tool_info(tool_dir)
                if tool_info:
                    category_tools.append(tool_info)
            
            if category_tools:
                tools[category_name] = sorted(category_tools, key=lambda x: x['name'])
        
        self._tool_cache = tools
        return tools
    
    def _parse_tool_info(self, tool_dir: Path) -> Optional[Dict[str, str]]:
        """Parse tool information from directory"""
        try:
            tool_name = tool_dir.name
            category = tool_dir.parent.name
            
            # Look for main executable
            main_file = None
            for candidate in ['main.py', 'main.sh', f'{tool_name}.py', f'{tool_name}.sh']:
                candidate_path = tool_dir / candidate
                if candidate_path.exists():
                    main_file = candidate
                    break
            
            if not main_file:
                return None
            
            # Get version and description from tools.yaml
            version = "1.0.0"  # default version
            description = "No description available"
            dependencies = []  # default no dependencies
            
            # Load tools.yaml for metadata
            tools_yaml_path = self.opskit_root / 'config' / 'tools.yaml'
            if tools_yaml_path.exists():
                try:
                    with open(tools_yaml_path, 'r', encoding='utf-8') as f:
                        tools_config = yaml.safe_load(f)
                    
                    if tools_config and 'tools' in tools_config:
                        tool_info_config = tools_config['tools'].get(category, {}).get(tool_name, {})
                        if tool_info_config:
                            version = tool_info_config.get('version', version)
                            description = tool_info_config.get('description', description)
                            # Extract dependencies from tools.yaml
                            dependencies = tool_info_config.get('dependencies', [])
                except Exception:
                    pass
            
            # Check for requirements and env file
            has_python_deps = (tool_dir / 'requirements.txt').exists()
            has_env_file = (tool_dir / '.env').exists()
            
            # Determine tool type
            tool_type = 'python' if main_file.endswith('.py') else 'shell'
            
            return {
                'name': tool_name,
                'path': str(tool_dir),
                'main_file': main_file,
                'description': description,
                'version': version,
                'type': tool_type,
                'has_python_deps': has_python_deps,
                'has_env_file': has_env_file,
                'category': category,
                'dependencies': dependencies
            }
        
        except Exception:
            return None
    
    def interactive_mode(self) -> None:
        """Simple interactive mode - just show available tools and let user pick one"""
        # Check if this is first run
        if is_first_run():
            self._print("Welcome to OpsKit! 🚀", "bold green")
            self._print("Let's set up your configuration first.", "yellow")
            success = self.initial_setup()
            if not success:
                self._print("Setup cancelled. You can configure later with: opskit config", "yellow")
                return

        # Show available tools
        self._print("Available tools:", "bold blue")
        self.list_tools()
        
        self._print("\nUse 'opskit run <tool-name>' to run a specific tool", "yellow")
        self._print("Use 'opskit list' to see this list again", "yellow")
        self._print("Use 'opskit config' for configuration", "yellow")
    
    def list_tools(self, category: Optional[str] = None) -> None:
        """List all tools or tools in a specific category"""
        tools = self.discover_tools()
        
        if not tools:
            self._print("No tools found.")
            return
        
        if category and category in tools:
            # Show specific category
            self._print(f"Tools in category '{category}':")
            for tool in tools[category]:
                self._print(f"  {tool['name']} - {tool['description']}")
        else:
            # Show all categories
            if rich_available and self.console:
                table = Table(show_header=True, header_style="bold blue")
                table.add_column("Category", width=15)
                table.add_column("Tool", width=20)
                table.add_column("Type", width=8)
                table.add_column("Description")
                
                for cat_name, cat_tools in tools.items():
                    for i, tool in enumerate(cat_tools):
                        category_display = cat_name if i == 0 else ""
                        table.add_row(
                            category_display,
                            tool['name'],
                            tool['type'],
                            tool['description'][:60] + ('...' if len(tool['description']) > 60 else '')
                        )
                
                self.console.print(table)
            else:
                for cat_name, cat_tools in tools.items():
                    print(f"\n{cat_name}:")
                    for tool in cat_tools:
                        print(f"  {tool['name']} ({tool['type']}) - {tool['description']}")
    
    def run_tool(self, tool_name: str, tool_args: List[str] = None) -> int:
        """Run a specific tool with environment variable injection and dependency management"""
        if tool_args is None:
            tool_args = []
        
        # Find the tool
        tools = self.discover_tools()
        found_tool = None
        
        for category, cat_tools in tools.items():
            for tool in cat_tools:
                if tool['name'] == tool_name:
                    found_tool = tool
                    break
            if found_tool:
                break
        
        if not found_tool:
            self._print(f"Tool '{tool_name}' not found", "red")
            return 1
        
        # Display comprehensive tool header
        tool_version = found_tool.get('version', '1.0.0')
        tool_description = found_tool.get('description', 'No description available')
        tool_type = found_tool.get('type', 'unknown')
        tool_category = found_tool.get('category', 'uncategorized')
        
        # Print formatted tool header
        self._print_tool_header(tool_name, tool_version, tool_description, tool_type, tool_category)
        
        try:
            # 1. Inject environment variables
            tool_path = found_tool['path']
            
            # Create tool-specific temporary directory
            tool_temp_dir = get_tool_temp_dir(found_tool['name'])
            
            # Inject environment variables with tool temp dir and base path
            env_vars = load_tool_env(tool_path)
            env_vars['OPSKIT_TOOL_TEMP_DIR'] = tool_temp_dir
            env_vars['OPSKIT_BASE_PATH'] = str(self.opskit_root)
            
            # Inject user's working directory (where opskit command was executed)
            # This allows tools to know the user's actual working directory, not the tool's directory
            env_vars['OPSKIT_WORKING_DIR'] = os.getcwd()
            
            # Inject tool metadata for shell tools
            env_vars['TOOL_NAME'] = found_tool.get('display_name', found_tool['name'])
            env_vars['TOOL_VERSION'] = tool_version
            
            # Set environment variables in current process
            for key, value in env_vars.items():
                os.environ[key] = str(value)
            
            # 2. Run tool with dependency management
            return self.dependency_manager.run_tool_with_dependencies(found_tool, tool_args)
            
        except Exception as e:
            self._print(f"❌ Error running tool: {e}", "red")
            return 1
    
    def search_tools(self, query: str) -> None:
        """Search tools by name or description"""
        tools = self.discover_tools()
        matches = []
        
        query_lower = query.lower()
        
        for category, cat_tools in tools.items():
            for tool in cat_tools:
                if (query_lower in tool['name'].lower() or 
                    query_lower in tool['description'].lower()):
                    matches.append(tool)
        
        if not matches:
            self._print(f"No tools found matching '{query}'")
            return
        
        self._print(f"Found {len(matches)} tools matching '{query}':")
        
        if rich_available and self.console:
            table = Table(show_header=True, header_style="bold blue")
            table.add_column("Name", width=20)
            table.add_column("Category", width=15)
            table.add_column("Type", width=8)
            table.add_column("Description")
            
            for tool in matches:
                table.add_row(
                    tool['name'],
                    tool['category'],
                    tool['type'],
                    tool['description'][:60] + ('...' if len(tool['description']) > 60 else '')
                )
            
            self.console.print(table)
        else:
            for tool in matches:
                print(f"{tool['name']} ({tool['category']}) - {tool['description']}")
    
    def show_status(self) -> None:
        """Show system status"""
        # Get system information
        system_info = self.platform_utils.get_system_info()
        config_summary = get_config_summary()
        tools = self.discover_tools()
        
        status_info = f"OpsKit Status Report\n\n"
        status_info += f"System Information:\n"
        status_info += f"  Platform: {system_info.get('platform', 'Unknown')}\n"
        status_info += f"  Python: {system_info.get('python_version', 'Unknown')}\n"
        
        if 'package_managers' in system_info:
            managers = system_info['package_managers']
            status_info += f"  Package Managers: {', '.join(managers) if managers else 'None detected'}\n"
        
        status_info += f"\nOpsKit Information:\n"
        status_info += f"  Root Directory: {self.opskit_root}\n"
        status_info += f"  Configuration: {'✓' if config_summary['main_config_exists'] else '✗'}\n"
        status_info += f"  Tool Categories: {len(tools)}\n"
        status_info += f"  Total Tools: {sum(len(cat_tools) for cat_tools in tools.values())}\n"
        status_info += f"  Tool Configs: {config_summary['tool_configs_count']}\n"
        
        self._print_panel(status_info, "System Status", "green")
    
    def settings_wizard(self, is_first_run_setup: bool = False) -> bool:
        """
        Settings configuration wizard
        
        Args:
            is_first_run_setup: True if this is first run setup, False for settings menu
        
        Returns:
            True if configuration was successful, False otherwise
        """
        if is_first_run_setup:
            self._print("\n🔧 Initial Setup", "bold cyan")
            self._print("Configure basic OpsKit settings:", "dim")
        else:
            self._print("\n⚙️  Settings Configuration", "bold cyan")
            self._print("Update your OpsKit settings:", "dim")
        
        # Basic setup - no complex configuration needed
        
        # Save basic configuration
        action_text = "Creating" if is_first_run_setup else "Updating"
        self._print(f"\n📝 {action_text} configuration...", "blue")
        success = initialize_env_file()
        
        if success:
            self._print(f"✅ Configuration {action_text.lower()} successfully!", "green")
            self._print(f"  - Config file: data/.env")
            
            if is_first_run_setup:
                self._print("\nYou can access settings later with: opskit config", "dim")
            
            return True
        else:
            self._print(f"❌ Failed to {action_text.lower()} configuration file", "red")
            return False
    
    def initial_setup(self) -> bool:
        """Initial setup wizard for first-time users"""
        return self.settings_wizard(is_first_run_setup=True)
    
    def configuration_menu(self) -> None:
        """Configuration management menu"""
        # Show current configuration
        config_info = f"Current Settings:\n"
        config_info += f"  Version: {env.version}\n"
        config_info += f"  Cache Directory: {env.cache_dir}\n"
        config_info += f"  Configuration file: data/.env"
        
        self._print_panel(config_info, "📋 Current Configuration", "cyan")
        
        # Ask if user wants to modify settings
        if self._confirm("Modify settings?", False):
            self.settings_wizard(is_first_run_setup=False)
    
    def update_opskit(self) -> None:
        """Update OpsKit using git pull"""
        if not (self.opskit_root / '.git').exists():
            self._print("OpsKit is not a git repository. Cannot update automatically.", "red")
            return
        
        if self._confirm("Update OpsKit to the latest version?"):
            try:
                self._print("Updating OpsKit...", "blue")
                
                # Run git pull
                result = subprocess.run(
                    ['git', 'pull'],
                    cwd=self.opskit_root,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    self._print("OpsKit updated successfully!", "green")
                    if result.stdout.strip():
                        self._print(f"Git output: {result.stdout}", "dim")
                    
                    # Clear tool cache to reflect any changes
                    self._tool_cache = None
                else:
                    self._print(f"Update failed: {result.stderr}", "red")
            
            except subprocess.TimeoutExpired:
                self._print("Update timed out. Please try again.", "red")
            except Exception as e:
                self._print(f"Update error: {e}", "red")
    
    def generate_completion(self, shell: str) -> None:
        """Generate shell completion script using Click's built-in functionality"""
        from pathlib import Path
        
        # Get the absolute path to the opskit script
        opskit_path = Path(__file__).parent.parent / "bin" / "opskit"
        
        if shell == 'bash':
            print(f"""# OpsKit Bash completion
# Add this to your ~/.bashrc:
# eval "$(_OPSKIT_COMPLETE=bash_source opskit)"

eval "$(_OPSKIT_COMPLETE=bash_source {opskit_path})"
""")
        
        elif shell == 'zsh':
            print(f"""# OpsKit Zsh completion  
# Add this to your ~/.zshrc:
# eval "$(_OPSKIT_COMPLETE=zsh_source opskit)"

eval "$(_OPSKIT_COMPLETE=zsh_source {opskit_path})"
""")
        
        elif shell == 'fish':
            print(f"""# OpsKit Fish completion
# Add this to ~/.config/fish/completions/opskit.fish:
# eval (env _OPSKIT_COMPLETE=fish_source opskit)

eval (env _OPSKIT_COMPLETE=fish_source {opskit_path})
""")
    
    def _show_help(self) -> None:
        """Show help information"""
        help_text = """
OpsKit Interactive Mode Help

Navigation:
- Use number keys to select menu options
- Type tool names directly when browsing tools
- Press Ctrl+C to exit at any time

Commands:
- Browse tools: Explore tools organized by category
- Search tools: Find tools by name or description
- Configuration: Manage OpsKit and tool settings
- System status: Check system health and information
- Update: Update OpsKit to the latest version

Tool Management:
- Tools are organized in categories (database, network, system, etc.)
- Each tool has its own configuration and dependencies
- Dependencies are automatically managed when running tools

For more information, visit: https://github.com/monlor/opskit
"""
        self._print_panel(help_text.strip(), "Help", "cyan")