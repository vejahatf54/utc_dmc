"""
Configuration Manager for DMC application.
Provides centralized configuration loading and hot reload capabilities.
"""

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)


class ConfigFileHandler(FileSystemEventHandler):
    """File system event handler for configuration file changes."""
    
    def __init__(self, config_manager: 'ConfigManager'):
        """Initialize the handler with a reference to the config manager."""
        self.config_manager = config_manager
        
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory and event.src_path == str(self.config_manager.config_file_path):
            logger.info(f"Configuration file changed: {event.src_path}")
            # Add a small delay to ensure file write is complete
            time.sleep(0.1)
            self.config_manager._reload_config()


class ConfigManager:
    """
    Centralized configuration manager with hot reload capabilities.
    Manages loading, caching, and automatic reloading of configuration settings.
    """
    
    def __init__(self, config_file_path: str = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_file_path: Path to the configuration file. Defaults to config.json in app root.
        """
        if config_file_path is None:
            # Default to config.json in the application root directory
            app_root = Path(__file__).parent.parent
            config_file_path = app_root / "config.json"
        
        self.config_file_path = Path(config_file_path)
        self._config: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._observers: Observer = None
        self._reload_callbacks: list[Callable] = []
        self._last_modified = None
        
        # Load initial configuration
        self._load_config()
        
        # Start file watcher for hot reload
        self._start_file_watcher()
    
    def _load_config(self) -> bool:
        """
        Load configuration from the JSON file.
        
        Returns:
            True if configuration was loaded successfully, False otherwise.
        """
        try:
            with self._lock:
                if not self.config_file_path.exists():
                    logger.warning(f"Configuration file not found: {self.config_file_path}")
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
                
                logger.info(f"Configuration loaded successfully from {self.config_file_path}")
                return True
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            return False
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return False
    
    def _reload_config(self):
        """Reload configuration and notify callbacks."""
        try:
            old_config = self._config.copy()
            
            if self._load_config():
                # Check if configuration actually changed
                if old_config != self._config:
                    logger.info("Configuration reloaded due to file changes")
                    self._notify_reload_callbacks()
                else:
                    logger.debug("Configuration file changed but content is the same")
            else:
                logger.error("Failed to reload configuration")
                
        except Exception as e:
            logger.error(f"Error during configuration reload: {e}")
    
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
    
    def _start_file_watcher(self):
        """Start file system watcher for configuration file changes."""
        try:
            if not self.config_file_path.exists():
                logger.warning("Configuration file does not exist, file watcher not started")
                return
                
            self._observer = Observer()
            event_handler = ConfigFileHandler(self)
            
            # Watch the directory containing the config file
            watch_directory = self.config_file_path.parent
            self._observer.schedule(event_handler, str(watch_directory), recursive=False)
            self._observer.start()
            
            logger.info(f"File watcher started for configuration directory: {watch_directory}")
            
        except Exception as e:
            logger.error(f"Failed to start file watcher: {e}")
    
    def _stop_file_watcher(self):
        """Stop the file system watcher."""
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join()
            logger.info("File watcher stopped")
    
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
                logger.error(f"Error getting configuration key '{key_path}': {e}")
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
    
    def add_reload_callback(self, callback: Callable[[], None]):
        """
        Add a callback function to be called when configuration is reloaded.
        
        Args:
            callback: Function to call when configuration changes
        """
        if callback not in self._reload_callbacks:
            self._reload_callbacks.append(callback)
            logger.debug(f"Added reload callback: {callback.__name__}")
    
    def remove_reload_callback(self, callback: Callable[[], None]):
        """
        Remove a reload callback.
        
        Args:
            callback: Function to remove from callbacks
        """
        if callback in self._reload_callbacks:
            self._reload_callbacks.remove(callback)
            logger.debug(f"Removed reload callback: {callback.__name__}")
    
    def _notify_reload_callbacks(self):
        """Notify all registered callbacks about configuration reload."""
        for callback in self._reload_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in reload callback {callback.__name__}: {e}")
    
    def reload(self):
        """Manually trigger configuration reload."""
        self._reload_config()
    
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
    
    def shutdown(self):
        """Shutdown the configuration manager and stop file watcher."""
        self._stop_file_watcher()
        self._reload_callbacks.clear()
        logger.info("Configuration manager shutdown completed")


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
    if _config_manager is not None:
        _config_manager.shutdown()
    
    _config_manager = ConfigManager(config_file_path)
    return _config_manager


def shutdown_config_manager():
    """Shutdown the global configuration manager."""
    global _config_manager
    if _config_manager is not None:
        _config_manager.shutdown()
        _config_manager = None
