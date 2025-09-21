"""
Configuration Manager for DMC application.
Provides centralized configuration loading capabilities with automatic decryption of sensitive values.
"""

import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from logging_config import get_logger

logger = get_logger(__name__)


class ConfigManager:
    """
    Centralized configuration manager.
    Manages loading and caching of configuration settings.
    """

    def __init__(self, config_file_path: str = None):
        """
        Initialize the configuration manager.

        Args:
            config_file_path: Path to the configuration file. Defaults to config.json in app root.
        """
        if config_file_path is None:
            # When running as a PyInstaller executable, look for config.json next to the .exe file
            if hasattr(sys, '_MEIPASS'):
                # Running as a PyInstaller bundle
                executable_dir = Path(sys.executable).parent
                config_file_path = executable_dir / "config.json"
                logger.debug(
                    f"Running as packaged app, looking for config at: {config_file_path}")
            else:
                # Running in development mode
                app_root = Path(__file__).parent.parent
                config_file_path = app_root / "config.json"
                logger.debug(
                    f"Running in development mode, looking for config at: {config_file_path}")

        self.config_file_path = Path(config_file_path)
        self._config: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._last_modified = None

        # Initialize secure config manager for decryption
        self._secure_manager = None
        self._init_secure_manager()

        # Check if running as Windows service
        self._is_service = self._check_if_running_as_service()
        if self._is_service:
            logger.info("Detected running as Windows service")

        # Load initial configuration
        self._load_config()

    def _init_secure_manager(self):
        """Initialize the secure configuration manager for decryption."""
        try:
            from .secure_config_manager import SecureConfigManager
            self._secure_manager = SecureConfigManager()
            logger.debug("Secure configuration manager initialized")
        except ImportError as e:
            logger.warning(f"Secure configuration manager not available: {e}")
            self._secure_manager = None
        except Exception as e:
            logger.error(
                f"Error initializing secure configuration manager: {e}")
            self._secure_manager = None

    def _check_if_running_as_service(self) -> bool:
        """
        Check if the application is running as a Windows service.
        This is useful when deployed with winsw.

        Returns:
            True if running as a Windows service
        """
        try:
            # Check if we're running as a service by looking at environment variables
            # or other service-specific indicators
            import psutil
            current_process = psutil.Process()
            parent_process = current_process.parent()

            if parent_process:
                parent_name = parent_process.name().lower()
                # Common service parent processes
                service_parents = ['services.exe', 'winsw.exe', 'sc.exe']
                if any(parent in parent_name for parent in service_parents):
                    return True

            # Alternative check: see if we have a console window
            # Services typically don't have console windows
            try:
                import sys
                if not hasattr(sys.stdin, 'isatty') or not sys.stdin.isatty():
                    # Might be running as a service
                    return True
            except:
                pass

            return False

        except Exception as e:
            logger.debug(f"Could not determine if running as service: {e}")
            return False

    def _load_config(self) -> bool:
        """
        Load configuration from the JSON file.

        Returns:
            True if configuration was loaded successfully, False otherwise.
        """
        try:
            with self._lock:
                if not self.config_file_path.exists():
                    logger.warning(
                        f"Configuration file not found: {self.config_file_path}")
                    self._config = self._get_default_config()
                    return False

                # Check if file has been modified
                current_modified = self.config_file_path.stat().st_mtime
                if self._last_modified is not None and current_modified == self._last_modified:
                    return True

                with open(self.config_file_path, 'r', encoding='utf-8') as f:
                    new_config = json.load(f)

                # Merge with defaults to ensure all required keys exist
                default_config = self._get_default_config()
                merged_config = self._merge_configs(default_config, new_config)

                # Check if first-run encryption is needed (but not during development)
                if self._should_encrypt_on_first_run(merged_config) and self._allow_encryption():
                    logger.info(
                        "First run detected - encrypting sensitive configuration values...")
                    if self._encrypt_config_file_first_run(merged_config):
                        logger.info(
                            "Configuration encrypted successfully on first run")
                        # Reload the config after encryption
                        with open(self.config_file_path, 'r', encoding='utf-8') as f:
                            new_config = json.load(f)
                        merged_config = self._merge_configs(
                            default_config, new_config)
                    else:
                        logger.warning(
                            "Failed to encrypt configuration on first run - continuing with plaintext")
                elif self._should_encrypt_on_first_run(merged_config) and not self._allow_encryption():
                    logger.debug(
                        "First-run encryption skipped - development mode or encryption disabled")

                # Decrypt sensitive values if secure manager is available
                self._config = self._decrypt_sensitive_values(merged_config)
                self._last_modified = current_modified

                logger.debug(
                    f"Configuration loaded successfully from {self.config_file_path}")
                return True

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            return False
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return False

    def _get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration values.

        Returns:
            Dictionary containing default configuration
        """
        return {
            "archive": {
                "base_path": "",
                "timeout": 30
            }
        }

    def _merge_configs(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge user configuration with default configuration.

        Args:
            default: Default configuration dictionary
            user: User configuration dictionary

        Returns:
            Merged configuration dictionary
        """
        merged = default.copy()

        for key, value in user.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value

        return merged

    def _decrypt_sensitive_values(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt sensitive values in the configuration.

        Args:
            config: Configuration dictionary to decrypt

        Returns:
            Configuration with sensitive values decrypted
        """
        if not self._secure_manager:
            # No secure manager available, return config as-is
            return config

        try:
            decrypted_config = config.copy()

            # Decrypt Oracle connection strings
            if 'oracle' in decrypted_config and 'connection_strings' in decrypted_config['oracle']:
                connection_strings = decrypted_config['oracle']['connection_strings']
                for key, value in connection_strings.items():
                    if isinstance(value, str):
                        decrypted_value = self._secure_manager.decrypt_value(
                            value)
                        connection_strings[key] = decrypted_value
                        if decrypted_value != value:  # Only log if actually decrypted
                            logger.debug(
                                f"Decrypted oracle.connection_strings.{key}")

            # Decrypt app secret key
            if 'app' in decrypted_config and 'secret_key' in decrypted_config['app']:
                original_key = decrypted_config['app']['secret_key']
                decrypted_key = self._secure_manager.decrypt_value(
                    original_key)
                decrypted_config['app']['secret_key'] = decrypted_key
                if decrypted_key != original_key:  # Only log if actually decrypted
                    logger.debug("Decrypted app.secret_key")

            return decrypted_config

        except Exception as e:
            logger.error(f"Error decrypting sensitive values: {e}")
            logger.warning(
                "Using configuration without decryption - some features may not work!")
            return config

    def _should_encrypt_on_first_run(self, config: Dict[str, Any]) -> bool:
        """
        Check if configuration should be encrypted on first run.
        Returns True if sensitive values are found in plaintext (not encrypted).

        Args:
            config: Configuration dictionary to check

        Returns:
            True if encryption is needed on first run
        """
        if not self._secure_manager:
            return False

        try:
            # Check Oracle connection strings
            if 'oracle' in config and 'connection_strings' in config['oracle']:
                connection_strings = config['oracle']['connection_strings']
                for key, value in connection_strings.items():
                    if isinstance(value, str) and not self._secure_manager.is_encrypted(value):
                        # Found plaintext connection string - encryption needed
                        logger.debug(
                            f"Found plaintext connection string: oracle.connection_strings.{key}")
                        return True

            # Check app secret key
            if 'app' in config and 'secret_key' in config['app']:
                secret_key = config['app']['secret_key']
                if isinstance(secret_key, str) and not self._secure_manager.is_encrypted(secret_key):
                    # Found plaintext secret key - encryption needed
                    logger.debug("Found plaintext secret key: app.secret_key")
                    return True

            # All sensitive values are already encrypted or not found
            return False

        except Exception as e:
            logger.error(f"Error checking if encryption is needed: {e}")
            return False

    def _allow_encryption(self) -> bool:
        """
        Check if configuration encryption should be allowed.
        This prevents accidental encryption during development, testing, or build processes.

        Returns:
            True if encryption is allowed
        """
        try:
            # Check for development/testing environment variables that disable encryption
            if os.environ.get('DMC_DISABLE_ENCRYPTION', '').lower() in ('true', '1', 'yes'):
                logger.debug(
                    "Encryption disabled by DMC_DISABLE_ENCRYPTION environment variable")
                return False

            # Check if we're running in development mode (has sys._MEIPASS means packaged)
            if not hasattr(sys, '_MEIPASS'):
                # Running in development mode - check if we should allow encryption
                if os.environ.get('DMC_ALLOW_DEV_ENCRYPTION', '').lower() not in ('true', '1', 'yes'):
                    logger.debug(
                        "Encryption disabled in development mode (set DMC_ALLOW_DEV_ENCRYPTION=true to enable)")
                    return False

            # Check if we're running during build process
            if os.environ.get('DMC_BUILD_MODE', '').lower() in ('true', '1', 'yes'):
                logger.debug("Encryption disabled during build process")
                return False

            # Default: allow encryption (for production/packaged deployment)
            return True

        except Exception as e:
            logger.error(f"Error checking encryption allowance: {e}")
            # On error, be conservative and allow encryption (for production safety)
            return True

    def _encrypt_config_file_first_run(self, config: Dict[str, Any]) -> bool:
        """
        Encrypt the configuration file on first run.
        Creates a backup and encrypts sensitive values in place.

        Args:
            config: Current configuration dictionary

        Returns:
            True if encryption was successful
        """
        if not self._secure_manager:
            logger.error("Secure manager not available for encryption")
            return False

        try:
            # Create a backup of the original config file
            backup_path = self.config_file_path.with_suffix('.original.json')
            if not backup_path.exists():  # Only create backup if it doesn't exist
                import shutil
                shutil.copy2(self.config_file_path, backup_path)
                logger.info(
                    f"Created backup of original config: {backup_path}")

            # Load current config from file (to get the exact format)
            with open(self.config_file_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)

            # Encrypt sensitive values
            encrypted_config = file_config.copy()

            # Encrypt Oracle connection strings
            if 'oracle' in encrypted_config and 'connection_strings' in encrypted_config['oracle']:
                connection_strings = encrypted_config['oracle']['connection_strings']
                for key, value in connection_strings.items():
                    if isinstance(value, str) and not self._secure_manager.is_encrypted(value):
                        encrypted_value = self._secure_manager.encrypt_value(
                            value)
                        connection_strings[key] = encrypted_value
                        logger.info(
                            f"Encrypted oracle.connection_strings.{key}")

            # Encrypt app secret key
            if 'app' in encrypted_config and 'secret_key' in encrypted_config['app']:
                secret_key = encrypted_config['app']['secret_key']
                if isinstance(secret_key, str) and not self._secure_manager.is_encrypted(secret_key):
                    encrypted_key = self._secure_manager.encrypt_value(
                        secret_key)
                    encrypted_config['app']['secret_key'] = encrypted_key
                    logger.info("Encrypted app.secret_key")

            # Write the encrypted config back to file
            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                json.dump(encrypted_config, f, indent=4)

            logger.info("Configuration file encrypted successfully")
            logger.info(
                "IMPORTANT: This config file is now tied to this machine and cannot be transferred!")
            return True

        except Exception as e:
            logger.error(f"Error encrypting configuration file: {e}")
            return False

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key_path: Dot-separated path to the configuration key (e.g., 'archive.base_path')
            default: Default value to return if key is not found

        Returns:
            Configuration value or default if not found
        """
        with self._lock:
            try:
                keys = key_path.split('.')
                value = self._config

                for key in keys:
                    if isinstance(value, dict) and key in value:
                        value = value[key]
                    else:
                        return default

                return value

            except Exception as e:
                logger.error(
                    f"Error getting configuration key '{key_path}': {e}")
                return default

    def get_archive_config(self) -> Dict[str, Any]:
        """
        Get archive-specific configuration.

        Returns:
            Dictionary containing archive configuration
        """
        return self.get('archive', {})

    def get_archive_base_path(self) -> str:
        """
        Get the archive base path.

        Returns:
            Archive base path string
        """
        return self.get('archive.base_path', "")

    def get_archive_timeout(self) -> int:
        """
        Get the archive operation timeout.

        Returns:
            Timeout in seconds
        """
        return self.get('archive.timeout', 30)

    def get_rtudata_config(self) -> Dict[str, Any]:
        """
        Get RTU data-specific configuration.

        Returns:
            Dictionary containing RTU data configuration
        """
        return self.get('rtudata', {})

    def get_rtudata_base_path(self) -> str:
        """
        Get the RTU data base path.

        Returns:
            RTU data base path string
        """
        return self.get('rtudata.base_path', "")

    def get_rtudata_timeout(self) -> int:
        """
        Get the RTU data operation timeout.

        Returns:
            Timeout in seconds
        """
        return self.get('rtudata.timeout', 30)

    def get_rtudata_default_output_path(self) -> str:
        """
        Get the default output path for RTU data.

        Returns:
            Default output path string
        """
        return self.get('rtudata.default_output_path', "D:\\Historical-Rtudata\\")

    def get_database_config(self) -> Dict[str, Any]:
        """
        Get the database configuration section.

        Returns:
            Database configuration dictionary
        """
        return self.get('database', {})

    def get_database_type(self) -> str:
        """
        Get the database type.

        Returns:
            Database type string ('sqlite' or 'sql_server')
        """
        return self.get('database.type', 'sqlite')

    def get_sqlite_path(self) -> str:
        """
        Get the SQLite database path.

        Returns:
            SQLite database path string
        """
        return self.get('database.sqlite_path', r"C:\Temp\OneSource\local_onesource.db")

    def get_sql_server_config(self) -> Dict[str, Any]:
        """
        Get SQL Server configuration.

        Returns:
            Dictionary with SQL Server connection settings
        """
        return {
            'server': self.get('database.sql_server', 'PRODDWAGL2'),
            'database': self.get('database.sql_database', 'ONESOURCEDATAMART'),
            'driver': self.get('database.sql_driver', 'SQL Server'),
            'echo': self.get('database.sql_echo', False)
        }

    def get_app_config(self) -> Dict[str, Any]:
        """
        Get the app configuration section.

        Returns:
            App configuration dictionary
        """
        return self.get('app', {})

    def get_app_secret_key(self) -> str:
        """
        Get the app secret key.

        Returns:
            Secret key string for Flask session security
        """
        return self.get('app.secret_key', 'dev-secret-key-change-in-production')

    def get_app_debug(self) -> bool:
        """
        Get the app debug setting.

        Returns:
            Debug mode boolean
        """
        return self.get('app.debug', True)

    def get_app_port(self) -> int:
        """
        Get the app port.

        Returns:
            Port number for the web server
        """
        return self.get('app.port', 8050)

    def get_oracle_config(self) -> Dict[str, Any]:
        """
        Get Oracle database configuration.

        Returns:
            Dictionary containing Oracle configuration
        """
        return self.get('oracle', {})

    def get_oracle_connection_string(self) -> str:
        """
        Get the Oracle database connection string based on domain.
        Uses CNPL connection string if domain is CNPL, otherwise uses ICS.

        Returns:
            Oracle connection string
        """
        import os

        # Get the user domain name (equivalent to Environment.UserDomainName in C#)
        domain = os.environ.get('USERDOMAIN', '').upper()

        # Select connection string based on domain
        connection_string_name = "CMT_CNPL" if domain == "CNPL" else "CMT_ICS"

        # Get the appropriate connection string
        connection_strings = self.get('oracle.connection_strings', {})
        return connection_strings.get(connection_string_name, "")

    def get_oracle_connection_string_name(self) -> str:
        """
        Get the Oracle connection string name based on domain.

        Returns:
            Connection string name (CMT_CNPL or CMT_ICS)
        """
        import os
        domain = os.environ.get('USERDOMAIN', '').upper()
        return "CMT_CNPL" if domain == "CNPL" else "CMT_ICS"

    def get_oracle_timeout(self) -> int:
        """
        Get the Oracle operation timeout.

        Returns:
            Timeout in seconds
        """
        return self.get('oracle.timeout', 30)

    def get_fluid_properties_config(self) -> Dict[str, Any]:
        """
        Get fluid properties specific configuration.

        Returns:
            Dictionary containing fluid properties configuration
        """
        return self.get('fluid_properties', {})

    def get_fluid_properties_test_ids(self) -> Dict[str, Any]:
        """
        Get fluid properties test IDs configuration.

        Returns:
            Dictionary containing test IDs for each property type
        """
        return self.get('fluid_properties.test_ids', {})

    def get_fluid_properties_units(self) -> Dict[str, Any]:
        """
        Get fluid properties units configuration.

        Returns:
            Dictionary containing units for each property type
        """
        return self.get('fluid_properties.units', {})

    def get_pymbsd_config(self) -> Dict[str, Any]:
        """
        Get PyMBSd service configuration.

        Returns:
            Dictionary containing PyMBSd configuration
        """
        return self.get('pymbsd', {})

    def get_pymbsd_packages_path(self) -> str:
        """
        Get PyMBSd packages UNC path.

        Returns:
            UNC path for PyMBSd service packages
        """
        return self.get('pymbsd.packages_path', '')

    def get_pymbsd_service_installation_path(self) -> str:
        """
        Get PyMBSd service installation path.

        Returns:
            Local path where PyMBSd services should be installed
        """
        return self.get('pymbsd.service_installation_path', '')

    def get_pymbsd_timeout(self) -> int:
        """
        Get PyMBSd operation timeout.

        Returns:
            Timeout in seconds for PyMBSd operations
        """
        return self.get('pymbsd.timeout', 30)

    def get_all_config(self) -> Dict[str, Any]:
        """
        Get the entire configuration dictionary.

        Returns:
            Complete configuration dictionary
        """
        with self._lock:
            return self._config.copy()

    def save_config(self, config: Dict[str, Any] = None):
        """
        Save configuration to file.

        Args:
            config: Configuration dictionary to save. If None, saves current config.
        """
        try:
            with self._lock:
                config_to_save = config if config is not None else self._config

                # Ensure directory exists
                self.config_file_path.parent.mkdir(parents=True, exist_ok=True)

                with open(self.config_file_path, 'w', encoding='utf-8') as f:
                    json.dump(config_to_save, f, indent=2, ensure_ascii=False)

                logger.info(f"Configuration saved to {self.config_file_path}")

        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            raise


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """
    Get the global configuration manager instance.

    Returns:
        Global ConfigManager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def initialize_config_manager(config_file_path: str = None) -> ConfigManager:
    """
    Initialize the global configuration manager with a specific config file.

    Args:
        config_file_path: Path to the configuration file

    Returns:
        Initialized ConfigManager instance
    """
    global _config_manager
    _config_manager = ConfigManager(config_file_path)
    return _config_manager


def shutdown_config_manager():
    """Shutdown the global configuration manager."""
    global _config_manager
    _config_manager = None
