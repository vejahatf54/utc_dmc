"""
Icon mapping from DashIconify to Bootstrap Icons

This file contains the mapping between DashIconify icon names and their Bootstrap icon equivalents.
"""

ICON_MAPPING = {
    # House/Home icons
    "noto:house": "house",
    
    # Settings/Gear icons
    "tabler:settings": "gear",
    "tabler:adjustments": "sliders",
    
    # Sun/Moon/Theme icons
    "radix-icons:sun": "sun",
    "radix-icons:moon": "moon",
    
    # Palette/Theme icons
    "tabler:palette": "palette",
    "emojione:artist-palette": "palette",
    
    # Info/Help icons
    "tabler:info-circle": "info-circle",
    "tabler:help": "question-circle",
    
    # Alert/Warning icons
    "tabler:alert-circle": "exclamation-circle",
    
    # Check/Success icons
    "tabler:check": "check",
    
    # Lightbulb/Tips icons
    "tabler:lightbulb": "lightbulb",
    
    # Folder icons
    "tabler:folder": "folder",
    "tabler:folder-open": "folder-open",
    "tabler:folder-search": "folder-search",
    
    # Upload/Download icons
    "tabler:file-upload": "upload",
    "tabler:cloud-upload": "cloud-upload",
    "tabler:file-export": "download",
    
    # Transform/Convert icons
    "tabler:transform": "arrow-repeat",
    "noto:repeat-button": "arrow-repeat",
    "tabler:arrows-left-right": "arrow-left-right",
    
    # Refresh icons
    "tabler:refresh": "arrow-clockwise",
    
    # File icons
    "tabler:file-spreadsheet": "file-earmark-spreadsheet",
    "noto:page-with-curl": "file-text",
    
    # Typography/Text icons
    "tabler:typography": "type",
    "tabler:hash": "hash",
    
    # Close/X icons
    "tabler:x": "x",
    
    # Other icons as needed
}


def get_bootstrap_icon(dashIconify_icon):
    """
    Get the Bootstrap icon equivalent for a DashIconify icon.
    
    Args:
        dashIconify_icon (str): The DashIconify icon name
        
    Returns:
        str: The Bootstrap icon name
    """
    return ICON_MAPPING.get(dashIconify_icon, "question-circle")  # Default fallback icon
