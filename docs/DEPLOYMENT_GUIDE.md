# Secure Configuration Deployment Guide

## Overview

This application now supports automatic encryption of sensitive configuration values on first run. This allows you to deploy the application with plaintext configuration files, and the application will automatically encrypt sensitive values (passwords, connection strings, secret keys) on its first startup on the target machine.

## Key Features

- **First-Run Encryption**: Sensitive values are automatically encrypted when the application starts for the first time
- **Machine-Specific**: Encrypted configurations are tied to the specific machine and cannot be transferred
- **Windows Service Compatible**: Works correctly when deployed as a Windows service using winsw
- **Automatic Backup**: Original configuration is backed up before encryption
- **Transparent Operation**: Application code doesn't change - ConfigManager handles encryption/decryption automatically

## Deployment Process

### ⚠️ CRITICAL: Build Process Configuration

**IMPORTANT**: The build process does NOT encrypt the configuration file. The `config.json` must remain in plaintext during:

- Development
- Building/packaging
- Deployment to target machines

Encryption only happens automatically when the application runs for the first time on the target machine.

### 1. Prepare Configuration

Create your `config.json` file with plaintext values:

```json
{
  "oracle": {
    "connection_strings": {
      "CMT_ICS": "Data Source=PROD_DB;User Id=production_user;Password=YourActualPassword;",
      "CMT_CNPL": "Data Source=PROD_DB2;User Id=production_user2;Password=AnotherPassword;"
    },
    "timeout": 30
  },
  "app": {
    "secret_key": "your-production-secret-key"
  }
}
```

### 2. Deploy Application Files

Copy your application files to the target machine:

- `app.py`
- `config.json` (with plaintext values)
- `services/` directory
- All other application files
- Dependencies (Python environment)

### 3. First Run

When the application starts for the first time:

1. **Automatic Detection**: ConfigManager detects plaintext sensitive values
2. **Backup Creation**: Creates `config.original.json` backup of original file
3. **Encryption**: Encrypts sensitive values using machine-specific encryption
4. **File Update**: Updates `config.json` with encrypted values
5. **Normal Operation**: Application continues with decrypted values in memory

After first run, your `config.json` will look like:

```json
{
  "oracle": {
    "connection_strings": {
      "CMT_ICS": "ENCRYPTED:base64encodedencrypteddata...",
      "CMT_CNPL": "ENCRYPTED:base64encodedencrypteddata..."
    },
    "timeout": 30
  },
  "app": {
    "secret_key": "ENCRYPTED:base64encodedencrypteddata..."
  }
}
```

### 4. Windows Service Deployment (using winsw)

The application is fully compatible with Windows service deployment and uses **machine-specific** (not user-specific) encryption:

#### Service Account Flexibility

- ✅ Works with any Windows service account (Local System, Network Service, custom accounts)
- ✅ Multiple users on the same machine can access the same encrypted config
- ✅ Service account changes don't affect encrypted configuration
- ✅ Perfect for production environments with dedicated service accounts

#### Deployment Steps

1. **Install winsw**: Place `winsw.exe` and your service configuration XML
2. **Service Config**: Configure your service to run the Python application
3. **First Run**: Service will perform first-run encryption automatically (machine-bound)
4. **Subsequent Runs**: Service starts normally with encrypted configuration
5. **Account Changes**: Works seamlessly if you change service accounts later

Example winsw configuration:

```xml
<service>
    <id>WUTCService</id>
    <name>WUTC Application</name>
    <description>WUTC Application Service</description>
    <executable>C:\Path\To\Python\python.exe</executable>
    <arguments>C:\Path\To\Your\App\app.py</arguments>
    <workingdirectory>C:\Path\To\Your\App</workingdirectory>
    <serviceaccount>
        <domain>YourDomain</domain>
        <user>ServiceAccount</user>
        <password>ServicePassword</password>
    </serviceaccount>
    <logmode>rotate</logmode>
</service>
```

#### Service Account Best Practices

- Use a dedicated service account with minimal required permissions
- The encrypted config will work regardless of which service account you use
- You can change service accounts without re-encrypting the configuration

## Security Details

### Encryption Method

- Uses AES-256-CBC encryption
- Machine-specific key derivation (similar to Windows DPAPI)
- Key derived from: computer name, username, domain, and application-specific salt
- Each encrypted value uses a unique random IV

### What Gets Encrypted

1. **Oracle Connection Strings**: `oracle.connection_strings.*`
2. **Application Secret Key**: `app.secret_key`

### Machine Binding

The encryption key is derived from machine-specific information:

- Computer name (`COMPUTERNAME`)
- Domain name (`USERDNSDOMAIN` or `USERDOMAIN`)
- MAC address of primary network interface (hardware binding)
- Platform details (machine type, system, node)
- Application-specific salt

**Important**: The key is machine-specific, NOT user-specific, making it perfect for Windows service deployment with strong hardware binding.

This means:

- ✅ Configuration works on the machine where it was encrypted
- ✅ Configuration works for ANY user on the same machine (including service accounts)
- ✅ Perfect for Windows service deployment with different service accounts
- ✅ Strong hardware binding via MAC address prevents VM cloning attacks
- ✅ Domain binding ensures proper corporate environment isolation
- ❌ Configuration will NOT work if copied to another machine
- ❌ Configuration will NOT work if network hardware changes
- ❌ Configuration will NOT work if machine joins different domain

## Troubleshooting

### Configuration Not Encrypting

**Check logs** for error messages:

```
grep "First run detected" logs/wutc_*.log
```

**Verify cryptography library** is installed:

```powershell
pip list | findstr cryptography
```

### Encryption Failed

If encryption fails:

1. Application continues with plaintext values
2. Check file permissions on config.json
3. Check available disk space
4. Review error logs

### Configuration Accidentally Encrypted During Build

If `config.json` gets encrypted during development/build (it shouldn't!):

1. **Check for backup**: Look for `config.original.json`
2. **Restore plaintext**: Copy `config.original.json` to `config.json`
3. **Clean build**: Run build process again
4. **Verify**: Ensure `config.json` contains plaintext passwords before deployment

### Configuration Stops Working After Hardware/Network Changes

If encrypted config stops working due to hardware changes:

1. **Network hardware change**: MAC address changed, re-encryption needed
2. **Domain change**: Machine joined different domain, re-encryption needed
3. **VM migration**: If running in VM and MAC address changed

**Solution**:

1. Restore from `config.original.json` backup
2. Restart application for fresh encryption with new hardware signature
3. Or manually replace encrypted values with plaintext and restart

### Configuration Not Working After Transfer

If you accidentally copy encrypted config to another machine:

1. Replace with the backed up `config.original.json`
2. Rename back to `config.json`
3. Restart application for fresh encryption

### Service Detection Issues

The application attempts to detect if it's running as a Windows service. If detection fails:

- Check that `psutil` library is installed
- Review service configuration
- Check service logs for warnings

## Files Created During Encryption

- `config.original.json`: Backup of original plaintext configuration
- `config.json`: Updated with encrypted values
- Log entries documenting the encryption process

## Best Practices

1. **Test First**: Test the application on a development machine first
2. **Backup Strategy**: Keep secure backups of your plaintext configuration
3. **Service Account**: Use a dedicated service account for Windows service deployment
4. **Log Monitoring**: Monitor application logs during first deployment
5. **Access Control**: Restrict access to the application directory and config files

## Command Line Testing

You can test the encryption functionality using the provided test script:

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run first-run encryption test
python test_first_run_encryption.py
```

This will simulate the deployment process and verify that encryption works correctly.
