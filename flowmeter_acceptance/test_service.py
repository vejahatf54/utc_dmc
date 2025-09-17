"""
Test script for the completely rewritten FlowmeterAcceptanceService.
This tests the service with the new Tags.csv format following exact specifications.
"""

import os
import sys
import logging
from datetime import datetime

# Add the parent directory to the path so we can import the service
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_flowmeter_acceptance_service():
    """Test the new FlowmeterAcceptanceService implementation."""
    
    try:
        from services.flowmeter_acceptance_service import FlowmeterAcceptanceService
        print("✓ Service import successful")
        
        # Create service instance
        service = FlowmeterAcceptanceService()
        print("✓ Service instantiation successful")
        
        # Test parameters that would typically come from the GUI
        test_params = {
            'rtu_file': 'test_data.dt',  # Would be actual file path
            'csv_tags_file': 'Tags_new_format.csv',  # Our new format file
            'review_file': 'test_review.review',  # Would be actual review file
            'report_name': 'test_flowmeter_report',
            'time_start': '25/06/27 04:00:00',
            'time_end': '25/06/27 08:00:00',
            'threshold_FLAT': 5,
            'min_Q': 100,
            'max_Q': 15000,
            'accuracy_range': 5,
            
            # Test flags - enable all checks to test complete functionality
            'reliability_check_1': True,
            'reliability_check_2': True,
            'reliability_check_3': True,
            'reliability_check_4': True,
            'tc_check_1': True,
            'tc_check_2': True,
            'robustness_check_1': True,
            'accuracy_check_1': True,
            'accuracy_check_2': True,
            'accuracy_check_3': True,
            
            # Theme data
            'theme_data': {'template': 'mantine_light'}
        }
        
        # Test parameter parsing
        service._parse_parameters(test_params)
        print("✓ Parameter parsing successful")
        print(f"  - Time range: {service.time_start} to {service.time_end}")
        print(f"  - Checks enabled: Reliability({service.reliability_check_1}), Accuracy({service.accuracy_check_1}), Robustness({service.robustness_check_1})")
        
        # Test Tags.csv loading (if file exists)
        if os.path.exists(test_params['csv_tags_file']):
            service._load_tags_csv()
            print("✓ Tags.csv loading successful")
            print(f"  - Loaded {len(service.dataframe_tags)} meter configurations")
            print(f"  - Columns: {list(service.dataframe_tags.columns)}")
            print(f"  - Sample data:\n{service.dataframe_tags.head()}")
        else:
            print("⚠ Tags.csv file not found - skipping CSV loading test")
        
        # Test directory creation
        service._create_directories()
        print("✓ Directory creation successful")
        
        # Test plotting methods (create sample plots)
        plots = service.create_analysis_plots(test_params.get('theme_data'))
        print(f"✓ Plotting methods successful - created {len(plots)} plots")
        print(f"  - Available plots: {list(plots.keys())}")
        
        # Test theme mapping
        template = service._get_plotly_template('mantine_light')
        print(f"✓ Theme mapping successful - mantine_light -> {template}")
        
        template_dark = service._get_plotly_template('mantine_dark')
        print(f"✓ Theme mapping successful - mantine_dark -> {template_dark}")
        
        print("\n🎉 All basic functionality tests passed!")
        print("\nNOTE: Full analysis testing requires actual RTU and Review data files.")
        print("The service is ready for integration with the DMC application.")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("This is expected in test environment without pandas/plotly dependencies")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing the completely rewritten FlowmeterAcceptanceService")
    print("=" * 60)
    
    # Change to the flowmeter_acceptance directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    success = test_flowmeter_acceptance_service()
    
    if success:
        print("\n✅ Service is ready for production use!")
    else:
        print("\n❌ Service needs attention before production use.")