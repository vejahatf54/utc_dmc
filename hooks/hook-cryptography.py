"""
PyInstaller hook for cryptography package
Ensures all cryptography components are properly included for oracledb compatibility
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

# Collect all cryptography modules and data
datas, binaries, hiddenimports = collect_all('cryptography')

# Add specific cryptography modules that oracledb needs
cryptography_modules = [
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
    'cryptography.hazmat.primitives.serialization.pkcs12',
    'cryptography.hazmat.primitives.asymmetric',
    'cryptography.hazmat.primitives.asymmetric.rsa',
    'cryptography.hazmat.primitives.asymmetric.dsa',
    'cryptography.hazmat.primitives.asymmetric.ec',
    'cryptography.hazmat.backends',
    'cryptography.hazmat.backends.openssl',
    'cryptography.hazmat.backends.openssl.backend',
    'cryptography.fernet',
    'cryptography.x509',
]

hiddenimports.extend(cryptography_modules)

# Collect all submodules to ensure nothing is missed
cryptography_submodules = collect_submodules('cryptography')
hiddenimports.extend(cryptography_submodules)

# Remove duplicates
hiddenimports = list(set(hiddenimports))
