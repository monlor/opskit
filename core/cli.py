"""
CLI Module

Interactive command line interface for OpsKit including:
- Interactive tool browsing and selection
- Tool configuration management
- System status display and health checking
- Git-based updates and maintenance
"""

import os
import sys
import subprocess
from typing import Dict, List, Optional, Tuple
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.prompt import Prompt, Confirm
    from rich.progress import track
    from rich.align import Align
    rich_available = True
except ImportError:
    rich_available = False

try:
    from prompt_toolkit import prompt
    from prompt_toolkit.application import Application
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout import Layout, HSplit, VSplit
    from prompt_toolkit.layout.containers import Window
    from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.widgets import SearchToolbar, Frame
    from prompt_toolkit.styles import Style
    from prompt_toolkit.formatted_text import FormattedText
    from prompt_toolkit.filters import Condition
    import threading
    import time
    prompt_toolkit_available = True
except ImportError:
    prompt_toolkit_available = False

from .env import env, get_tool_temp_dir, load_tool_env, get_config_summary, is_first_run, initialize_env_file
from .platform_utils import PlatformUtils
from .dependency_manager import DependencyManager
from .theme import theme_manager
import yaml


class OpsKitCLI:
    """Interactive command line interface for OpsKit"""
    
    def __init__(self):
        """Initialize CLI interface"""
        self.console = Console() if rich_available else None
        
        # Set up logging
        import logging
        self.logger = logging.getLogger(__name__)
        
        # Get OpsKit root directory
        current_file = Path(__file__).resolve()
        self.opskit_root = current_file.parent.parent
        self.tools_dir = self.opskit_root / 'tools'
        
        # Tool cache
        self._tool_cache = None
        self._tool_categories = None
        self._yaml_tools = None
        
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
        
        except Exception as e:
            self.logger.debug(f"Error parsing tool {tool_dir}: {e}")
            return None
    
    def interactive_mode(self) -> None:
        """Enter interactive CLI mode with list view, pagination and real-time search"""
        if not prompt_toolkit_available:
            self._print("Error: prompt_toolkit is required for interactive mode.", "red")
            self._print("Please install it with: pip install prompt-toolkit", "yellow")
            return
        
        # Check if this is first run - if so, go directly to initial setup
        if is_first_run():
            self._print("Welcome to OpsKit! 🚀", "bold green")
            self._print("Let's set up your configuration first.", "yellow")
            success = self.initial_setup()
            if not success:
                self._print("Setup cancelled. You can run settings later with Ctrl+S.", "yellow")
                return
        
        # Load and prepare tools
        tools = self.discover_tools()
        if not tools:
            self._print("No tools found. Please check your OpsKit installation.", "yellow")
            return
        
        # Flatten and sort tools by name
        all_tools = []
        for category, cat_tools in tools.items():
            for tool in cat_tools:
                tool['full_name'] = f"{tool['name']} ({tool['category']})"
                all_tools.append(tool)
        
        all_tools.sort(key=lambda x: x['name'])
        
        # Application state
        class AppState:
            def __init__(self):
                self.tools = all_tools
                self.filtered_tools = all_tools[:]
                self.selected_index = 0
                self.page_size = 10
                self.current_page = 0
                self.search_text = ""
                self.show_help = False
        
        state = AppState()
        
        # Search buffer
        search_buffer = Buffer()
        
        def filter_tools():
            """Filter tools based on search text"""
            search_term = search_buffer.text.lower()
            if not search_term:
                state.filtered_tools = state.tools[:]
            else:
                state.filtered_tools = [
                    tool for tool in state.tools
                    if (search_term in tool['name'].lower() or 
                        search_term in tool['description'].lower() or
                        search_term in tool['category'].lower())
                ]
            
            # Reset selection
            state.selected_index = 0
            state.current_page = 0
        
        def get_tool_list_text():
            """Generate formatted tool list"""
            if not state.filtered_tools:
                return FormattedText([('class:no-results', 'No tools found')])
            
            start_idx = state.current_page * state.page_size
            end_idx = min(start_idx + state.page_size, len(state.filtered_tools))
            page_tools = state.filtered_tools[start_idx:end_idx]
            
            result = []
            
            # Header info
            total_tools = len(state.filtered_tools)
            current_page_num = state.current_page + 1
            total_pages = (total_tools + state.page_size - 1) // state.page_size
            
            result.append(('class:header', f'OpsKit Tools ({total_tools} found) - Page {current_page_num}/{total_pages}\n'))
            result.append(('class:separator', '-' * 80 + '\n'))
            
            # Tool list
            for i, tool in enumerate(page_tools):
                global_idx = start_idx + i
                prefix = '> ' if global_idx == state.selected_index else '  '
                style = 'class:selected' if global_idx == state.selected_index else 'class:normal'
                
                # Format: > name (category) - description
                name_part = f"{prefix}{tool['name']}"
                category_part = f" ({tool['category']})"
                desc_part = f" - {tool['description'][:50]}{'...' if len(tool['description']) > 50 else ''}"
                
                result.extend([
                    (style, name_part),
                    ('class:category', category_part),
                    ('class:description', desc_part),
                    ('', '\n')
                ])
            
            # Footer with keybindings
            result.append(('class:separator', '-' * 80 + '\n'))
            result.extend([
                ('class:keybind', '↑↓: Navigate  '),
                ('class:keybind', 'PgUp/PgDn: Page  '),
                ('class:keybind', 'Enter: Select  '),
                ('class:keybind', 'Ctrl+S: Settings  '),
                ('class:keybind', 'Ctrl+C: Exit')
            ])
            
            return FormattedText(result)
        
        # Key bindings
        kb = KeyBindings()
        
        @kb.add('up')
        def move_up(event):
            if state.selected_index > 0:
                state.selected_index -= 1
                # Check if we need to go to previous page
                if state.selected_index < state.current_page * state.page_size:
                    state.current_page -= 1
        
        @kb.add('down')
        def move_down(event):
            if state.selected_index < len(state.filtered_tools) - 1:
                state.selected_index += 1
                # Check if we need to go to next page
                if state.selected_index >= (state.current_page + 1) * state.page_size:
                    state.current_page += 1
        
        @kb.add('pageup')
        def page_up(event):
            if state.current_page > 0:
                state.current_page -= 1
                state.selected_index = min(state.selected_index, 
                                          (state.current_page + 1) * state.page_size - 1)
        
        @kb.add('pagedown')
        def page_down(event):
            max_page = (len(state.filtered_tools) - 1) // state.page_size
            if state.current_page < max_page:
                state.current_page += 1
                state.selected_index = max(state.selected_index,
                                          state.current_page * state.page_size)
        
        @kb.add('enter')
        def select_tool(event):
            if state.filtered_tools and 0 <= state.selected_index < len(state.filtered_tools):
                selected_tool = state.filtered_tools[state.selected_index]
                event.app.exit(result=selected_tool)
        
        @kb.add('c-s')
        def show_settings(event):
            event.app.exit(result='settings')
        
        @kb.add('c-c')
        def exit_app(event):
            event.app.exit(result='exit')
        
        @kb.add('?')
        def toggle_help(event):
            state.show_help = not state.show_help
        
        # Update search when buffer changes
        def on_search_buffer_change(buffer):
            filter_tools()
        
        search_buffer.on_text_changed += on_search_buffer_change
        
        # Layout
        search_field = Window(
            BufferControl(buffer=search_buffer),
            height=1,
            wrap_lines=False,
        )
        
        tool_list_window = Window(
            FormattedTextControl(
                get_tool_list_text,
                focusable=True,
                show_cursor=False,
            ),
            wrap_lines=False,
        )
        
        root_container = HSplit([
            Window(
                FormattedTextControl(FormattedText([('class:title', 'OpsKit - Unified Operations Management')])),
                height=1
            ),
            Window(
                FormattedTextControl(FormattedText([('class:search-label', 'Search: ')])),
                height=1
            ),
            search_field,
            Window(height=1),  # Separator
            tool_list_window,
        ])
        
        # Style - use theme manager for adaptive colors
        style = theme_manager.get_style(env.ui_theme)
        
        # Create and run application
        app = Application(
            layout=Layout(root_container),
            key_bindings=kb,
            style=style,
            full_screen=True,
        )
        
        try:
            result = app.run()
            
            if result == 'exit':
                self._print("Goodbye!", "green")
            elif result == 'settings':
                self.configuration_menu()
            elif isinstance(result, dict):  # Selected tool
                # Directly run the tool instead of showing details
                tool_name = result['name']
                exit_code = self.run_tool(tool_name)
                if exit_code == 0:
                    self._print(f"\n{tool_name} completed successfully", "green")
                else:
                    self._print(f"\n{tool_name} exited with code {exit_code}", "yellow")
        
        except KeyboardInterrupt:
            self._print("\nGoodbye!", "green")
    
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
            
            # Inject tool metadata for shell tools
            env_vars['TOOL_NAME'] = found_tool.get('display_name', found_tool['name'])
            env_vars['TOOL_VERSION'] = tool_version
            
            if env_vars:
                self.logger.debug(f"Loaded {len(env_vars)} environment variables")
                for key, value in list(env_vars.items())[:5]:  # Show first 5
                    self.logger.debug(f"  {key}={value}")
                if len(env_vars) > 5:
                    self.logger.debug(f"  ... and {len(env_vars) - 5} more")
            
            # Set environment variables in current process
            for key, value in env_vars.items():
                os.environ[key] = str(value)
            
            # 2. Run tool with dependency management
            return self.dependency_manager.run_tool_with_dependencies(found_tool, tool_args)
            
        except Exception as e:
            self._print(f"❌ Error running tool: {e}", "red")
            self.logger.debug("Full traceback:", exc_info=True)
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
        
        # Get current values (defaults for first run, current values for settings)
        if is_first_run_setup:
            current_log_enabled = True  # Default for first run
            current_theme = 'auto'      # Default for first run
        else:
            current_log_enabled = env.log_file_enabled
            current_theme = env.ui_theme
        
        # 1. Ask about file logging
        self._print("\n1. Logging Configuration", "bold yellow")
        if not is_first_run_setup:
            self._print(f"   Current: File logging is {'enabled' if current_log_enabled else 'disabled'}", "dim")
        
        log_to_file = self._confirm(
            "Save logs to file? (recommended for debugging)", 
            current_log_enabled
        )
        
        # 2. Ask about theme
        self._print("\n2. Theme Configuration", "bold yellow")
        if not is_first_run_setup:
            theme_info = theme_manager.get_theme_info(current_theme)
            self._print(f"   Current: {current_theme} (active: {theme_info['active_theme']})", "dim")
        
        self._print("Theme options:")
        self._print("  auto  - automatically detect terminal background")
        self._print("  light - for light terminal backgrounds")
        self._print("  dark  - for dark terminal backgrounds")
        
        theme_choice = self._input("Choose theme", current_theme).lower()
        if theme_choice not in ['auto', 'light', 'dark']:
            theme_choice = current_theme
        
        # 3. Save configuration
        action_text = "Creating" if is_first_run_setup else "Updating"
        self._print(f"\n📝 {action_text} configuration...", "blue")
        success = initialize_env_file(log_to_file=log_to_file, theme=theme_choice)
        
        if success:
            self._print(f"✅ Configuration {action_text.lower()} successfully!", "green")
            self._print(f"  - File logging: {'enabled' if log_to_file else 'disabled'}")
            self._print(f"  - Theme: {theme_choice}")
            self._print(f"  - Config file: data/.env")
            
            if not is_first_run_setup:
                # Show what changed
                changes = []
                if log_to_file != current_log_enabled:
                    changes.append(f"file logging: {current_log_enabled} → {log_to_file}")
                if theme_choice != current_theme:
                    changes.append(f"theme: {current_theme} → {theme_choice}")
                
                if changes:
                    self._print(f"\nChanges made:", "yellow")
                    for change in changes:
                        self._print(f"  - {change}")
                else:
                    self._print("No changes made.", "dim")
            else:
                self._print("\nYou can access settings later with Ctrl+S", "dim")
            
            return True
        else:
            self._print(f"❌ Failed to {action_text.lower()} configuration file", "red")
            return False
    
    def initial_setup(self) -> bool:
        """Initial setup wizard for first-time users"""
        return self.settings_wizard(is_first_run_setup=True)
    
    def configuration_menu(self) -> None:
        """Configuration management menu"""
        # Show current configuration first
        theme_info = theme_manager.get_theme_info(env.ui_theme)
        
        config_info = f"Current Settings:\n"
        config_info += f"  Version: {env.version}\n"
        config_info += f"  File Logging: {'enabled' if env.log_file_enabled else 'disabled'}\n"
        config_info += f"  Theme: {env.ui_theme} (active: {theme_info['active_theme']})\n"
        config_info += f"  Detected Background: {theme_info['detected_background']}\n"
        
        # Show macOS-specific info if available
        if 'macos_appearance' in theme_info and theme_info['macos_appearance'] != 'unknown':
            config_info += f"  macOS System: {theme_info['macos_appearance']} mode\n"
        
        config_info += f"\nConfiguration file: data/.env"
        
        self._print_panel(config_info, "📋 Current Configuration", "cyan")
        
        # Ask if user wants to modify settings
        if self._confirm("Modify settings?", False):
            # Use the same settings wizard
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