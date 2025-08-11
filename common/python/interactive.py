"""
Interactive Components Library - Python Implementation

Provides common interactive UI components for OpsKit tools:
- User input with validation
- Confirmation dialogs  
- Selection lists
- Advanced selection with prompt_toolkit
- Delete confirmations
- Progress indicators
"""

import os
import sys
import getpass
from typing import List, Dict, Any, Optional, Callable, Union
from datetime import datetime

# Third-party imports (optional dependencies)
try:
    from prompt_toolkit import prompt
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.shortcuts import radiolist_dialog, button_dialog
    from prompt_toolkit.shortcuts import confirm
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.styles import Style
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

try:
    from colorama import init, Fore, Style as ColoramaStyle, Back
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    # Fallback empty strings if colorama not available
    class _MockFore:
        RED = GREEN = YELLOW = BLUE = CYAN = MAGENTA = WHITE = ""
    class _MockStyle:
        RESET_ALL = BRIGHT = DIM = ""
    class _MockBack:
        RED = GREEN = YELLOW = BLUE = CYAN = MAGENTA = WHITE = ""
    Fore = _MockFore()
    ColoramaStyle = _MockStyle()
    Back = _MockBack()


class InteractiveComponents:
    """Collection of interactive UI components for terminal applications"""
    
    def __init__(self, use_colors: bool = True):
        """
        Initialize interactive components
        
        Args:
            use_colors: Enable colored output (requires colorama)
        """
        self.use_colors = use_colors and COLORAMA_AVAILABLE
    
    def get_user_input(self, 
                      prompt_text: str, 
                      default: Optional[str] = None,
                      validator: Optional[Callable[[str], bool]] = None,
                      error_message: str = "Invalid input, please try again",
                      required: bool = True,
                      password: bool = False,
                      completions: Optional[List[str]] = None) -> str:
        """
        Get user input with validation and optional features
        
        Args:
            prompt_text: Text to display as prompt
            default: Default value if user enters nothing
            validator: Function to validate input (returns bool)
            error_message: Message to show on validation failure
            required: Whether input is required
            password: Hide input (for passwords)
            completions: List of auto-completion options
            
        Returns:
            User input string
        """
        # Format prompt
        if default:
            display_prompt = f"{prompt_text} [{default}]: "
        else:
            display_prompt = f"{prompt_text}: "
        
        if self.use_colors:
            display_prompt = f"{Fore.CYAN}{display_prompt}{ColoramaStyle.RESET_ALL}"
        
        while True:
            try:
                if password:
                    user_input = getpass.getpass(display_prompt)
                # Force simple input for better OpsKit compatibility
                # elif PROMPT_TOOLKIT_AVAILABLE and completions:
                #     completer = WordCompleter(completions)
                #     user_input = prompt(display_prompt, completer=completer)
                else:
                    user_input = input(display_prompt)
                
                # Handle empty input
                if not user_input.strip():
                    if default:
                        return default
                    elif not required:
                        return ""
                    else:
                        if self.use_colors:
                            print(f"{Fore.RED}Input is required{ColoramaStyle.RESET_ALL}")
                        else:
                            print("Input is required")
                        continue
                
                # Validate input
                if validator and not validator(user_input.strip()):
                    if self.use_colors:
                        print(f"{Fore.RED}{error_message}{ColoramaStyle.RESET_ALL}")
                    else:
                        print(error_message)
                    continue
                
                return user_input.strip()
                
            except KeyboardInterrupt:
                print("\nOperation cancelled by user")
                sys.exit(1)
            except EOFError:
                print("\nEOF received, exiting")
                sys.exit(1)
    
    def confirm(self, 
                message: str, 
                default: bool = False,
                yes_text: str = "yes",
                no_text: str = "no") -> bool:
        """
        Show confirmation dialog
        
        Args:
            message: Confirmation message
            default: Default choice (True for yes, False for no)
            yes_text: Text for yes option
            no_text: Text for no option
            
        Returns:
            True if confirmed, False otherwise
        """
        # Force simple input for better compatibility with OpsKit subprocess handling
        # prompt_toolkit can cause issues when tools are run through subprocess
        
        # Fallback to simple input
        default_char = 'Y' if default else 'N'
        other_char = 'n' if default else 'y'
        
        if self.use_colors:
            prompt_text = f"{Fore.CYAN}{message} [{default_char}/{other_char}]: {ColoramaStyle.RESET_ALL}"
        else:
            prompt_text = f"{message} [{default_char}/{other_char}]: "
        
        while True:
            try:
                response = input(prompt_text).strip().lower()
                
                if not response:
                    return default
                
                if response in ['y', 'yes', 'true', '1']:
                    return True
                elif response in ['n', 'no', 'false', '0']:
                    return False
                else:
                    if self.use_colors:
                        print(f"{Fore.RED}Please enter {yes_text} or {no_text}{ColoramaStyle.RESET_ALL}")
                    else:
                        print(f"Please enter {yes_text} or {no_text}")
                    
            except KeyboardInterrupt:
                print("\nOperation cancelled by user")
                return False
    
    def select_from_list(self, 
                        items: List[Union[str, Dict[str, Any]]], 
                        title: str = "Select an option",
                        allow_multiple: bool = False,
                        numbered: bool = True,
                        allow_cancel: bool = True) -> Union[int, List[int], None]:
        """
        Display a selection list and get user choice
        
        Args:
            items: List of items (strings or dicts with 'name' and 'value')
            title: Title for the selection
            allow_multiple: Allow multiple selections
            numbered: Show numbers for selection
            allow_cancel: Allow cancellation
            
        Returns:
            Selected index(es) or None if cancelled
        """
        if not items:
            if self.use_colors:
                print(f"{Fore.YELLOW}No items to select from{ColoramaStyle.RESET_ALL}")
            else:
                print("No items to select from")
            return None
        
        # Display title
        if self.use_colors:
            print(f"\n{Fore.CYAN}=== {title} ==={ColoramaStyle.RESET_ALL}")
        else:
            print(f"\n=== {title} ===")
        
        # Display items
        for i, item in enumerate(items, 1):
            if isinstance(item, dict):
                display_text = item.get('name', str(item))
            else:
                display_text = str(item)
            
            if numbered:
                if self.use_colors:
                    print(f"{Fore.YELLOW}{i:2d}.{ColoramaStyle.RESET_ALL} {display_text}")
                else:
                    print(f"{i:2d}. {display_text}")
            else:
                print(f"  {display_text}")
        
        # Show selection options
        if allow_multiple:
            selection_help = "Enter numbers separated by commas (e.g., 1,3,5)"
        else:
            selection_help = "Enter the number of your choice"
        
        if allow_cancel:
            selection_help += ", or 'cancel' to abort"
        
        if self.use_colors:
            print(f"\n{Fore.CYAN}{selection_help}{ColoramaStyle.RESET_ALL}")
        else:
            print(f"\n{selection_help}")
        
        while True:
            try:
                response = input(f"Your choice: ").strip().lower()
                
                if allow_cancel and response in ['cancel', 'c', 'quit', 'q']:
                    return None
                
                if allow_multiple:
                    try:
                        # Parse multiple selections
                        selections = []
                        for part in response.split(','):
                            part = part.strip()
                            if '-' in part:
                                # Handle ranges like "1-5"
                                start, end = map(int, part.split('-'))
                                selections.extend(range(start, end + 1))
                            else:
                                selections.append(int(part))
                        
                        # Validate selections
                        valid_selections = []
                        for sel in selections:
                            if 1 <= sel <= len(items):
                                if sel - 1 not in valid_selections:
                                    valid_selections.append(sel - 1)
                        
                        if valid_selections:
                            return sorted(valid_selections)
                        else:
                            raise ValueError("No valid selections")
                            
                    except ValueError:
                        if self.use_colors:
                            print(f"{Fore.RED}Invalid selection format{ColoramaStyle.RESET_ALL}")
                        else:
                            print("Invalid selection format")
                        continue
                else:
                    try:
                        selection = int(response)
                        if 1 <= selection <= len(items):
                            return selection - 1
                        else:
                            raise ValueError("Selection out of range")
                    except ValueError:
                        if self.use_colors:
                            print(f"{Fore.RED}Please enter a number between 1 and {len(items)}{ColoramaStyle.RESET_ALL}")
                        else:
                            print(f"Please enter a number between 1 and {len(items)}")
                        continue
                        
            except KeyboardInterrupt:
                print("\nSelection cancelled by user")
                return None
    
    def advanced_select(self, 
                       items: List[Dict[str, Any]], 
                       title: str = "Select an option",
                       text_key: str = 'name',
                       value_key: str = 'value') -> Any:
        """
        Advanced selection using prompt_toolkit (if available)
        
        Args:
            items: List of dictionaries with text and value
            title: Dialog title
            text_key: Key for display text in item dict
            value_key: Key for return value in item dict
            
        Returns:
            Selected value or None if cancelled
        """
        if not PROMPT_TOOLKIT_AVAILABLE:
            # Fallback to simple selection
            result_idx = self.select_from_list(items, title, allow_cancel=True)
            if result_idx is not None:
                return items[result_idx].get(value_key)
            return None
        
        try:
            # Convert items to prompt_toolkit format
            radio_items = []
            for item in items:
                radio_items.append((
                    item.get(value_key),
                    item.get(text_key, str(item))
                ))
            
            result = radiolist_dialog(
                title=title,
                text="Use arrow keys to navigate and Space to select:",
                values=radio_items,
                style=Style.from_dict({
                    'dialog': 'bg:#88ff88',
                    'button': 'bg:#ffffff #000000',
                    'radio-selected': 'bg:#0000aa #ffffff',
                    'radio': '#ffffff',
                })
            ).run()
            
            return result
            
        except KeyboardInterrupt:
            return None
        except Exception:
            # Fallback to simple selection on any error
            result_idx = self.select_from_list(items, title, allow_cancel=True)
            if result_idx is not None:
                return items[result_idx].get(value_key)
            return None
    
    def delete_confirmation(self, 
                           item_name: str, 
                           item_type: str = "item",
                           force_typing: bool = False,
                           confirmation_text: str = "DELETE") -> bool:
        """
        Specialized confirmation for delete operations
        
        Args:
            item_name: Name of item being deleted
            item_type: Type of item (file, database, etc.)
            force_typing: Require typing confirmation text
            confirmation_text: Text user must type to confirm
            
        Returns:
            True if deletion confirmed
        """
        if self.use_colors:
            print(f"\n{Fore.RED}⚠️  WARNING: Destructive Operation{ColoramaStyle.RESET_ALL}")
            print(f"You are about to delete {item_type}: {Fore.YELLOW}{item_name}{ColoramaStyle.RESET_ALL}")
            print(f"{Fore.RED}This action cannot be undone!{ColoramaStyle.RESET_ALL}")
        else:
            print(f"\n⚠️  WARNING: Destructive Operation")
            print(f"You are about to delete {item_type}: {item_name}")
            print("This action cannot be undone!")
        
        if force_typing:
            typed_confirmation = self.get_user_input(
                f"Type '{confirmation_text}' to confirm deletion",
                validator=lambda x: x.upper() == confirmation_text.upper(),
                error_message=f"You must type '{confirmation_text}' exactly to confirm"
            )
            return typed_confirmation.upper() == confirmation_text.upper()
        else:
            return self.confirm(f"Delete {item_type} '{item_name}'?", default=False)
    
    def show_progress_bar(self, 
                         current: int, 
                         total: int, 
                         prefix: str = "Progress",
                         suffix: str = "Complete",
                         length: int = 50,
                         fill: str = '█',
                         empty: str = '-') -> None:
        """
        Display a progress bar
        
        Args:
            current: Current progress value
            total: Total value for completion
            prefix: Text before progress bar
            suffix: Text after progress bar  
            length: Length of progress bar in characters
            fill: Character for filled portion
            empty: Character for empty portion
        """
        if total == 0:
            return
            
        percent = min(100.0 * current / total, 100.0)
        filled_length = int(length * current // total)
        
        if self.use_colors:
            bar = f"{Fore.GREEN}{fill * filled_length}{ColoramaStyle.RESET_ALL}"
            bar += f"{Fore.WHITE}{empty * (length - filled_length)}{ColoramaStyle.RESET_ALL}"
            print(f"\r{prefix} |{bar}| {percent:6.1f}% {suffix}", end="", flush=True)
        else:
            bar = fill * filled_length + empty * (length - filled_length)
            print(f"\r{prefix} |{bar}| {percent:6.1f}% {suffix}", end="", flush=True)
    
    def show_spinner(self, message: str = "Processing", delay: float = 0.1) -> None:
        """
        Show a simple spinner (for use in loops)
        Call repeatedly to animate
        
        Args:
            message: Message to show with spinner
            delay: Animation delay between calls
        """
        import time
        
        spinner_chars = ['|', '/', '-', '\\']
        char_index = int(time.time() / delay) % len(spinner_chars)
        
        if self.use_colors:
            print(f"\r{Fore.CYAN}{spinner_chars[char_index]}{ColoramaStyle.RESET_ALL} {message}", end="", flush=True)
        else:
            print(f"\r{spinner_chars[char_index]} {message}", end="", flush=True)
    
    def display_table(self, 
                     data: List[Dict[str, Any]], 
                     headers: Optional[List[str]] = None,
                     title: Optional[str] = None) -> None:
        """
        Display data in a simple table format
        
        Args:
            data: List of dictionaries with table data
            headers: Column headers (auto-detected if None)
            title: Optional table title
        """
        if not data:
            if self.use_colors:
                print(f"{Fore.YELLOW}No data to display{ColoramaStyle.RESET_ALL}")
            else:
                print("No data to display")
            return
        
        # Auto-detect headers if not provided
        if headers is None:
            headers = list(data[0].keys()) if data else []
        
        # Calculate column widths
        col_widths = {}
        for header in headers:
            col_widths[header] = len(str(header))
            for row in data:
                col_widths[header] = max(col_widths[header], len(str(row.get(header, ''))))
        
        # Display title
        if title:
            if self.use_colors:
                print(f"\n{Fore.CYAN}=== {title} ==={ColoramaStyle.RESET_ALL}")
            else:
                print(f"\n=== {title} ===")
        
        # Display headers
        header_line = " | ".join(header.ljust(col_widths[header]) for header in headers)
        separator_line = "-" * len(header_line)
        
        if self.use_colors:
            print(f"{Fore.YELLOW}{header_line}{ColoramaStyle.RESET_ALL}")
        else:
            print(header_line)
        print(separator_line)
        
        # Display data rows
        for row in data:
            row_line = " | ".join(str(row.get(header, '')).ljust(col_widths[header]) for header in headers)
            print(row_line)


# Global instance for easy access
interactive = InteractiveComponents()

# Convenience functions for common use cases
def get_input(prompt_text: str, **kwargs) -> str:
    """Convenience function for getting user input"""
    return interactive.get_user_input(prompt_text, **kwargs)

def confirm(message: str, **kwargs) -> bool:
    """Convenience function for confirmation"""
    return interactive.confirm(message, **kwargs)

def select_from_list(items: List, **kwargs) -> Union[int, List[int], None]:
    """Convenience function for list selection"""
    return interactive.select_from_list(items, **kwargs)

def delete_confirm(item_name: str, **kwargs) -> bool:
    """Convenience function for delete confirmation"""
    return interactive.delete_confirmation(item_name, **kwargs)

def show_progress(current: int, total: int, **kwargs) -> None:
    """Convenience function for progress bar"""
    interactive.show_progress_bar(current, total, **kwargs)


if __name__ == "__main__":
    # Demo/test the interactive components
    print("Interactive Components Demo")
    print("=" * 30)
    
    # Test basic input
    name = get_input("Enter your name", default="User")
    print(f"Hello, {name}!")
    
    # Test confirmation
    if confirm("Continue with demo?", default=True):
        # Test list selection
        items = ["Option A", "Option B", "Option C"]
        selection = select_from_list(items, "Choose an option")
        if selection is not None:
            print(f"You selected: {items[selection]}")
        
        # Test delete confirmation
        if delete_confirm("test_file.txt", "file"):
            print("File would be deleted")
        else:
            print("Delete cancelled")
        
        # Test progress bar
        import time
        print("\nProgress bar demo:")
        for i in range(101):
            show_progress(i, 100)
            time.sleep(0.02)
        print("\nDemo complete!")
    else:
        print("Demo cancelled")