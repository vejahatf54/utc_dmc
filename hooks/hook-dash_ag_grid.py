"""
PyInstaller hook for dash_ag_grid
Ensures package-info.json and other data files are included
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os

# Collect all data files from dash_ag_grid package
datas = collect_data_files('dash_ag_grid')

# Collect all submodules
hiddenimports = collect_submodules('dash_ag_grid')

# Ensure we get the package-info.json file specifically
try:
    import dash_ag_grid
    dag_path = os.path.dirname(dash_ag_grid.__file__)

    # Add package-info.json specifically
    package_info_path = os.path.join(dag_path, 'package-info.json')
    if os.path.exists(package_info_path):
        datas.append((package_info_path, 'dash_ag_grid'))

    # Add any other JSON files
    for file in os.listdir(dag_path):
        if file.endswith('.json'):
            file_path = os.path.join(dag_path, file)
            datas.append((file_path, 'dash_ag_grid'))

except ImportError:
    pass
