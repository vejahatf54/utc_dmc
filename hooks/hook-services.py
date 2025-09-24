"""
PyInstaller hook for services modules
Ensures all service modules are properly included
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

# Collect all submodules from services package
hiddenimports = collect_submodules('services')

# Collect data files (if any)
datas, binaries, additional_imports = collect_all('services')
hiddenimports.extend(additional_imports)

# Add specific service modules to ensure they're included
service_modules = [
    'services.config_manager',
    'services.secure_config_manager',
    'services.csv_to_rtu_service',
    'services.date_range_service',
    'services.elevation_data_service',
    'services.exceptions',
    'services.fetch_archive_service',
    'services.fetch_rtu_data_service',
    'services.fluid_id_service',
    'services.fluid_properties_service',
    'services.linefill_service',
    'services.onesource_service',
    'services.pipe_analysis_service',
    'services.pymbsd_service',
    'services.replace_text_service',
    'services.replay_file_poke_service',

    'services.rtu_service',
    'services.sps_time_converter_service',
]
hiddenimports.extend(service_modules)
