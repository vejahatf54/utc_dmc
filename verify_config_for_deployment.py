"""
Pre-deployment configuration verification script.
Ensures config.json is in the correct state for deployment (plaintext, not encrypted).
"""

import json
import sys
from pathlib import Path


def check_config_for_deployment():
    """Check if config.json is ready for deployment (plaintext, not encrypted)."""

    try:
        # Get the current working directory for debugging
        current_dir = Path.cwd()
        print(f"🔍 Working directory: {current_dir}")

        config_path = Path("config.json")
        print(f"🔍 Looking for config at: {config_path.absolute()}")

        if not config_path.exists():
            print("❌ ERROR: config.json not found!")
            print(f"❌ Searched in: {config_path.absolute()}")
            return False
    except Exception as e:
        print(f"❌ ERROR: Exception during initial setup: {e}")
        return False

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON in config.json: {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR: Could not read config.json: {e}")
        return False

    print("🔍 Checking configuration for deployment readiness...")
    print()

    # Check Oracle connection strings
    issues = []
    oracle_encrypted = []

    if 'oracle' in config and 'connection_strings' in config['oracle']:
        for key, value in config['oracle']['connection_strings'].items():
            if isinstance(value, str):
                if value.startswith("ENCRYPTED:"):
                    issues.append(
                        f"Oracle connection string '{key}' is encrypted")
                    oracle_encrypted.append(key)
                else:
                    print(f"✅ Oracle {key}: Plaintext (ready for deployment)")

    # Check app secret key
    app_secret_encrypted = False
    if 'app' in config and 'secret_key' in config['app']:
        secret_key = config['app']['secret_key']
        if isinstance(secret_key, str):
            if secret_key.startswith("ENCRYPTED:"):
                issues.append("App secret key is encrypted")
                app_secret_encrypted = True
            else:
                print("✅ App secret key: Plaintext (ready for deployment)")

    print()

    if issues:
        print("❌ DEPLOYMENT READINESS: FAILED")
        print()
        print("Issues found:")
        for issue in issues:
            print(f"  • {issue}")

        print()
        print("🔧 SOLUTION:")
        print("The config.json file appears to have been encrypted on this machine.")
        print("For deployment, you need the plaintext version:")
        print()

        if Path("config.original.json").exists():
            print("1. Restore from backup:")
            print("   copy config.original.json config.json")
        else:
            print("1. Manually edit config.json to restore plaintext passwords")

        print("2. Re-run this verification script")
        print("3. Proceed with build/deployment")
        print()
        print("REMEMBER: Encryption happens automatically on the TARGET machine!")

        return False
    else:
        print("✅ DEPLOYMENT READINESS: PASSED")
        print()
        print("Your config.json is ready for deployment:")
        print("  • All sensitive values are in plaintext")
        print("  • File can be safely deployed to target machines")
        print("  • Encryption will happen automatically on first run")
        print()
        print("🚀 You can proceed with building and deploying your application!")

        return True


if __name__ == "__main__":
    try:
        success = check_config_for_deployment()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
