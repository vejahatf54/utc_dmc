#!/usr/bin/env python3
"""
Test script to verify logging configuration across all DMC components.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from logging_config import get_logger, setup_logging

# Initialize logging
setup_logging()

def test_all_services():
    """Test logging from all services"""
    print("Testing logging across all DMC services...")
    
    # Test various service imports and logging
    test_logger = get_logger('test_logging')
    test_logger.info("Starting comprehensive logging test")
    
    # Test config manager
    try:
        from services.config_manager import ConfigManager
        config_mgr = ConfigManager()
        test_logger.info("ConfigManager imported and initialized successfully")
    except Exception as e:
        test_logger.error(f"Failed to test ConfigManager: {e}")
    
    # Test replay service
    try:
        from services.replay_file_poke_service import UtcReplayFilePokeExtractorService
        replay_service = UtcReplayFilePokeExtractorService()
        test_logger.info("ReplayFilePokeService imported and initialized successfully")
    except Exception as e:
        test_logger.error(f"Failed to test ReplayFilePokeService: {e}")
    
    # Test page components
    try:
        import components.replay_file_poke_page
        test_logger.info("Replay file poke page imported successfully")
    except Exception as e:
        test_logger.error(f"Failed to import replay file poke page: {e}")
    
    try:
        import components.fetch_archive_page
        test_logger.info("Fetch archive page imported successfully")
    except Exception as e:
        test_logger.error(f"Failed to import fetch archive page: {e}")
    
    # Test other services
    services_to_test = [
        'services.date_range_service',
        'services.elevation_data_service', 
        'services.exceptions',
        'services.fetch_archive_service',
        'services.fetch_rtu_data_service',
        'services.onesource_service',
        'services.pipe_analysis_service',
        'services.replace_text_service',
        'services.review_to_csv_service',
        'services.rtu_to_csv_service'
    ]
    
    for service_name in services_to_test:
        try:
            __import__(service_name)
            test_logger.info(f"Service {service_name} imported successfully")
        except Exception as e:
            test_logger.error(f"Failed to import {service_name}: {e}")
    
    test_logger.info("Comprehensive logging test completed")
    print("Test completed - check logs/dmc_20250910.log for detailed logging output")

if __name__ == "__main__":
    test_all_services()
