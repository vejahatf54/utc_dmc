# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for DMC Dash Application
This creates a one-file executable with all dependencies included
Config.json is kept external to the executable for easy configuration
"""

import sys
import os
from pathlib import Path

# Get the project root directory
project_root = Path().cwd()

block_cipher = None

# Define all the data files and folders to include
datas = [
    # Include all assets (CSS, images, fonts, etc.)
    (str(project_root / 'assets'), 'assets'),
    
    # Include components as data (for dynamic imports)
    (str(project_root / 'components'), 'components'),
    
    # Include services as data (for dynamic imports)
    (str(project_root / 'services'), 'services'),
    
    # Include SQL files
    (str(project_root / 'sql'), 'sql'),
    
    # Include requirements.txt for reference
    (str(project_root / 'requirements.txt'), '.'),
    
    # NOTE: config.json is intentionally NOT included here
    # It will be placed next to the .exe file for external configuration
]

# Add dash_ag_grid data files - this fixes the package-info.json error
try:
    from PyInstaller.utils.hooks import collect_data_files
    dag_data = collect_data_files('dash_ag_grid')
    datas.extend(dag_data)
    print(f"Added {len(dag_data)} dash_ag_grid data files")
except ImportError:
    # Fallback method
    try:
        import dash_ag_grid
        dag_path = os.path.dirname(dash_ag_grid.__file__)
        # Add specific files we know exist
        for file in ['package-info.json', 'metadata.json']:
            file_path = os.path.join(dag_path, file)
            if os.path.exists(file_path):
                datas.append((file_path, 'dash_ag_grid'))
    except ImportError:
        pass

# Add dash_mantine_components data files for offline operation
try:
    from PyInstaller.utils.hooks import collect_data_files
    dmc_data = collect_data_files('dash_mantine_components')
    datas.extend(dmc_data)
    print(f"Added {len(dmc_data)} DMC data files")
except ImportError:
    # Fallback method for DMC
    try:
        import dash_mantine_components as dmc
        dmc_path = os.path.dirname(dmc.__file__)
        # Add the entire DMC package assets
        if os.path.exists(dmc_path):
            datas.append((dmc_path, 'dash_mantine_components'))
    except ImportError:
        print("Warning: dash_mantine_components not found")

# Add cryptography data files for oracledb compatibility
try:
    from PyInstaller.utils.hooks import collect_data_files, collect_all
    crypto_datas, crypto_binaries, crypto_hiddenimports = collect_all('cryptography')
    datas.extend(crypto_datas)
    print(f"Added {len(crypto_datas)} cryptography data files")
except ImportError:
    print("Warning: cryptography collection failed")

# Add oracledb data files
try:
    from PyInstaller.utils.hooks import collect_data_files
    oracle_data = collect_data_files('oracledb')
    datas.extend(oracle_data)
    print(f"Added {len(oracle_data)} oracledb data files")
except ImportError:
    print("Warning: oracledb data collection failed")

# Note: dash_bootstrap_components removed - no longer used in the application

# Hidden imports - modules that PyInstaller might miss
hiddenimports = [
    # Dash and related
    'dash',
    'dash.dependencies',
    'dash._callback',
    'dash._callback_context',
    'dash._utils',
    'dash.development.base_component',
    'dash.exceptions',
    'dash.resources',
    'dash.dcc',
    'dash.html',
    'dash.callback_context',
    'dash.clientside_callback',
    'dash.ClientsideFunction',
    'dash.no_update',
    'dash.ctx',
    'dash.ALL',
    'dash_ag_grid',
    'dash_mantine_components',
    'dash_mantine_components.DatePickerInput',
    'dash_mantine_components.MantineProvider',
    'dash_mantine_components.Checkbox',
    'dash_mantine_components.CheckboxGroup',
    'dash_mantine_components.TagsInput',
    'dash_mantine_components.MultiSelect',
    'dash_mantine_components.Autocomplete',
    'plotly',
    'plotly.graph_objects',
    'plotly.express',
    'plotly.subplots',
    'plotly.colors',
    'plotly.figure_factory',
    'plotly.io',
    'plotly.offline',
    
    # Flask and web server
    'flask',
    'werkzeug',
    'werkzeug.serving',
    'werkzeug.middleware.proxy_fix',
    
    # Data processing
    'pandas',
    'numpy',
    'scipy',
    'scipy.signal',
    'scipy.stats',
    'json',
    'csv',
    'narwhals',
    'logging',
    'dataclasses',
    'traceback',
    
    # Database connectivity
    'pyodbc',
    'sqlalchemy',
    'sqlalchemy.engine',
    'sqlalchemy.pool',
    'sqlalchemy.text',
    'oracledb',
    'oracledb.thin',
    'oracledb.thick',
    'oracledb.defaults',
    
    # File operations
    'pathlib',
    'os',
    'shutil',
    'tempfile',
    'zipfile',
    'pillow',
    'PIL',
    'PIL.Image',
    
    # Date/time
    'datetime',
    'dateutil',
    'pytz',
    'tzdata',
    
    # Utilities
    'requests',
    'yaml',
    'base64',
    'io',
    'retrying',
    'setuptools',
    'six',
    'zipp',
    'importlib_metadata',
    'typing_extensions',
    'psutil',
    'secrets',
    
    # Cryptography and security - comprehensive imports for oracledb
    'cryptography',
    'cryptography.hazmat',
    'cryptography.hazmat.primitives',
    'cryptography.hazmat.primitives.kdf',
    'cryptography.hazmat.primitives.kdf.pbkdf2',
    'cryptography.hazmat.primitives.kdf.scrypt',
    'cryptography.hazmat.primitives.kdf.hkdf',
    'cryptography.hazmat.primitives.kdf.kbkdf',
    'cryptography.hazmat.primitives.kdf.concatkdf',
    'cryptography.hazmat.primitives.hashes',
    'cryptography.hazmat.primitives.ciphers',
    'cryptography.hazmat.primitives.ciphers.algorithms',
    'cryptography.hazmat.primitives.ciphers.modes',
    'cryptography.hazmat.primitives.serialization',
    'cryptography.hazmat.primitives.asymmetric',
    'cryptography.hazmat.primitives.asymmetric.rsa',
    'cryptography.hazmat.backends',
    'cryptography.hazmat.backends.openssl',
    'cryptography.hazmat.backends.openssl.backend',
    'cryptography.fernet',
    'cffi',
    'pycparser',
    
    # SPS API
    'sps-api',
    
    # .NET integration
    'pythonnet',
    'clr_loader',
    
    # Windows specific (for file dialogs and UI)
    'tkinter',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'win32api',
    'win32gui',
    'win32con',
    'win32file',
    'win32security',
    'pywintypes',
    'pythoncom',
    
    # Your application modules - Components
    'components.bootstrap_icon',
    'components.csv_to_rtu_page',
    'components.custom_theme',
    'components.directory_selector',
    'components.elevation_page',
    'components.fetch_archive_page',
    'components.fetch_rtu_data_page',
    'components.file_selector',
    'components.flowmeter_acceptance_page',
    'components.fluid_id_page',
    'components.fluid_properties_page',
    'components.home_page',
    'components.icon_mapping',
    'components.linefill_page',
    'components.pymbsd_page',
    'components.replace_text_page',
    'components.replay_file_poke_page',
    'components.review_to_csv_page',
    'components.rtu_resizer_page',
    'components.rtu_to_csv_page',
    'components.sidebar',
    'components.sps_time_converter_page',
    'components.theme_switch',
    
    # Services
    'services.config_manager',
    'services.secure_config_manager',
    'services.csv_to_rtu_service',
    'services.date_range_service',
    'services.elevation_data_service',
    'services.exceptions',
    'services.fetch_archive_service',
    'services.fetch_rtu_data_service',
    'services.flowmeter_acceptance_service',
    'services.fluid_id_service',
    'services.fluid_properties_service',
    'services.linefill_service',
    'services.onesource_service',
    'services.pipe_analysis_service',
    'services.pymbsd_service',
    'services.replace_text_service',
    'services.replay_file_poke_service',
    'services.review_to_csv_service',
    'services.rtu_service',
    'services.sps_time_converter_service',
]

# Collect all Python files in components and services directories
for directory in ['components', 'services']:
    dir_path = project_root / directory
    if dir_path.exists():
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    rel_path = Path(root).relative_to(project_root)
                    module_name = str(rel_path / file[:-3]).replace(os.sep, '.')
                    if module_name not in hiddenimports:
                        hiddenimports.append(module_name)

# Exclude unnecessary modules to reduce size
excludes = [
    # 'tkinter',  # Needed for file dialogs - don't exclude
    # 'unittest',  # Needed by numpy.testing which scipy depends on - don't exclude
    'test',
    'tests',
    'pytest',
    'IPython',
    'jupyter',
    'notebook',
    'matplotlib.backends._backend_tk',
    'PyQt5',
    'PyQt6',
    'PySide2',
    'PySide6',
]

a = Analysis(
    ['app.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[str(project_root / 'hooks')],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove duplicate entries
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DMC',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to False for windowed mode (no console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / 'assets' / 'homeimage.png') if (project_root / 'assets' / 'homeimage.png').exists() else None,
)
