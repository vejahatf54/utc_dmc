"""
PyInstaller hook for oracledb package
Ensures all oracledb components are properly included
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

# Collect all oracledb modules and data
datas, binaries, hiddenimports = collect_all('oracledb')

# Add specific oracledb modules
oracledb_modules = [
    'oracledb',
    'oracledb.thin',
    'oracledb.thick',
    'oracledb.defaults',
    'oracledb.connection',
    'oracledb.cursor',
    'oracledb.pool',
    'oracledb.exceptions',
    'oracledb.constants',
]

hiddenimports.extend(oracledb_modules)

# Collect all submodules to ensure nothing is missed
oracledb_submodules = collect_submodules('oracledb')
hiddenimports.extend(oracledb_submodules)

# Remove duplicates
hiddenimports = list(set(hiddenimports))
