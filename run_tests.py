"""
Test runner for WUTC application.
Runs all unit tests to validate the refactored architecture.
"""

import sys
import unittest
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def run_all_tests():
    """Run all unit tests in the tests directory."""
    # Discover and run all tests
    loader = unittest.TestLoader()
    suite = loader.discover('tests', pattern='test_*.py')

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code based on test results
    if result.wasSuccessful():
        print("\n✅ All tests passed!")
        return 0
    else:
        print(
            f"\n❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s)")
        return 1


def run_specific_test(test_module):
    """Run tests from a specific module."""
    suite = unittest.TestLoader().loadTestsFromName(f'tests.{test_module}')
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print(f"\n✅ All tests in {test_module} passed!")
        return 0
    else:
        print(
            f"\n❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s) in {test_module}")
        return 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run WUTC unit tests")
    parser.add_argument(
        "--module", "-m", help="Run tests from specific module (e.g., test_domain_models)")
    parser.add_argument("--list", "-l", action="store_true",
                        help="List available test modules")

    args = parser.parse_args()

    if args.list:
        # List all test modules
        test_files = [f for f in os.listdir(
            'tests') if f.startswith('test_') and f.endswith('.py')]
        print("Available test modules:")
        for test_file in test_files:
            module_name = test_file[:-3]  # Remove .py extension
            print(f"  - {module_name}")
        sys.exit(0)

    if args.module:
        sys.exit(run_specific_test(args.module))
    else:
        sys.exit(run_all_tests())
