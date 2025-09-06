"""
PyInstaller hook for dash_mantine_components
Ensures all DMC components and assets are included for offline operation
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os

# Collect all data files from dash_mantine_components package
datas = collect_data_files('dash_mantine_components')

# Collect all submodules
hiddenimports = collect_submodules('dash_mantine_components')

# Add specific DMC components that are commonly used
dmc_components = [
    'dash_mantine_components.DatePickerInput',
    'dash_mantine_components.MantineProvider',
    'dash_mantine_components.Select',
    'dash_mantine_components.MultiSelect',
    'dash_mantine_components.Button',
    'dash_mantine_components.Card',
    'dash_mantine_components.Container',
    'dash_mantine_components.Title',
    'dash_mantine_components.Text',
    'dash_mantine_components.Group',
    'dash_mantine_components.Stack',
    'dash_mantine_components.Grid',
    # 'dash_mantine_components.Col',  # Not available in this version
    'dash_mantine_components.Space',
    'dash_mantine_components.Divider',
    'dash_mantine_components.Paper',
    'dash_mantine_components.Alert',
    'dash_mantine_components.Notification',
    'dash_mantine_components.Modal',
    'dash_mantine_components.Drawer',
    'dash_mantine_components.Anchor',
    # 'dash_mantine_components.Navbar',  # Not available in this version
    'dash_mantine_components.NavLink',
    'dash_mantine_components.ThemeIcon',
    'dash_mantine_components.CheckboxGroup',
    'dash_mantine_components.Checkbox',
    'dash_mantine_components.Switch',
    'dash_mantine_components.ColorPicker',
    'dash_mantine_components.Slider',
    'dash_mantine_components.NumberInput',
    'dash_mantine_components.TextInput',
    'dash_mantine_components.Textarea',
    'dash_mantine_components.PasswordInput',
    # 'dash_mantine_components.FileInput',  # Not available in this version
    'dash_mantine_components.Radio',
    'dash_mantine_components.RadioGroup',
    'dash_mantine_components.SegmentedControl',
    'dash_mantine_components.Tabs',
    'dash_mantine_components.TabsList',
    'dash_mantine_components.TabsTab',
    'dash_mantine_components.TabsPanel',
    'dash_mantine_components.Accordion',
    'dash_mantine_components.AccordionItem',
    'dash_mantine_components.AccordionControl',
    'dash_mantine_components.AccordionPanel',
    'dash_mantine_components.Tooltip',
    'dash_mantine_components.Popover',
    'dash_mantine_components.HoverCard',
    'dash_mantine_components.Menu',
    'dash_mantine_components.MenuItem',
    'dash_mantine_components.MenuTarget',
    'dash_mantine_components.MenuDropdown',
    'dash_mantine_components.Progress',
    'dash_mantine_components.RingProgress',
    'dash_mantine_components.Loader',
    'dash_mantine_components.Skeleton',
    'dash_mantine_components.Badge',
    'dash_mantine_components.Image',
    'dash_mantine_components.Avatar',
    'dash_mantine_components.AvatarGroup',
    'dash_mantine_components.Indicator',
]

hiddenimports.extend(dmc_components)

# Ensure we get any assets/static files from DMC
try:
    import dash_mantine_components as dmc
    dmc_path = os.path.dirname(dmc.__file__)
    
    # Add the entire DMC package to ensure assets are included
    if os.path.exists(dmc_path):
        # Look for common asset directories
        for subdir in ['assets', 'static', '_assets', 'dist']:
            asset_path = os.path.join(dmc_path, subdir)
            if os.path.exists(asset_path):
                datas.append((asset_path, f'dash_mantine_components/{subdir}'))
        
        # Add any JSON files that might contain component metadata
        for file in os.listdir(dmc_path):
            if file.endswith('.json'):
                file_path = os.path.join(dmc_path, file)
                datas.append((file_path, 'dash_mantine_components'))

except ImportError:
    pass
