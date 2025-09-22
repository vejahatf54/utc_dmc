"""
Secure Configuration Manager for WUTC application.
Provides encryption/decryption of sensitive configuration values using Windows DPAPI.
Similar to C# DPAPI functionality - encrypted values are tied to the local machine.
"""

import json
import base64
import os
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import secrets
from logging_config import get_logger

logger = get_logger(__name__)


class SecureConfigManager:
    """
    Secure configuration manager that encrypts/decrypts sensitive configuration values.
    Uses Windows DPAPI-like functionality by deriving encryption keys from machine-specific data.
    """

    def __init__(self):
        """Initialize the secure configuration manager."""
        self._machine_key = self._get_machine_key()
        self._encrypted_prefix = "ENCRYPTED:"

    def _get_machine_key(self) -> bytes:
        """
        Generate a machine-specific key (not user-specific).
        This key is derived from machine-only information making configs non-transferable
        but allows any user on the same machine to use the application (important for Windows services).

        Returns:
            Machine-specific encryption key
        """
        try:
            # Get machine-specific identifiers only (not user-specific)
            machine_id = os.environ.get('COMPUTERNAME', 'unknown')

            # Get domain name (machine-specific in corporate environments)
            machine_domain = os.environ.get(
                'USERDNSDOMAIN', os.environ.get('USERDOMAIN', 'unknown'))

            # Get MAC address for hardware-specific binding
            mac_address = self._get_mac_address()

            # Get additional machine-specific information for stronger key
            try:
                import platform
                machine_info = {
                    'machine': platform.machine(),
                    'system': platform.system(),
                    'node': platform.node()
                }
                machine_details = f"{machine_info['machine']}:{machine_info['system']}:{machine_info['node']}"
            except Exception as e:
                logger.debug(f"Could not get detailed machine info: {e}")
                machine_details = "default_machine_info"

            # Create a machine-specific salt combining multiple machine identifiers
            machine_string = f"{machine_id}:{machine_domain}:{mac_address}:{machine_details}:WUTC_CONFIG_SALT"
            salt = machine_string.encode('utf-8')

            # Derive key using PBKDF2 (similar to how DPAPI works internally)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,  # 256-bit key
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )

            # Use a fixed password combined with machine info for reproducibility
            password = f"WUTC_SECURE_CONFIG_{machine_id}".encode('utf-8')
            key = kdf.derive(password)

            logger.debug(
                f"Generated machine-specific (not user-specific) key for computer: {machine_id}")
            return key

        except Exception as e:
            logger.error(f"Error generating machine key: {e}")
            # Fallback to a basic key (not recommended for production)
            return b"fallback_key_not_secure_change_me"

    def _get_mac_address(self) -> str:
        """
        Get the MAC address of the primary network interface for hardware-specific binding.

        Returns:
            MAC address as a string, or 'unknown' if not available
        """
        try:
            import uuid
            # Get the MAC address of the primary network interface
            mac = uuid.getnode()
            # Convert to standard MAC address format
            mac_str = ':'.join(
                f'{(mac >> i) & 0xFF:02x}' for i in range(0, 48, 8))
            # Log only partial for security
            logger.debug(
                f"Retrieved MAC address for machine binding: {mac_str[:8]}...")
            return mac_str
        except Exception as e:
            logger.debug(f"Could not get MAC address: {e}")
            return "unknown_mac"

    def encrypt_value(self, plaintext: str) -> str:
        """
        Encrypt a configuration value.

        Args:
            plaintext: The plaintext value to encrypt

        Returns:
            Encrypted value with prefix
        """
        try:
            if not plaintext:
                return plaintext

            # Generate a random IV for each encryption
            iv = secrets.token_bytes(16)

            # Create cipher
            cipher = Cipher(
                algorithms.AES(self._machine_key),
                modes.CBC(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()

            # Pad the plaintext to be multiple of 16 bytes (AES block size)
            plaintext_bytes = plaintext.encode('utf-8')
            padding_length = 16 - (len(plaintext_bytes) % 16)
            padded_plaintext = plaintext_bytes + \
                bytes([padding_length] * padding_length)

            # Encrypt
            ciphertext = encryptor.update(
                padded_plaintext) + encryptor.finalize()

            # Combine IV and ciphertext, then base64 encode
            encrypted_data = iv + ciphertext
            encoded_data = base64.b64encode(encrypted_data).decode('utf-8')

            return f"{self._encrypted_prefix}{encoded_data}"

        except Exception as e:
            logger.error(f"Error encrypting value: {e}")
            return plaintext  # Return original on error

    def decrypt_value(self, encrypted_value: str) -> str:
        """
        Decrypt a configuration value.

        Args:
            encrypted_value: The encrypted value to decrypt

        Returns:
            Decrypted plaintext value
        """
        try:
            if not encrypted_value or not encrypted_value.startswith(self._encrypted_prefix):
                # Not encrypted, return as-is
                return encrypted_value

            # Remove prefix and decode
            encoded_data = encrypted_value[len(self._encrypted_prefix):]
            encrypted_data = base64.b64decode(encoded_data.encode('utf-8'))

            # Extract IV and ciphertext
            iv = encrypted_data[:16]
            ciphertext = encrypted_data[16:]

            # Create cipher
            cipher = Cipher(
                algorithms.AES(self._machine_key),
                modes.CBC(iv),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()

            # Decrypt
            padded_plaintext = decryptor.update(
                ciphertext) + decryptor.finalize()

            # Remove padding
            padding_length = padded_plaintext[-1]
            if padding_length > 16:
                raise ValueError("Invalid padding")
            plaintext_bytes = padded_plaintext[:-padding_length]

            return plaintext_bytes.decode('utf-8')

        except Exception as e:
            logger.error(f"Error decrypting value: {e}")
            logger.warning(
                "This config file may have been encrypted on a different machine!")
            return encrypted_value  # Return encrypted value on error for debugging

    def encrypt_config_section(self, config_section: Dict[str, Any], sensitive_keys: list) -> Dict[str, Any]:
        """
        Encrypt sensitive keys in a configuration section.

        Args:
            config_section: Configuration section dictionary
            sensitive_keys: List of keys that should be encrypted

        Returns:
            Configuration section with sensitive values encrypted
        """
        result = config_section.copy()

        for key in sensitive_keys:
            if key in result and isinstance(result[key], str):
                result[key] = self.encrypt_value(result[key])

        return result

    def decrypt_config_section(self, config_section: Dict[str, Any], sensitive_keys: list) -> Dict[str, Any]:
        """
        Decrypt sensitive keys in a configuration section.

        Args:
            config_section: Configuration section dictionary
            sensitive_keys: List of keys that should be decrypted

        Returns:
            Configuration section with sensitive values decrypted
        """
        result = config_section.copy()

        for key in sensitive_keys:
            if key in result and isinstance(result[key], str):
                result[key] = self.decrypt_value(result[key])

        return result

    def is_encrypted(self, value: str) -> bool:
        """
        Check if a value is encrypted.

        Args:
            value: Value to check

        Returns:
            True if the value is encrypted
        """
        return isinstance(value, str) and value.startswith(self._encrypted_prefix)


def encrypt_config_file(config_file_path: str, backup: bool = True) -> bool:
    """
    Encrypt sensitive values in a configuration file.

    Args:
        config_file_path: Path to the configuration file
        backup: Whether to create a backup before encryption

    Returns:
        True if encryption was successful
    """
    try:
        config_path = Path(config_file_path)
        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_file_path}")
            return False

        # Create backup if requested
        if backup:
            backup_path = config_path.with_suffix('.backup.json')
            import shutil
            shutil.copy2(config_path, backup_path)
            logger.info(f"Created backup at: {backup_path}")

        # Load current configuration
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        secure_manager = SecureConfigManager()

        # Define which keys should be encrypted in each section
        sensitive_sections = {
            'oracle': {
                # Encrypt the connection strings themselves
                'connection_strings': ['CMT_ICS', 'CMT_CNPL']
            },
            'app': ['secret_key']  # Encrypt the app secret key
        }

        # Encrypt sensitive values
        modified = False
        for section_name, sensitive_items in sensitive_sections.items():
            if section_name in config:
                if isinstance(sensitive_items, dict):
                    # Handle nested sections like oracle.connection_strings
                    for subsection_name, keys in sensitive_items.items():
                        if subsection_name in config[section_name]:
                            for key in keys:
                                if key in config[section_name][subsection_name]:
                                    current_value = config[section_name][subsection_name][key]
                                    if not secure_manager.is_encrypted(current_value):
                                        encrypted_value = secure_manager.encrypt_value(
                                            current_value)
                                        config[section_name][subsection_name][key] = encrypted_value
                                        modified = True
                                        logger.info(
                                            f"Encrypted {section_name}.{subsection_name}.{key}")
                else:
                    # Handle direct keys like app.secret_key
                    for key in sensitive_items:
                        if key in config[section_name]:
                            current_value = config[section_name][key]
                            if not secure_manager.is_encrypted(current_value):
                                encrypted_value = secure_manager.encrypt_value(
                                    current_value)
                                config[section_name][key] = encrypted_value
                                modified = True
                                logger.info(f"Encrypted {section_name}.{key}")

        if modified:
            # Write back the encrypted configuration
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            logger.info(
                f"Successfully encrypted sensitive values in {config_file_path}")
            return True
        else:
            logger.info(
                "No sensitive values found to encrypt or all values already encrypted")
            return True

    except Exception as e:
        logger.error(f"Error encrypting configuration file: {e}")
        return False


if __name__ == "__main__":
    # CLI usage for encrypting config file
    import sys

    if len(sys.argv) < 2:
        print("Usage: python secure_config_manager.py <config_file_path>")
        sys.exit(1)

    config_file = sys.argv[1]
    success = encrypt_config_file(config_file)

    if success:
        print(f"Successfully encrypted sensitive values in {config_file}")
        print("IMPORTANT: This config file is now tied to this machine and cannot be transferred!")
    else:
        print(f"Failed to encrypt {config_file}")
        sys.exit(1)
