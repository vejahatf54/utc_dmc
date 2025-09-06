"""
PyInstaller hook for DMC application components and services
Ensures all UI components and services are properly included
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

# Collect all submodules from components package
components_modules = collect_submodules('components')
hiddenimports = components_modules

# Collect all submodules from services package
services_modules = collect_submodules('services')
hiddenimports.extend(services_modules)

# Add specific component modules to ensure they're included
component_modules = [
    'components.bootstrap_icon',
    'components.csv_to_rtu_page',
    'components.custom_theme',
    'components.directory_selector',
    'components.elevation_page',
    'components.fetch_archive_page',
    'components.fluid_id_page',
    'components.home_page',
    'components.icon_mapping',
    'components.sidebar',
    'components.theme_switch',
]
hiddenimports.extend(component_modules)

# Add specific service modules to ensure they're included
service_modules = [
    'services.config_manager',
    'services.csv_to_rtu_service',
    'services.elevation_data_service',
    'services.exceptions',
    'services.fetch_archive_service',
    'services.fluid_id_service',
    'services.onesource_service',
    'services.pipe_analysis_service',
]
hiddenimports.extend(service_modules)

# Add dash_ag_grid data files - fix for package-info.json error
try:
    dag_datas = collect_data_files('dash_ag_grid')
    datas = dag_datas
except ImportError:
    datas = []

# Add Dash-specific modules
dash_modules = [
    'dash.dependencies',
    'dash.exceptions',
    'dash.resources',
    'dash._callback',
    'dash._callback_context',
    'dash._utils',
    'dash.development.base_component',
]
hiddenimports.extend(dash_modules)

# Add Plotly modules
plotly_modules = [
    'plotly.graph_objects',
    'plotly.express',
    'plotly.subplots',
    'plotly.colors',
    'plotly.figure_factory',
    'plotly.io',
    'plotly.offline',
]
hiddenimports.extend(plotly_modules)

# Add DMC-specific modules (only components that exist in the current version)
dmc_modules = [
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
    'dash_mantine_components.Space',
    'dash_mantine_components.Divider',
    'dash_mantine_components.Paper',
    'dash_mantine_components.Alert',
    'dash_mantine_components.Notification',
    'dash_mantine_components.Modal',
    'dash_mantine_components.Drawer',
    'dash_mantine_components.Anchor',
    'dash_mantine_components.NavLink',
    'dash_mantine_components.ThemeIcon',
    'dash_mantine_components.CheckboxGroup',
    'dash_mantine_components.Switch',
    'dash_mantine_components.ColorPicker',
    'dash_mantine_components.Slider',
]
hiddenimports.extend(dmc_modules)
