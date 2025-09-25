# WUTC License Manager

This is a standalone license manager for the WUTC application. It generates server-based licenses with expiration dates.

## Features

- **Server-based licensing**: Licenses are tied to specific server names
- **Encrypted license files**: Uses Fernet encryption for security
- **Human-readable headers**: License files include readable information about the license
- **Built-in validation**: Can validate existing license files
- **GUI interface**: Easy-to-use Tkinter interface

## Requirements

- Python 3.7+
- cryptography package

## Installation

1. Install the required package:

   ```bash
   pip install cryptography
   ```

2. Run the license manager:
   ```bash
   python license_manager.py
   ```

## Usage

### Creating a License

1. **Server Name**: Enter the target server name or use "Auto-detect" for the current machine
2. **Duration**: Specify the license duration in days (presets available: 30, 90, 365, or unlimited)
3. **Additional Info**: Optional notes about the license
4. **Generate Preview**: Click to see what the license will look like
5. **Save License**: Save the license to a .lic file

### Validating a License

1. Click "Validate License"
2. Select a .lic file
3. The manager will show the license details and validation status

### License File Format

License files (.lic) contain:

- **Header section**: Human-readable information about the license
- **Encrypted section**: Encrypted license data that cannot be modified

Example license file structure:

```
# WUTC Application License
# ========================
#
# Server Name: SERVER-01
# Issue Date:  2024-09-24 10:30:00
# Expiry Date: 2025-09-24 10:30:00
# Duration:    365 days
# Version:     1.0
#
# This license is tied to the server name specified above.
# Do not modify this file or the license will become invalid.
#
# ========================

[Encrypted license data follows...]
```

## Integration with WUTC

The WUTC application automatically:

1. Looks for .lic files in its directory
2. Validates the license against the current server name
3. Runs in trial mode (30 days) if no valid license is found
4. Shows license status in the application

## Security Notes

- The encryption key (`license_key.key`) must be kept secure
- Licenses are tied to specific server names and cannot be transferred
- Modifying license files will invalidate them
- The same encryption key must be used for both generation and validation

## Troubleshooting

### "License server mismatch" error

- The license was created for a different server name
- Generate a new license for the current server

### "License key file not found" error

- The `license_key.key` file is missing
- Make sure both the license manager and WUTC app have access to the same key file

### "Cryptography package not available" error

- Install the cryptography package: `pip install cryptography`
