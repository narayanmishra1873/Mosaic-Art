"""
Configuration and constants for the Color-by-Numbers application.
"""

from typing import List, Tuple
from dataclasses import dataclass

# Color palette configuration
@dataclass
class ColorPalette:
    """Represents a color in the palette."""
    label: str
    hex_value: str
    rgb: Tuple[int, int, int]
    
    @classmethod
    def from_hex(cls, label: str, hex_value: str) -> 'ColorPalette':
        """Create a ColorPalette from hex value."""
        hex_value = hex_value.lstrip('#')
        rgb = tuple(int(hex_value[i:i+2], 16) for i in (0, 2, 4))
        return cls(label, hex_value, rgb)


# Default UI configuration (window will open fullscreen)
DEFAULT_WINDOW_WIDTH = 1400
DEFAULT_WINDOW_HEIGHT = 900
CANVAS_WIDTH = 600
CANVAS_HEIGHT = 600

# PDF configuration
PDF_DPI = 72
PDF_MARGIN = 0.15  # inches (reduced to maximize grid size)

# Image processing defaults
DEFAULT_ROWS = 168
DEFAULT_COLUMNS = 120
CONTRAST_ENHANCEMENT = 1.2  # 20% contrast increase
