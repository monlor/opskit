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

from .config_manager import ConfigManager
from .platform_utils import PlatformUtils
from .dependency_manager import DependencyManager
import yaml


class OpsKitCLI:
    """Interactive command line interface for OpsKit"""
    
    def __init__(self, debug: bool = False):
        """Initialize CLI interface"""
        self.debug = debug
        self.console = Console() if rich_available else None
        
        # Get OpsKit root directory
        current_file = Path(__file__).resolve()
        self.opskit_root = current_file.parent.parent
        self.tools_dir = self.opskit_root / 'tools'
        
        # Tool cache
        self._tool_cache = None
        self._tool_categories = None
        self._yaml_tools = None
        
        # Initialize managers
        self.config_manager = ConfigManager()
        self.platform_utils = PlatformUtils()
        self.dependency_manager = DependencyManager(self.opskit_root, debug=debug)
    
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
            
            # Look for main executable
            main_file = None
            for candidate in ['main.py', 'main.sh', f'{tool_name}.py', f'{tool_name}.sh']:
                candidate_path = tool_dir / candidate
                if candidate_path.exists():
                    main_file = candidate
                    break
            
            if not main_file:
                return None
            
            # Parse CLAUDE.md for description
            description = "No description available"
            claude_md = tool_dir / 'CLAUDE.md'
            if claude_md.exists():
                try:
                    with open(claude_md, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    # Look for description section
                    in_description = False
                    desc_lines = []
                    for line in lines:
                        line = line.strip()
                        if line.startswith('## ') and ('功能描述' in line or 'description' in line.lower()):
                            in_description = True
                            continue
                        elif line.startswith('## ') and in_description:
                            break
                        elif in_description and line and not line.startswith('#'):
                            desc_lines.append(line)
                    
                    if desc_lines:
                        description = ' '.join(desc_lines)[:200] + ('...' if len(' '.join(desc_lines)) > 200 else '')
                except Exception:
                    pass
            
            # Check for requirements
            has_python_deps = (tool_dir / 'requirements.txt').exists()
            has_config = (tool_dir / 'config.yaml.template').exists()
            
            # Determine tool type
            tool_type = 'python' if main_file.endswith('.py') else 'shell'
            
            return {
                'name': tool_name,
                'path': str(tool_dir),
                'main_file': main_file,
                'description': description,
                'type': tool_type,
                'has_python_deps': has_python_deps,
                'has_config': has_config,
                'category': tool_dir.parent.name
            }
        
        except Exception as e:
            if self.debug:
                self._print(f"Error parsing tool {tool_dir}: {e}", "red")
            return None
    
    def interactive_mode(self) -> None:
        """Enter interactive CLI mode with list view, pagination and real-time search"""
        if not prompt_toolkit_available:
            self._print("prompt_toolkit is not installed. Please install it for advanced CLI features.", "yellow")
            return self._fallback_interactive_mode()
        
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
        
        # Style
        style = Style.from_dict({
            'title': '#00ff00 bold',
            'search-label': '#ffff00',
            'header': '#87d7ff bold',
            'separator': '#666666',
            'selected': '#000000 bg:#87d7ff',
            'normal': '#ffffff',
            'category': '#ffff00',
            'description': '#aaaaaa',
            'keybind': '#87d7ff',
            'no-results': '#ff0000',
        })
        
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
    
    def _fallback_interactive_mode(self) -> None:
        """Fallback interactive mode without prompt_toolkit"""
        self._print_panel(
            "Welcome to OpsKit - Unified Operations Tool Management Platform\n"
            "Discover, configure, and run operational tools with ease.",
            "OpsKit Interactive Mode",
            "green"
        )
        
        while True:
            try:
                self._print("\nWhat would you like to do?")
                self._print("1. List all tools")
                self._print("2. Browse tools by category")
                self._print("3. Search tools")
                self._print("4. Configuration management")
                self._print("5. System status")
                self._print("6. Update OpsKit")
                self._print("7. Help")
                self._print("0. Exit")
                
                choice = self._input("Enter your choice")
                
                if choice == '1':
                    self.list_tools()
                elif choice == '2':
                    self._browse_tools_menu()
                elif choice == '3':
                    self._search_tools_interactive()
                elif choice == '4':
                    self.configuration_menu()
                elif choice == '5':
                    self.show_status()
                elif choice == '6':
                    self.update_opskit()
                elif choice == '7':
                    self._show_help()
                elif choice == '0':
                    self._print("Goodbye!", "green")
                    break
                else:
                    self._print("Invalid choice. Please try again.", "yellow")
            
            except KeyboardInterrupt:
                self._print("\nGoodbye!", "green")
                break
            except Exception as e:
                self._print(f"Error: {e}", "red")
                if self.debug:
                    import traceback
                    traceback.print_exc()
    
    def _browse_tools_menu(self) -> None:
        """Browse tools by category"""
        tools = self.discover_tools()
        
        if not tools:
            self._print("No tools found. Please check your OpsKit installation.", "yellow")
            return
        
        categories = list(tools.keys())
        
        while True:
            self._print("\nAvailable tool categories:")
            for i, category in enumerate(categories, 1):
                tool_count = len(tools[category])
                self._print(f"{i}. {category} ({tool_count} tools)")
            self._print("0. Back to main menu")
            
            choice = self._input("Select a category")
            
            if choice == '0':
                break
            
            try:
                category_index = int(choice) - 1
                if 0 <= category_index < len(categories):
                    category = categories[category_index]
                    self._show_category_tools(category, tools[category])
                else:
                    self._print("Invalid selection.", "yellow")
            except ValueError:
                self._print("Please enter a number.", "yellow")
    
    def _show_category_tools(self, category: str, category_tools: List[Dict[str, str]]) -> None:
        """Show tools in a specific category"""
        while True:
            self._print(f"\nTools in category '{category}':")
            
            if rich_available and self.console:
                table = Table(show_header=True, header_style="bold blue")
                table.add_column("#", width=3)
                table.add_column("Name", width=20)
                table.add_column("Type", width=8)
                table.add_column("Description")
                
                for i, tool in enumerate(category_tools, 1):
                    table.add_row(
                        str(i),
                        tool['name'],
                        tool['type'],
                        tool['description'][:80] + ('...' if len(tool['description']) > 80 else '')
                    )
                
                self.console.print(table)
            else:
                for i, tool in enumerate(category_tools, 1):
                    print(f"{i}. {tool['name']} ({tool['type']})")
                    print(f"   {tool['description']}")
            
            self._print("0. Back to categories")
            
            choice = self._input("Select a tool to run (or enter tool name)")
            
            if choice == '0':
                break
            
            # Try to find tool by number or name
            selected_tool = None
            
            # Try by number first
            try:
                tool_index = int(choice) - 1
                if 0 <= tool_index < len(category_tools):
                    selected_tool = category_tools[tool_index]
            except ValueError:
                # Try by name
                for tool in category_tools:
                    if tool['name'].lower() == choice.lower():
                        selected_tool = tool
                        break
            
            if selected_tool:
                self._show_tool_details(selected_tool)
            else:
                self._print("Tool not found.", "yellow")
    
    def _show_tool_details(self, tool: Dict[str, str]) -> None:
        """Show detailed information about a tool"""
        self._print_panel(
            f"Name: {tool['name']}\n"
            f"Type: {tool['type']}\n"
            f"Category: {tool['category']}\n"
            f"Path: {tool['path']}\n"
            f"Main File: {tool['main_file']}\n"
            f"Has Dependencies: {'Yes' if tool['has_python_deps'] else 'No'}\n"
            f"Has Configuration: {'Yes' if tool['has_config'] else 'No'}\n\n"
            f"Description:\n{tool['description']}",
            f"Tool Details: {tool['name']}",
            "blue"
        )
        
        while True:
            self._print("\nWhat would you like to do?")
            self._print("1. Run this tool")
            self._print("2. Configure this tool")
            self._print("3. Show dependencies")
            self._print("0. Back")
            
            choice = self._input("Enter your choice")
            
            if choice == '1':
                self.run_tool(tool['name'])
                break
            elif choice == '2':
                self.configure_tool(tool['name'])
                break
            elif choice == '3':
                self._show_tool_dependencies(tool)
            elif choice == '0':
                break
            else:
                self._print("Invalid choice.", "yellow")
    
    def _show_tool_dependencies(self, tool: Dict[str, str]) -> None:
        """Show tool dependencies"""
        tool_path = Path(tool['path'])
        
        # Python dependencies
        python_deps = []
        requirements_file = tool_path / 'requirements.txt'
        if requirements_file.exists():
            try:
                with open(requirements_file, 'r') as f:
                    python_deps = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            except Exception:
                pass
        
        # System dependencies (basic check)
        system_deps = []
        if tool['type'] == 'shell':
            main_file = tool_path / tool['main_file']
            if main_file.exists():
                try:
                    with open(main_file, 'r') as f:
                        content = f.read()
                    
                    # Look for common commands
                    common_commands = ['mysql', 'mysqldump', 'git', 'curl', 'wget', 'jq', 'docker']
                    for cmd in common_commands:
                        if cmd in content:
                            system_deps.append(cmd)
                except Exception:
                    pass
        
        deps_info = f"Tool: {tool['name']}\n\n"
        
        if python_deps:
            deps_info += "Python Dependencies:\n"
            for dep in python_deps:
                deps_info += f"  - {dep}\n"
        else:
            deps_info += "Python Dependencies: None\n"
        
        deps_info += "\n"
        
        if system_deps:
            deps_info += "System Dependencies (detected):\n"
            for dep in system_deps:
                available = "✓" if self.platform_utils.command_exists(dep) else "✗"
                deps_info += f"  {available} {dep}\n"
        else:
            deps_info += "System Dependencies: None detected\n"
        
        self._print_panel(deps_info, "Dependencies", "yellow")
    
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
        """Run a specific tool directly with dependency management"""
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
        
        self._print(f"Running {tool_name}...\n", "green")
        
        # Run tool with dependency management
        try:
            return self.dependency_manager.run_tool_with_dependencies(found_tool, tool_args)
        except Exception as e:
            self._print(f"Error running tool: {e}", "red")
            if self.debug:
                import traceback
                traceback.print_exc()
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
    
    def _search_tools_interactive(self) -> None:
        """Interactive tool search"""
        query = self._input("Enter search query")
        if query:
            self.search_tools(query)
    
    def show_status(self) -> None:
        """Show system status"""
        # Get system information
        system_info = self.platform_utils.get_system_info()
        config_summary = self.config_manager.get_config_summary()
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
    
    def configuration_menu(self) -> None:
        """Configuration management menu"""
        self._print("Configuration management functionality will be implemented here", "yellow")
    
    def configure_tool(self, tool_name: str) -> None:
        """Configure a specific tool"""
        self._print(f"Tool configuration for '{tool_name}' will be implemented here", "yellow")
    
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