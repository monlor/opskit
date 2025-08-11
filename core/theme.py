"""
Theme Management Module for OpsKit

Provides terminal background detection and adaptive theme selection.
"""

import os
import sys
import subprocess
import platform
from typing import Dict, Tuple, Optional
from prompt_toolkit.styles import Style


def detect_macos_appearance() -> str:
    """
    Detect macOS system appearance (light/dark) via AppleInterfaceStyle.
    
    Returns:
        'light', 'dark', or 'unknown'
    """
    if platform.system() != 'Darwin':
        return 'unknown'
    
    try:
        # Try to read AppleInterfaceStyle from user defaults
        result = subprocess.run([
            'defaults', 'read', '-g', 'AppleInterfaceStyle'
        ], capture_output=True, text=True, timeout=3)
        
        if result.returncode == 0:
            appearance = result.stdout.strip().lower()
            if appearance == 'dark':
                return 'dark'
            # If key exists but not 'dark', it's usually light mode
            elif appearance:
                return 'light'
        else:
            # Key doesn't exist, which typically means light mode in macOS
            return 'light'
    
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        pass
    
    return 'unknown'


def detect_terminal_background() -> str:
    """
    Detect terminal background color (light/dark) using various methods.
    
    Returns:
        'light' or 'dark' or 'unknown'
    """
    # Method 1: macOS System Appearance (highest priority on macOS)
    if platform.system() == 'Darwin':
        macos_appearance = detect_macos_appearance()
        if macos_appearance in ['light', 'dark']:
            return macos_appearance
    
    # Method 2: Check COLORFGBG environment variable (used by many terminals)
    colorfgbg = os.environ.get('COLORFGBG', '')
    if colorfgbg:
        # COLORFGBG format is "foreground;background"
        parts = colorfgbg.split(';')
        if len(parts) >= 2:
            try:
                bg_color = int(parts[-1])
                # Standard terminal colors: 0-7 are dark, 8-15 are light
                # For 256-color terminals, colors 0-7 and 232-243 are typically dark
                if bg_color in [0, 1, 2, 3, 4, 5, 6, 8] or (232 <= bg_color <= 243):
                    return 'dark'
                elif bg_color in [7, 15] or (244 <= bg_color <= 255):
                    return 'light'
            except ValueError:
                pass
    
    # Method 3: Check TERM_PROGRAM for known terminals
    term_program = os.environ.get('TERM_PROGRAM', '').lower()
    if 'vscode' in term_program:
        # VS Code integrated terminal - assume dark by default
        return 'dark'
    elif 'apple_terminal' in term_program:
        # macOS Terminal - if we reach here, macOS detection above failed
        # Fall back to terminal-specific detection
        pass
    
    # Method 4: Check if running in TTY (usually dark)
    if os.environ.get('TERM', '') == 'linux':
        return 'dark'
    
    # Method 5: Check for light/dark theme indicators in environment
    if any(var in os.environ for var in ['LIGHT_THEME', 'GNOME_DESKTOP_SESSION_ID']):
        desktop_session = os.environ.get('DESKTOP_SESSION', '').lower()
        if 'light' in desktop_session:
            return 'light'
        elif 'dark' in desktop_session:
            return 'dark'
    
    # Default assumption - most modern terminals use dark backgrounds
    return 'dark'


def get_theme_colors(theme_mode: str) -> Dict[str, str]:
    """
    Get color scheme for the specified theme.
    
    Args:
        theme_mode: 'light' or 'dark'
    
    Returns:
        Dictionary of style mappings
    """
    if theme_mode == 'light':
        return {
            'title': '#0066cc bold',          # Dark blue title
            'search-label': '#cc6600',        # Dark orange search label  
            'header': '#0066cc bold',         # Dark blue header
            'separator': '#999999',           # Medium gray separator
            'selected': '#ffffff bg:#0066cc', # White text on dark blue background
            'normal': '#000000',              # Black text (visible on light background)
            'category': '#cc6600',            # Dark orange category
            'description': '#666666',         # Dark gray description
            'keybind': '#0066cc',            # Dark blue keybindings
            'no-results': '#cc0000',          # Dark red for no results
        }
    else:  # dark theme
        return {
            'title': '#00ff00 bold',          # Bright green title
            'search-label': '#ffff00',        # Yellow search label
            'header': '#87d7ff bold',         # Light blue header
            'separator': '#666666',           # Gray separator
            'selected': '#000000 bg:#87d7ff', # Black text on light blue background
            'normal': '#ffffff',              # White text (visible on dark background)
            'category': '#ffff00',            # Yellow category
            'description': '#aaaaaa',         # Light gray description
            'keybind': '#87d7ff',            # Light blue keybindings
            'no-results': '#ff0000',          # Red for no results
        }


class ThemeManager:
    """Manages terminal themes and color schemes"""
    
    def __init__(self):
        self._detected_background = None
        self._current_theme = None
    
    def detect_background(self) -> str:
        """Detect and cache terminal background"""
        if self._detected_background is None:
            self._detected_background = detect_terminal_background()
        return self._detected_background
    
    def get_theme_mode(self, user_preference: str = 'auto') -> str:
        """
        Determine the theme mode based on user preference and terminal detection.
        
        Args:
            user_preference: 'auto', 'light', or 'dark'
            
        Returns:
            'light' or 'dark'
        """
        if user_preference == 'light':
            return 'light'
        elif user_preference == 'dark':
            return 'dark'
        elif user_preference == 'auto':
            detected = self.detect_background()
            if detected == 'light':
                return 'light'
            else:
                # Default to dark for 'dark' or 'unknown'
                return 'dark'
        else:
            # Invalid preference, default to auto
            return self.get_theme_mode('auto')
    
    def get_style(self, user_preference: str = 'auto') -> Style:
        """
        Get prompt_toolkit Style object for the current theme.
        
        Args:
            user_preference: 'auto', 'light', or 'dark'
            
        Returns:
            prompt_toolkit Style object
        """
        theme_mode = self.get_theme_mode(user_preference)
        colors = get_theme_colors(theme_mode)
        return Style.from_dict(colors)
    
    def get_theme_info(self, user_preference: str = 'auto') -> Dict:
        """
        Get information about the current theme settings.
        
        Returns:
            Dictionary with theme information
        """
        detected_bg = self.detect_background()
        theme_mode = self.get_theme_mode(user_preference)
        
        # Get macOS appearance if on macOS
        macos_info = {}
        if platform.system() == 'Darwin':
            macos_appearance = detect_macos_appearance()
            macos_info = {
                'macos_appearance': macos_appearance,
                'platform': 'macOS'
            }
        
        info = {
            'detected_background': detected_bg,
            'user_preference': user_preference,
            'active_theme': theme_mode,
            'colorfgbg': os.environ.get('COLORFGBG', 'not set'),
            'term_program': os.environ.get('TERM_PROGRAM', 'not set'),
            'term': os.environ.get('TERM', 'not set'),
        }
        
        # Add macOS-specific info
        info.update(macos_info)
        
        return info


# Global theme manager instance
theme_manager = ThemeManager()