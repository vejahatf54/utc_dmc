"""
Bootstrap Icon component for replacing DashIconify
"""
from dash import html


def BootstrapIcon(icon, width=None, height=None, color=None, style=None, className=None, **kwargs):
    """
    Create a Bootstrap icon using CSS classes.
    
    Args:
        icon (str): Bootstrap icon name (e.g., 'house', 'gear', 'sun', etc.)
        width (int/str): Icon width
        height (int/str): Icon height  
        color (str): Icon color
        style (dict): Additional CSS styles
        className (str): Additional CSS classes
        **kwargs: Additional props to pass to the element
    
    Returns:
        html.I: Bootstrap icon element
    """
    # Ensure icon name has 'bi-' prefix
    if not icon.startswith('bi-'):
        icon = f'bi-{icon}'
    
    # Build style dict
    icon_style = {}
    if width is not None:
        icon_style['fontSize'] = f'{width}px' if isinstance(width, int) else width
    if height is not None:
        icon_style['lineHeight'] = f'{height}px' if isinstance(height, int) else height
    if color is not None:
        icon_style['color'] = color
    
    # Merge with user-provided style
    if style:
        icon_style.update(style)
    
    # Build class name
    classes = [icon]
    if className:
        classes.append(className)
    
    return html.I(
        className=' '.join(classes),
        style=icon_style,
        **kwargs
    )
