import os
import zipfile
import xml.etree.ElementTree as ET
import subprocess
import psutil
import threading
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from services.config_manager import get_config_manager

logger = logging.getLogger(__name__)


class PyMBSdService:
    """Service class for managing PyMBSd Windows services"""

    @staticmethod
    def fetch_service_packages() -> List[Dict[str, Any]]:
        """
        Fetch list of available service packages from UNC path
        Returns list of service information dictionaries
        """
        try:
            config_manager = get_config_manager()
            packages_path = config_manager.get_pymbsd_packages_path()
            if not packages_path:
                raise Exception(
                    "PyMBSd packages path is not configured in config.json")

            if not os.path.exists(packages_path):
                raise Exception(
                    f"PyMBSd packages path is not accessible: {packages_path}\n\nPlease ensure:\n1. The network path is accessible\n2. You have proper permissions\n3. The path exists on the server")

            services = []
            zip_files = [f for f in os.listdir(
                packages_path) if f.endswith('.zip')]

            if not zip_files:
                logger.warning(f"No zip files found in {packages_path}")
                return []

            for zip_file in zip_files:
                zip_path = os.path.join(packages_path, zip_file)
                package_name = os.path.splitext(zip_file)[0]

                try:
                    service_info = PyMBSdService._extract_service_info(
                        zip_path, package_name)
                    if service_info:
                        # Check current service status
                        service_info["status"] = PyMBSdService._get_service_status(
                            service_info["service_name"])
                        services.append(service_info)
                except Exception as e:
                    logger.error(f"Error processing package {zip_file}: {e}")
                    # Add package with error status
                    services.append({
                        "package_name": package_name,
                        "service_name": package_name,
                        "status": "error",
                        "zip_path": zip_path
                    })

            return services

        except Exception as e:
            logger.error(f"Error fetching service packages: {e}")
            raise

    @staticmethod
    def fetch_service_packages_fast() -> List[Dict[str, Any]]:
        """
        Fast fetch of service packages without status checking (UI optimization)
        Status will be loaded asynchronously via interval updates
        """
        try:
            config_manager = get_config_manager()
            packages_path = config_manager.get_pymbsd_packages_path()
            if not packages_path:
                raise Exception(
                    "PyMBSd packages path is not configured in config.json")

            if not os.path.exists(packages_path):
                raise Exception(
                    f"PyMBSd packages path is not accessible: {packages_path}\n\nPlease ensure:\n1. The network path is accessible\n2. You have proper permissions\n3. The path exists on the server")

            services = []
            zip_files = [f for f in os.listdir(
                packages_path) if f.endswith('.zip')]

            if not zip_files:
                logger.warning(f"No zip files found in {packages_path}")
                return []

            for zip_file in zip_files:
                zip_path = os.path.join(packages_path, zip_file)
                package_name = os.path.splitext(zip_file)[0]

                try:
                    service_info = PyMBSdService._extract_service_info(
                        zip_path, package_name)
                    if service_info:
                        # Don't check status initially for faster load
                        service_info["status"] = "loading"
                        services.append(service_info)
                except Exception as e:
                    logger.error(f"Error processing package {zip_file}: {e}")
                    # Add package with error status
                    services.append({
                        "package_name": package_name,
                        "service_name": package_name,
                        "status": "error",
                        "zip_path": zip_path
                    })

            return services

        except Exception as e:
            logger.error(f"Error fetching service packages: {e}")
            raise

    @staticmethod
    def _extract_service_info(zip_path: str, package_name: str) -> Optional[Dict[str, Any]]:
        """Extract service information from zip package"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                # Look for XML configuration file
                xml_files = [f for f in zip_file.namelist()
                             if f.endswith('.xml') and package_name in f]

                if xml_files:
                    xml_content = zip_file.read(xml_files[0])
                    root = ET.fromstring(xml_content)

                    # Extract service name from XML
                    name_element = root.find('.//name')
                    if name_element is not None:
                        service_name = name_element.text

                        return {
                            "package_name": package_name,
                            "service_name": service_name,
                            "zip_path": zip_path,
                            "xml_file": xml_files[0]
                        }

            return None

        except Exception as e:
            logger.error(f"Error extracting service info from {zip_path}: {e}")
            return None

    @staticmethod
    def _get_service_status(service_name: str) -> str:
        """Get the current status of a Windows service"""
        try:
            # Check if service exists and get status
            result = subprocess.run(
                ["sc", "query", service_name],
                capture_output=True,
                text=True,
                shell=True
            )

            if result.returncode != 0:
                return "not_found"

            output = result.stdout
            if "RUNNING" in output:
                return "running"
            elif "STOPPED" in output:
                return "stopped"
            elif "START_PENDING" in output:
                return "starting"
            elif "STOP_PENDING" in output:
                return "stopping"
            else:
                return "unknown"

        except Exception as e:
            logger.error(
                f"Error getting service status for {service_name}: {e}")
            return "error"

    @staticmethod
    def update_service_statuses(service_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Update status for all services in the list"""
        updated_services = []

        for service in service_data:
            updated_service = service.copy()
            updated_service["status"] = PyMBSdService._get_service_status(
                service["service_name"])
            updated_services.append(updated_service)

        return updated_services

    @staticmethod
    def install_services(services: List[Dict[str, Any]], start_after_install: bool = True,
                         auto_mode: bool = True) -> Dict[str, Any]:
        """Install selected services"""
        try:
            config_manager = get_config_manager()
            installation_path = config_manager.get_pymbsd_service_installation_path()

            # Ensure installation directory exists
            os.makedirs(installation_path, exist_ok=True)

            installed_services = []
            errors = []

            for service in services:
                try:
                    # Uninstall existing service first
                    PyMBSdService._uninstall_service(service["service_name"])

                    # Remove existing directory
                    service_dir = os.path.join(
                        installation_path, service["package_name"])
                    if os.path.exists(service_dir):
                        PyMBSdService._force_delete_directory(service_dir)

                    # Extract package
                    with zipfile.ZipFile(service["zip_path"], 'r') as zip_file:
                        zip_file.extractall(installation_path)

                    # Find service executable and config
                    service_files = PyMBSdService._find_service_files(
                        service_dir)
                    if not service_files:
                        raise Exception(
                            "Service package missing necessary files")

                    # Install service
                    PyMBSdService._install_service(
                        service_dir, service_files["exe"])

                    # Set auto mode if requested
                    if auto_mode:
                        PyMBSdService._set_service_auto_mode(
                            service_dir, service_files["xml"])

                    # Start service if requested
                    if start_after_install:
                        PyMBSdService._start_service(service["service_name"])

                    installed_services.append(service["service_name"])

                except Exception as e:
                    error_msg = f"Error installing {service['service_name']}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            if errors:
                return {
                    "success": False,
                    "message": f"Installed {len(installed_services)} services with {len(errors)} errors: {'; '.join(errors)}"
                }
            else:
                return {
                    "success": True,
                    "message": f"Successfully installed {len(installed_services)} services"
                }

        except Exception as e:
            logger.error(f"Error in install_services: {e}")
            return {"success": False, "message": f"Installation failed: {str(e)}"}

    @staticmethod
    def start_services(services: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Start selected services"""
        try:
            started_services = []
            errors = []

            for service in services:
                try:
                    PyMBSdService._start_service(service["service_name"])
                    started_services.append(service["service_name"])
                except Exception as e:
                    error_msg = f"Error starting {service['service_name']}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            if errors:
                return {
                    "success": False,
                    "message": f"Started {len(started_services)} services with {len(errors)} errors: {'; '.join(errors)}"
                }
            else:
                return {
                    "success": True,
                    "message": f"Successfully started {len(started_services)} services"
                }

        except Exception as e:
            logger.error(f"Error in start_services: {e}")
            return {"success": False, "message": f"Start failed: {str(e)}"}

    @staticmethod
    def stop_services(services: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Stop selected services"""
        try:
            stopped_services = []
            errors = []

            for service in services:
                try:
                    PyMBSdService._stop_service(service["service_name"])
                    stopped_services.append(service["service_name"])
                except Exception as e:
                    error_msg = f"Error stopping {service['service_name']}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            if errors:
                return {
                    "success": False,
                    "message": f"Stopped {len(stopped_services)} services with {len(errors)} errors: {'; '.join(errors)}"
                }
            else:
                return {
                    "success": True,
                    "message": f"Successfully stopped {len(stopped_services)} services"
                }

        except Exception as e:
            logger.error(f"Error in stop_services: {e}")
            return {"success": False, "message": f"Stop failed: {str(e)}"}

    @staticmethod
    def uninstall_services(services: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Uninstall selected services"""
        try:
            config_manager = get_config_manager()
            installation_path = config_manager.get_pymbsd_service_installation_path()

            uninstalled_services = []
            errors = []

            for service in services:
                try:
                    # Stop service first
                    PyMBSdService._stop_service(service["service_name"])

                    # Uninstall service
                    PyMBSdService._uninstall_service(service["service_name"])

                    # Remove directory
                    service_dir = os.path.join(
                        installation_path, service["package_name"])
                    if os.path.exists(service_dir):
                        PyMBSdService._force_delete_directory(service_dir)

                    uninstalled_services.append(service["service_name"])

                except Exception as e:
                    error_msg = f"Error uninstalling {service['service_name']}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            if errors:
                return {
                    "success": False,
                    "message": f"Uninstalled {len(uninstalled_services)} services with {len(errors)} errors: {'; '.join(errors)}"
                }
            else:
                return {
                    "success": True,
                    "message": f"Successfully uninstalled {len(uninstalled_services)} services"
                }

        except Exception as e:
            logger.error(f"Error in uninstall_services: {e}")
            return {"success": False, "message": f"Uninstall failed: {str(e)}"}

    @staticmethod
    def _find_service_files(service_dir: str) -> Optional[Dict[str, str]]:
        """Find service executable and XML configuration files"""
        try:
            exe_files = list(Path(service_dir).glob("pymbsd_*.exe"))
            xml_files = list(Path(service_dir).glob("pymbsd_*.xml"))

            if exe_files and xml_files:
                return {
                    "exe": str(exe_files[0]),
                    "xml": str(xml_files[0])
                }
            return None

        except Exception as e:
            logger.error(f"Error finding service files in {service_dir}: {e}")
            return None

    @staticmethod
    def _install_service(service_dir: str, exe_path: str):
        """Install a Windows service using the executable"""
        try:
            result = subprocess.run(
                [exe_path, "install"],
                cwd=service_dir,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                raise Exception(
                    f"Service installation failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            raise Exception("Service installation timed out")
        except Exception as e:
            raise Exception(f"Failed to install service: {str(e)}")

    @staticmethod
    def _uninstall_service(service_name: str):
        """Uninstall a Windows service"""
        try:
            # First check if service exists
            result = subprocess.run(
                ["sc", "query", service_name],
                capture_output=True,
                text=True,
                shell=True
            )

            if result.returncode != 0:
                return  # Service doesn't exist

            # Delete the service
            result = subprocess.run(
                ["sc", "delete", service_name],
                capture_output=True,
                text=True,
                shell=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.warning(
                    f"Failed to delete service {service_name}: {result.stderr}")

        except Exception as e:
            logger.error(f"Error uninstalling service {service_name}: {e}")

    @staticmethod
    def _start_service(service_name: str):
        """Start a Windows service"""
        try:
            # Check if service exists
            if PyMBSdService._get_service_status(service_name) == "not_found":
                raise Exception(f"Service {service_name} not found")

            # Check if already running
            if PyMBSdService._get_service_status(service_name) == "running":
                return

            result = subprocess.run(
                ["sc", "start", service_name],
                capture_output=True,
                text=True,
                shell=True,
                timeout=30
            )

            if result.returncode != 0:
                raise Exception(f"Failed to start service: {result.stderr}")

            # Wait for service to start
            max_wait = 20
            for _ in range(max_wait):
                if PyMBSdService._get_service_status(service_name) == "running":
                    break
                time.sleep(1)

        except Exception as e:
            raise Exception(
                f"Failed to start service {service_name}: {str(e)}")

    @staticmethod
    def _stop_service(service_name: str):
        """Stop a Windows service"""
        try:
            # Check if service exists
            if PyMBSdService._get_service_status(service_name) == "not_found":
                return

            # Check if already stopped
            if PyMBSdService._get_service_status(service_name) == "stopped":
                return

            result = subprocess.run(
                ["sc", "stop", service_name],
                capture_output=True,
                text=True,
                shell=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.warning(
                    f"Failed to stop service {service_name}: {result.stderr}")

            # Wait for service to stop
            max_wait = 20
            for _ in range(max_wait):
                if PyMBSdService._get_service_status(service_name) in ["stopped", "not_found"]:
                    break
                time.sleep(1)

        except Exception as e:
            logger.error(f"Error stopping service {service_name}: {e}")

    @staticmethod
    def _set_service_auto_mode(service_dir: str, xml_path: str):
        """Set service start mode to automatic by modifying XML config"""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Remove existing startmode if present
            for elem in root.findall('startmode'):
                root.remove(elem)

            # Add automatic start mode
            startmode = ET.SubElement(root, 'startmode')
            startmode.text = 'Automatic'

            tree.write(xml_path, encoding='utf-8', xml_declaration=True)

        except Exception as e:
            logger.error(f"Error setting service auto mode: {e}")

    @staticmethod
    def _force_delete_directory(directory_path: str):
        """Force delete a directory and all its contents"""
        try:
            def handle_remove_readonly(func, path, exc):
                os.chmod(path, 0o777)
                func(path)

            if os.path.exists(directory_path):
                # Kill any processes that might be using files in the directory
                for proc in psutil.process_iter(['pid', 'name', 'exe']):
                    try:
                        if proc.info['exe'] and directory_path.lower() in proc.info['exe'].lower():
                            proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                # Wait a bit for processes to terminate
                time.sleep(1)

                # Force remove directory
                import shutil
                shutil.rmtree(directory_path, onerror=handle_remove_readonly)

        except Exception as e:
            logger.error(
                f"Error force deleting directory {directory_path}: {e}")
            raise
