"""
Configuration Manager for DMC application.
Provides centralized configuration loading capabilities.
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

        # Load initial configuration
        self._load_config()

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
                self._config = self._merge_configs(default_config, new_config)
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
