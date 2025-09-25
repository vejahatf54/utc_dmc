"""
Licensing Service for WUTC Application

This service handles license validation, generation, and management.
Supports both development and production environments.
"""

import hashlib
import json
import os
import sys
import socket
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
import logging
from dataclasses import dataclass
from enum import Enum

try:
    from cryptography.fernet import Fernet
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

from services.config_manager import get_config_manager

logger = logging.getLogger(__name__)


class LicenseType(Enum):
    """Types of licenses supported"""
    TRIAL = "trial"
    STANDARD = "standard"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class LicenseStatus(Enum):
    """License validation status"""
    VALID = "valid"
    EXPIRED = "expired"
    INVALID = "invalid"
    NOT_FOUND = "not_found"
    CORRUPTED = "corrupted"


@dataclass
class LicenseInfo:
    """License information structure"""
    license_type: LicenseType
    status: LicenseStatus
    expires_at: Optional[datetime]
    issued_at: datetime
    company_name: str
    licensed_to: str
    max_users: int
    features: Dict[str, bool]
    license_key: str
    days_remaining: Optional[int] = None
    is_trial: bool = False


class LicenseService:
    """Service for handling application licensing"""
    
    def __init__(self):
        self.license_file = self._get_license_file_path()
        self._secret_key = self._get_secret_key()
        self._current_license: Optional[LicenseInfo] = None
        
    def _get_license_file_path(self) -> Path:
        """Get the path to the license file"""
        # Check if running as PyInstaller/Nuitka bundle
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller
                app_dir = Path(sys.executable).parent
            else:
                # Nuitka or other
                app_dir = Path(sys.executable).parent
        else:
            # Running as script
            app_dir = Path(__file__).parent.parent
            
        # Look in license folder next to executable
        license_dir = app_dir / "license"
        
        # Look for .lic files in license folder first
        if license_dir.exists():
            lic_files = list(license_dir.glob("*.lic"))
            if lic_files:
                return lic_files[0]  # Use the first .lic file found
        
        # Fallback: look in root directory for .lic files
        lic_files = list(app_dir.glob("*.lic"))
        if lic_files:
            return lic_files[0]  # Use the first .lic file found
        
        # Final fallback
        return license_dir / "license.key" if license_dir.exists() else app_dir / "license.key"
    
    def _get_secret_key(self) -> str:
        """Get the secret key for license validation"""
        # In production, this should be more secure
        # For now, use a combination of application-specific data
        app_identifier = "WUTC_LICENSE_KEY_2024"
        machine_id = self._get_machine_identifier()
        return hashlib.sha256(f"{app_identifier}_{machine_id}".encode()).hexdigest()[:32]
    
    def _get_license_encryption_key(self) -> bytes:
        """Get the encryption key for license decryption from config"""
        try:
            # Use the secret key from config.json
            config_manager = get_config_manager()
            config_secret = config_manager.get_app_secret_key()
            
            # Create a deterministic key from the config secret
            key_material = f"WUTC_LICENSE_ENCRYPTION_{config_secret}".encode()
            key_hash = hashlib.sha256(key_material).digest()
            
            # Fernet requires a 32-byte base64-encoded key
            return base64.urlsafe_b64encode(key_hash)
        except Exception as e:
            logger.error(f"Error generating license encryption key: {e}")
            raise
    
    def _get_machine_identifier(self) -> str:
        """Get a machine-specific identifier (server name)"""
        try:
            import socket
            return socket.gethostname()
        except Exception:
            # Fallback to a default value
            return "unknown_server"
    
    def _generate_license_hash(self, license_data: Dict[str, Any]) -> str:
        """Generate a hash for license validation"""
        # Create a string from key license data
        hash_data = f"{license_data.get('license_key', '')}"
        hash_data += f"{license_data.get('company_name', '')}"
        hash_data += f"{license_data.get('licensed_to', '')}"
        hash_data += f"{license_data.get('expires_at', '')}"
        hash_data += f"{license_data.get('license_type', '')}"
        hash_data += self._secret_key
        
        return hashlib.sha256(hash_data.encode()).hexdigest()
    
    def _validate_license_hash(self, license_data: Dict[str, Any]) -> bool:
        """Validate the license hash"""
        stored_hash = license_data.get('hash', '')
        calculated_hash = self._generate_license_hash(license_data)
        return stored_hash == calculated_hash
    
    def _load_new_format_license(self, content: str) -> Optional[LicenseInfo]:
        """Load new format license with server-based validation"""
        try:
            if not CRYPTOGRAPHY_AVAILABLE:
                logger.error("Cryptography package not available for license validation")
                return None
            
            # Extract encrypted part (everything after the header)
            lines = content.split('\n')
            encrypted_start = -1
            
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith('#') and '=' not in line[:30]:
                    encrypted_start = i
                    break
            
            if encrypted_start == -1:
                logger.error("Could not find encrypted license data")
                return None
            
            encrypted_license = '\n'.join(lines[encrypted_start:]).strip()
            
            # Get encryption key from config
            try:
                key = self._get_license_encryption_key()
                cipher = Fernet(key)
            except Exception as e:
                logger.error(f"Failed to initialize license decryption: {e}")
                return None
            
            # Decrypt license data
            decoded = base64.b64decode(encrypted_license.encode())
            decrypted = cipher.decrypt(decoded)
            license_data = json.loads(decrypted.decode())
            
            # Validate server name
            license_server = license_data.get('server_name', '')
            current_server = socket.gethostname()
            
            if license_server.lower() != current_server.lower():
                logger.error(f"License server mismatch: licensed for '{license_server}', running on '{current_server}'")
                return None
            
            # Parse dates
            issued_at = datetime.fromisoformat(license_data['issue_date'])
            expires_at = datetime.fromisoformat(license_data['expiry_date'])
            
            # Determine status and days remaining
            now = datetime.now()
            if now > expires_at:
                status = LicenseStatus.EXPIRED
                days_remaining = 0
            else:
                status = LicenseStatus.VALID
                days_remaining = (expires_at - now).days
            
            # Map to license type based on duration
            days_total = license_data.get('days', 0)
            if days_total <= 30:
                license_type = LicenseType.TRIAL
            elif days_total <= 365:
                license_type = LicenseType.STANDARD
            else:
                license_type = LicenseType.PROFESSIONAL
            
            # Set features based on license type
            features = {
                "export_data": True,
                "advanced_reporting": license_type in [LicenseType.PROFESSIONAL, LicenseType.ENTERPRISE],
                "multi_user": license_type in [LicenseType.PROFESSIONAL, LicenseType.ENTERPRISE],
                "api_access": license_type == LicenseType.ENTERPRISE,
                "priority_support": license_type in [LicenseType.PROFESSIONAL, LicenseType.ENTERPRISE]
            }
            
            return LicenseInfo(
                license_type=license_type,
                status=status,
                expires_at=expires_at,
                issued_at=issued_at,
                company_name=license_data.get('additional_info', 'Licensed User'),
                licensed_to=license_server,
                max_users=10 if license_type in [LicenseType.PROFESSIONAL, LicenseType.ENTERPRISE] else 1,
                features=features,
                license_key=encrypted_license[:50] + "...",  # Show partial key
                days_remaining=days_remaining,
                is_trial=license_type == LicenseType.TRIAL
            )
            
        except Exception as e:
            logger.error(f"Error loading new format license: {e}")
            return None
    
    def load_license(self) -> Optional[LicenseInfo]:
        """Load and validate the license file"""
        try:
            if not self.license_file.exists():
                logger.error(f"License file not found at {self.license_file}")
                return None
            
            with open(self.license_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # Check if this is a new format license (starts with # comments)
            if content.startswith('#'):
                return self._load_new_format_license(content)
            
            # Try loading as JSON (old format)
            try:
                license_data = json.loads(content)
                
                # Validate license hash
                if not self._validate_license_hash(license_data):
                    logger.error("License file is corrupted or tampered with")
                    return None
            except json.JSONDecodeError:
                logger.error("License file format is not recognized")
                return None
            
            # Parse license data
            license_type = LicenseType(license_data.get('license_type', 'trial'))
            issued_at = datetime.fromisoformat(license_data.get('issued_at', datetime.now().isoformat()))
            expires_at = None
            if license_data.get('expires_at'):
                expires_at = datetime.fromisoformat(license_data['expires_at'])
            
            # Determine status
            status = LicenseStatus.VALID
            days_remaining = None
            
            if expires_at:
                if datetime.now() > expires_at:
                    status = LicenseStatus.EXPIRED
                    days_remaining = 0
                else:
                    days_remaining = (expires_at - datetime.now()).days
            
            license_info = LicenseInfo(
                license_type=license_type,
                status=status,
                expires_at=expires_at,
                issued_at=issued_at,
                company_name=license_data.get('company_name', ''),
                licensed_to=license_data.get('licensed_to', ''),
                max_users=license_data.get('max_users', 1),
                features=license_data.get('features', {}),
                license_key=license_data.get('license_key', ''),
                days_remaining=days_remaining,
                is_trial=license_type == LicenseType.TRIAL
            )
            
            self._current_license = license_info
            logger.info(f"License loaded successfully: {license_type.value} ({status.value})")
            return license_info
            
        except Exception as e:
            logger.error(f"Error loading license: {e}")
            return None
    
    def save_license(self, license_data: Dict[str, Any]) -> bool:
        """Save a license file"""
        try:
            # Add hash to license data
            license_data['hash'] = self._generate_license_hash(license_data)
            
            # Ensure directory exists
            self.license_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.license_file, 'w', encoding='utf-8') as f:
                json.dump(license_data, f, indent=2, default=str)
            
            logger.info(f"License saved to {self.license_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving license: {e}")
            return False
    
    def validate_license_key(self, license_key: str) -> Tuple[bool, Dict[str, Any]]:
        """Validate a license key and return license data"""
        # This is a simplified validation - in production, this would
        # typically involve server-side validation or cryptographic verification
        
        try:
            # For demo purposes, support some predefined license keys
            if license_key.startswith("WUTC-STANDARD-"):
                return True, {
                    "license_key": license_key,
                    "license_type": "standard",
                    "company_name": "Licensed Company",
                    "licensed_to": "Licensed User",
                    "max_users": 5,
                    "issued_at": datetime.now().isoformat(),
                    "expires_at": (datetime.now() + timedelta(days=365)).isoformat(),
                    "features": {
                        "basic_functionality": True,
                        "advanced_reports": True,
                        "api_access": True,
                        "multi_user": True
                    }
                }
            elif license_key.startswith("WUTC-PRO-"):
                return True, {
                    "license_key": license_key,
                    "license_type": "professional",
                    "company_name": "Licensed Company",
                    "licensed_to": "Licensed User",
                    "max_users": 10,
                    "issued_at": datetime.now().isoformat(),
                    "expires_at": (datetime.now() + timedelta(days=365)).isoformat(),
                    "features": {
                        "basic_functionality": True,
                        "advanced_reports": True,
                        "api_access": True,
                        "multi_user": True,
                        "premium_support": True
                    }
                }
            elif license_key == "WUTC-ENTERPRISE-UNLIMITED":
                return True, {
                    "license_key": license_key,
                    "license_type": "enterprise",
                    "company_name": "Licensed Company",
                    "licensed_to": "Licensed User",
                    "max_users": 999,
                    "issued_at": datetime.now().isoformat(),
                    "expires_at": None,  # No expiration
                    "features": {
                        "basic_functionality": True,
                        "advanced_reports": True,
                        "api_access": True,
                        "multi_user": True,
                        "premium_support": True,
                        "custom_features": True
                    }
                }
            else:
                return False, {}
                
        except Exception as e:
            logger.error(f"Error validating license key: {e}")
            return False, {}
    
    def get_current_license(self) -> Optional[LicenseInfo]:
        """Get the current license information"""
        if not self._current_license:
            self._current_license = self.load_license()
        return self._current_license
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a specific feature is enabled in the current license"""
        license_info = self.get_current_license()
        if not license_info or license_info.status != LicenseStatus.VALID:
            return False
        return license_info.features.get(feature_name, False)
    
    def get_license_summary(self) -> Dict[str, Any]:
        """Get a summary of the current license status"""
        license_info = self.get_current_license()
        if not license_info:
            return {"status": "error", "message": "Unable to load license"}
        
        return {
            "status": license_info.status.value,
            "type": license_info.license_type.value,
            "company": license_info.company_name,
            "licensed_to": license_info.licensed_to,
            "expires_at": license_info.expires_at.isoformat() if license_info.expires_at else None,
            "days_remaining": license_info.days_remaining,
            "is_trial": license_info.is_trial,
            "features": license_info.features
        }


# Global license service instance
license_service = LicenseService()