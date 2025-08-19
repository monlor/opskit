"""
Interactive Components Library - Enhanced Logger with Interactive Components

Provides enhanced logging functionality with interactive UI components for OpsKit tools:
- Enhanced logger with semantic logging methods  
- Interactive components integration (confirm, input, selection)
- Formatting helpers and structured display
- Connection and operation logging
"""

import os
import sys
import getpass
import time
import threading
from typing import List, Dict, Any, Optional, Callable

# Import OpsKit logger
sys.path.insert(0, os.environ['OPSKIT_BASE_PATH'])
from common.python.logger import get_logger

try:
    import colorama
    from colorama import Fore, Style
    colorama.init(autoreset=True)
    colorama_available = True
except ImportError:
    colorama_available = False


class LoadingSpinner:
    """Loading spinner for long-running operations"""
    
    def __init__(self, message: str = "Loading", spinner_chars: str = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏", logger=None):
        self.message = message
        self.spinner_chars = spinner_chars
        self.running = False
        self.thread = None
        self.start_time = None
        self.logger = logger or get_logger("interactive")
    
    def start(self):
        """Start the loading spinner"""
        if self.running:
            return
        
        self.running = True
        self.start_time = time.time()
        self.thread = threading.Thread(target=self._spin)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self, final_message: str = None):
        """Stop the loading spinner"""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join()
        
        # Clear the spinner line
        sys.stdout.write('\r\033[K')
        
        # Show final message with duration if provided
        if final_message:
            duration = time.time() - self.start_time if self.start_time else 0
            self.logger.info(f"{final_message} ({duration:.1f}s)")
        
        sys.stdout.flush()
    
    def _spin(self):
        """Internal spinner animation"""
        i = 0
        while self.running:
            duration = time.time() - self.start_time if self.start_time else 0
            char = self.spinner_chars[i % len(self.spinner_chars)]
            sys.stdout.write(f'\r{char} {self.message}... ({duration:.1f}s)')
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if exc_type is None:
            self.stop("✅ Completed")
        else:
            self.stop("❌ Failed")


class ProgressTracker:
    """Progress tracker for operations with known steps"""
    
    def __init__(self, total_steps: int, operation_name: str = "Operation", logger=None):
        self.total_steps = total_steps
        self.operation_name = operation_name
        self.current_step = 0
        self.start_time = time.time()
        self.logger = logger or get_logger("interactive")
    
    def update(self, step_description: str = None):
        """Update progress to next step"""
        self.current_step += 1
        progress_pct = (self.current_step / self.total_steps) * 100
        
        # Create progress bar
        bar_width = 30
        filled_width = int(bar_width * self.current_step / self.total_steps)
        bar = "█" * filled_width + "░" * (bar_width - filled_width)
        
        # Calculate elapsed and estimated time
        elapsed = time.time() - self.start_time
        if self.current_step > 0:
            estimated_total = elapsed * self.total_steps / self.current_step
            remaining = estimated_total - elapsed
        else:
            remaining = 0
        
        # Format message
        message = f"[{self.current_step}/{self.total_steps}] {bar} {progress_pct:.0f}%"
        if step_description:
            message += f" - {step_description}"
        if remaining > 0:
            message += f" (ETA: {remaining:.0f}s)"
        
        self.logger.info(f"\r{message}")
        
        if self.current_step >= self.total_steps:
            self.logger.info(f"✅ {self.operation_name} completed in {elapsed:.1f}s")
    
    def finish(self, message: str = None):
        """Mark operation as finished"""
        elapsed = time.time() - self.start_time
        if message:
            self.logger.info(f"✅ {message} ({elapsed:.1f}s)")
        else:
            self.logger.info(f"✅ {self.operation_name} completed in {elapsed:.1f}s")


class Interactive:
    """Enhanced logger with interactive components and formatting helpers"""
    
    def __init__(self, name: str, tool_name: Optional[str] = None):
        self.logger = get_logger(name, tool_name)
        
        # Import colors
        try:
            from colorama import Fore, Style
            self.Fore = Fore
            self.Style = Style
            self.colors_available = True
        except ImportError:
            self.colors_available = False
    
    def info(self, message: str, *args, **kwargs):
        """Info level logging"""
        self.logger.info(message, *args, **kwargs)
    
    def debug(self, message: str, *args, **kwargs):
        """Debug level logging"""
        self.logger.debug(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """Warning level logging"""
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """Error level logging"""
        self.logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """Critical level logging"""
        self.logger.critical(message, *args, **kwargs)
    
    def section(self, title: str, width: int = 80):
        """Log a section header"""
        separator = "=" * width
        self.info(f"\n{separator}")
        self.info(f"🔄 {title}")
        self.info(separator)
    
    def subsection(self, title: str, width: int = 60):
        """Log a subsection header"""
        separator = "-" * width
        self.info(f"\n{separator}")
        self.info(f"📋 {title}")
        self.info(separator)
    
    def step(self, step_num: int, total_steps: int, description: str):
        """Log a step in a process"""
        self.info(f"[{step_num}/{total_steps}] 🔄 {description}")
    
    def success(self, message: str):
        """Log a success message with emoji"""
        self.info(f"✅ {message}")
    
    def failure(self, message: str):
        """Log a failure message with emoji"""
        self.error(f"❌ {message}")
    
    def warning_msg(self, message: str):
        """Log a warning message with emoji"""
        self.warning(f"⚠️  {message}")
    
    def progress(self, message: str):
        """Log a progress message with emoji"""
        self.info(f"📊 {message}")
    
    def connection_test(self, host: str, port: str, result: bool):
        """Log connection test results"""
        if result:
            self.success(f"Connection to {host}:{port} successful")
        else:
            self.failure(f"Connection to {host}:{port} failed")
    
    def operation_start(self, operation: str, details: str = ""):
        """Log operation start"""
        if details:
            self.info(f"🚀 Starting {operation}: {details}")
        else:
            self.info(f"🚀 Starting {operation}")
    
    def operation_complete(self, operation: str, duration: float = None):
        """Log operation completion"""
        if duration is not None:
            self.success(f"{operation} completed (duration: {duration:.1f}s)")
        else:
            self.success(f"{operation} completed")
    
    def display_info(self, title: str, info_dict: Dict[str, Any]):
        """Display structured information"""
        self.info(f"\n📋 {title}:")
        for key, value in info_dict.items():
            self.info(f"   {key}: {value}")
    
    def display_list(self, title: str, items: List[str], indent: str = "  • "):
        """Display a list with proper formatting"""
        self.info(f"\n📊 {title} ({len(items)} items):")
        for item in items:
            self.info(f"{indent}{item}")
    
    def confirmation_required(self, message: str):
        """Log that confirmation is required"""
        self.warning_msg(f"Confirmation required: {message}")
    
    def user_cancelled(self, operation: str = "operation"):
        """Log user cancellation"""
        self.info(f"👋 User cancelled {operation}")
    
    def retry_attempt(self, attempt: int, max_attempts: int, operation: str):
        """Log retry attempts"""
        self.warning_msg(f"Retry attempt {attempt}/{max_attempts} for {operation}")
    
    def cache_operation(self, operation: str, item: str):
        """Log cache operations"""
        self.debug(f"Cache {operation}: {item}")
    
    # Interactive component methods
    def confirm(self, message: str, default: bool = False, **kwargs) -> bool:
        """Interactive confirmation with logging"""
        self.confirmation_required(message)
        
        # Simple confirmation implementation
        default_char = 'Y' if default else 'N'
        other_char = 'n' if default else 'y'
        prompt_text = f"{message} [{default_char}/{other_char}]: "
        
        while True:
            try:
                response = input(prompt_text).strip().lower()
                
                if not response:
                    result = default
                elif response in ['y', 'yes', 'true', '1']:
                    result = True
                elif response in ['n', 'no', 'false', '0']:
                    result = False
                else:
                    self.logger.warning("Please enter yes or no")
                    continue
                
                if result:
                    self.info(f"✅ User confirmed: {message}")
                else:
                    self.info(f"❌ User declined: {message}")
                
                return result
                
            except KeyboardInterrupt:
                self.user_cancelled("confirmation")
                return False
    
    def get_input(self, prompt: str, default: str = "", password: bool = False, 
                  validator=None, error_message: str = "Invalid input", required: bool = True, **kwargs) -> str:
        """Interactive input with logging"""
        self.debug(f"Requesting input: {prompt}")
        
        # Format prompt
        if default:
            display_prompt = f"{prompt} [{default}]: "
        else:
            display_prompt = f"{prompt}: "
        
        while True:
            try:
                if password:
                    user_input = getpass.getpass(display_prompt)
                else:
                    user_input = input(display_prompt)
                
                # Handle empty input
                if not user_input.strip():
                    if default:
                        user_input = default
                    elif not required:
                        # Allow empty input when not required
                        return ""
                    else:
                        self.logger.warning("Input is required")
                        continue
                
                # Validate input
                if validator and not validator(user_input.strip()):
                    self.logger.warning(error_message)
                    continue
                
                self.debug(f"User input received for: {prompt}")
                return user_input.strip()
                
            except KeyboardInterrupt:
                self.user_cancelled("input")
                return ""
            except EOFError:
                return ""
    
    def delete_confirm(self, item_name: str, item_type: str = "item", 
                      force_typing: bool = False, confirmation_text: str = "DELETE", **kwargs) -> bool:
        """Interactive delete confirmation with logging"""
        self.warning_msg(f"Delete confirmation requested for: {item_name}")
        
        self.logger.warning(f"⚠️  WARNING: Destructive Operation")
        self.logger.warning(f"You are about to delete {item_type}: {item_name}")
        self.logger.warning("This action cannot be undone!")
        
        if force_typing:
            typed_confirmation = self.get_input(
                f"Type '{confirmation_text}' to confirm deletion",
                validator=lambda x: x.upper() == confirmation_text.upper(),
                error_message=f"You must type '{confirmation_text}' exactly to confirm"
            )
            result = typed_confirmation.upper() == confirmation_text.upper()
        else:
            result = self.confirm(f"Delete {item_type} '{item_name}'?", default=False)
        
        if result:
            self.warning_msg(f"Delete confirmed for: {item_name}")
        else:
            self.info(f"Delete cancelled for: {item_name}")
        
        return result
    
    def select_from_list(self, items: List, title: str = "Select an option", **kwargs):
        """Interactive list selection with logging"""
        self.info(f"List selection requested: {title} ({len(items)} items)")
        
        if not items:
            self.logger.warning("No items to select from")
            return None
        
        self.logger.info(f"=== {title} ===")
        for i, item in enumerate(items, 1):
            self.logger.info(f"{i:2d}. {item}")
        
        while True:
            try:
                response = input("Your choice: ").strip()
                
                if not response:
                    self.info(f"User cancelled selection from: {title}")
                    return None
                
                try:
                    selection = int(response)
                    if 1 <= selection <= len(items):
                        result = selection - 1
                        self.info(f"User selected option {result} from: {title}")
                        return result
                    else:
                        self.logger.warning(f"Please enter a number between 1 and {len(items)}")
                except ValueError:
                    self.logger.warning("Please enter a valid number")
                    
            except KeyboardInterrupt:
                self.info(f"User cancelled selection from: {title}")
                return None
    
    def select_multiple_from_list(self, items: List, title: str = "Select multiple options", **kwargs):
        """Interactive multiple selection from list with logging"""
        self.info(f"Multiple selection requested: {title} ({len(items)} items)")
        
        if not items:
            self.logger.warning("No items to select from")
            return []
        
        self.logger.info(f"=== {title} ===")
        for i, item in enumerate(items, 1):
            self.logger.info(f"{i:2d}. {item}")
        
        self.logger.info("Enter numbers separated by spaces (e.g., '1 3 5') or comma (e.g., '1,3,5')")
        self.logger.info("Use ranges (e.g., '1-3' for items 1,2,3) or combine (e.g., '1-3,5,7-9')")
        self.logger.info("Type 'all' or '*' to select all items")
        self.logger.info("Press Enter without input to finish selection")
        
        while True:
            try:
                response = input("Your choices: ").strip()
                
                if not response:
                    self.info(f"User finished selection from: {title}")
                    return []
                
                # Check for "select all" commands
                if response.lower() in ['all', '*']:
                    all_selections = list(range(len(items)))
                    selected_items = [items[i] for i in all_selections]
                    self.info(f"User selected ALL {len(items)} options: {selected_items}")
                    return all_selections
                
                try:
                    # Parse selections supporting ranges and multiple formats
                    selections = []
                    
                    # Split by comma first, then by spaces
                    parts = []
                    if ',' in response:
                        parts = [x.strip() for x in response.split(',') if x.strip()]
                    else:
                        parts = [x.strip() for x in response.split() if x.strip()]
                    
                    for part in parts:
                        if '-' in part and part.count('-') == 1:
                            # Range format (e.g., "1-3")
                            try:
                                start_str, end_str = part.split('-')
                                start = int(start_str.strip())
                                end = int(end_str.strip())
                                if start <= end:
                                    selections.extend(range(start, end + 1))
                                else:
                                    selections.extend(range(start, end - 1, -1))
                            except ValueError:
                                # Invalid range, treat as single number
                                selections.append(int(part))
                        else:
                            # Single number
                            selections.append(int(part))
                    
                    # Validate all selections
                    valid_selections = []
                    invalid_selections = []
                    
                    for selection in selections:
                        if 1 <= selection <= len(items):
                            valid_selections.append(selection - 1)
                        else:
                            invalid_selections.append(selection)
                    
                    if invalid_selections:
                        self.logger.warning(f"Invalid selections: {invalid_selections}. Please enter numbers between 1 and {len(items)}")
                        continue
                    
                    if valid_selections:
                        # Remove duplicates while preserving order
                        unique_selections = []
                        seen = set()
                        for sel in valid_selections:
                            if sel not in seen:
                                unique_selections.append(sel)
                                seen.add(sel)
                        
                        selected_items = [items[i] for i in unique_selections]
                        self.info(f"User selected {len(unique_selections)} options: {selected_items}")
                        return unique_selections
                    else:
                        self.logger.warning("No valid selections provided")
                        
                except ValueError:
                    self.logger.warning("Please enter valid numbers separated by spaces or commas")
                    
            except KeyboardInterrupt:
                self.info(f"User cancelled multiple selection from: {title}")
                return []
    
    # Loading and progress methods
    def loading_spinner(self, message: str = "Processing") -> LoadingSpinner:
        """Create a loading spinner for long-running operations"""
        self.debug(f"Starting loading spinner: {message}")
        return LoadingSpinner(message, logger=self.logger)
    
    def progress_tracker(self, total_steps: int, operation_name: str = "Operation") -> ProgressTracker:
        """Create a progress tracker for operations with known steps"""
        self.debug(f"Starting progress tracker: {operation_name} ({total_steps} steps)")
        return ProgressTracker(total_steps, operation_name, logger=self.logger)
    
    def with_loading(self, operation: Callable, message: str = "Processing", *args, **kwargs):
        """Execute an operation with a loading spinner"""
        with self.loading_spinner(message) as spinner:
            try:
                result = operation(*args, **kwargs)
                spinner.stop("✅ Completed")
                return result
            except Exception as e:
                spinner.stop(f"❌ Failed: {e}")
                raise


def get_interactive(name: str, tool_name: Optional[str] = None) -> Interactive:
    """
    Get an interactive logger with components and formatting helpers
    
    Args:
        name: Logger name (usually __name__)
        tool_name: Optional tool name for tool-specific logging
    
    Returns:
        Interactive logger instance with additional methods
    
    Example:
        logger = get_interactive(__name__, 'mysql-sync')
        logger.section("Database Synchronization")
        logger.success("Operation completed successfully")
        result = logger.confirm("Continue with operation?")
    """
    return Interactive(name, tool_name)


# Convenience functions for backward compatibility
def confirm(message: str, **kwargs) -> bool:
    """Interactive confirmation"""
    temp_logger = Interactive("interactive")
    return temp_logger.confirm(message, **kwargs)

def get_input(prompt: str, **kwargs) -> str:
    """Interactive input"""
    temp_logger = Interactive("interactive")
    return temp_logger.get_input(prompt, **kwargs)

def delete_confirm(item_name: str, **kwargs) -> bool:
    """Interactive delete confirmation"""
    temp_logger = Interactive("interactive")
    return temp_logger.delete_confirm(item_name, **kwargs)

def select_from_list(items: List, title: str = "Select an option", **kwargs):
    """Interactive list selection"""
    temp_logger = Interactive("interactive")
    return temp_logger.select_from_list(items, title, **kwargs)

def select_multiple_from_list(items: List, title: str = "Select multiple options", **kwargs):
    """Interactive multiple selection from list"""
    temp_logger = Interactive("interactive")
    return temp_logger.select_multiple_from_list(items, title, **kwargs)

def loading_spinner(message: str = "Processing") -> LoadingSpinner:
    """Create a loading spinner for long-running operations"""
    return LoadingSpinner(message)

def progress_tracker(total_steps: int, operation_name: str = "Operation") -> ProgressTracker:
    """Create a progress tracker for operations with known steps"""
    return ProgressTracker(total_steps, operation_name)

def with_loading(operation: Callable, message: str = "Processing", *args, **kwargs):
    """Execute an operation with a loading spinner"""
    with loading_spinner(message) as spinner:
        try:
            result = operation(*args, **kwargs)
            spinner.stop("✅ Completed")
            return result
        except Exception as e:
            spinner.stop(f"❌ Failed: {e}")
            raise