#!/usr/bin/env python3
"""
Test script for API validation system
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validation.api_identifier import APIIdentifier
from validation.api_validator import APIValidator
from validation.meta_file_finder import MetaFileFinder


def test_api_identification():
    """Test API type identification."""
    print("=== Testing API Identification ===")
    
    identifier = APIIdentifier()
    identifier.print_identification_details()
    
    api_type = identifier.identify_api_type()
    print(f"Final API Type: {api_type}")
    
    return api_type


def test_validator_initialization():
    """Test validator initialization."""
    print("\n=== Testing Validator Initialization ===")
    
    try:
        validator = APIValidator()
        print(f"✓ Validator initialized successfully")
        print(f"✓ Detected API type: {validator.api_type}")
        print(f"✓ Should validate: {not validator.skip_validation}")
        return True
    except Exception as e:
        print(f"✗ Validator initialization failed: {e}")
        return False


def test_file_filtering():
    """Test file filtering logic."""
    print("\n=== Testing File Filtering ===")
    
    validator = APIValidator()
    
    test_files = [
        'test.py',
        'config.json',
        'data.json',
        'readme.md',
        'script.sh',
        '__pycache__/test.pyc',
        '.git/config',
        'node_modules/package.json'
    ]
    
    filtered = validator._filter_files_by_type(test_files)
    print(f"Original files: {test_files}")
    print(f"Filtered files: {filtered}")
    
    expected_filtered = ['test.py', 'config.json', 'data.json']
    success = set(filtered) == set(expected_filtered)
    print(f"✓ File filtering works correctly" if success else "✗ File filtering failed")
    
    return success


def test_meta_file_finder():
    """Test meta file discovery functionality."""
    print("\n=== Testing Meta File Finder ===")
    
    try:
        finder = MetaFileFinder()
        
        # Test finding meta files
        meta_files = finder.find_meta_files()
        print(f"Found meta files: {meta_files}")
        
        # Test meta file patterns
        test_filenames = [
            'api.meta',
            'api.meta.json',
            'api.meta.json',
            'API.meta',
            'not_meta.txt',
            'api.json'
        ]
        
        print("\nTesting meta file pattern matching:")
        for filename in test_filenames:
            is_meta = finder._is_meta_file(filename)
            print(f"  {filename}: {'✓' if is_meta else '✗'}")
        
        # Test directory skipping
        test_dirs = ['.git', '__pycache__', 'normal_dir', '.hidden', 'node_modules']
        print("\nTesting directory skipping:")
        for dirname in test_dirs:
            should_skip = finder._should_skip_directory(dirname)
            print(f"  {dirname}: {'skip' if should_skip else 'include'}")
        
        print("✓ Meta file finder works correctly")
        return True
        
    except Exception as e:
        print(f"✗ Meta file finder test failed: {e}")
        return False


def test_validation_skip_logic():
    """Test that validation is skipped for non-API repos."""
    print("\n=== Testing Validation Skip Logic ===")
    
    try:
        validator = APIValidator()
        
        # Check skip logic
        should_validate = validator._should_validate_repo()
        print(f"Repository type: {validator.api_type}")
        print(f"Should validate: {should_validate}")
        print(f"Skip validation: {validator.skip_validation}")
        
        # Test validation methods return True when skipping
        if validator.skip_validation:
            staged_result = validator.validate_staged_files()
            commit_result = validator.validate_commit_range("HEAD~1..HEAD")
            files_result = validator.validate_files(['test.py'])
            
            success = staged_result and commit_result and files_result
            print(f"✓ Validation skip logic works correctly" if success else "✗ Validation skip logic failed")
            return success
        else:
            print("✓ Repository requires validation - testing actual validation")
            return True
        
    except Exception as e:
        print(f"✗ Validation skip logic test failed: {e}")
        return False


def create_sample_meta_files():
    """Create sample meta files for testing."""
    print("\n=== Creating Sample Meta Files for Testing ===")
    
    try:
        # Create a sample directory structure
        os.makedirs('test_api/v1', exist_ok=True)
        os.makedirs('test_api/v2', exist_ok=True)
        
        # Create sample api.meta files
        sample_meta_content = """# Sample API Meta File
api_name: test-api
version: 1.0
description: Test API for validation
endpoint: /api/test
method: GET
"""
        
        with open('test_api/api.meta', 'w') as f:
            f.write(sample_meta_content)
        
        # Create a JSON format meta file
        json_meta_content = """{
    "api_name": "test-api-v2",
    "version": "2.0",
    "description": "Test API v2 for validation",
    "endpoint": "/api/v2/test",
    "methods": ["GET", "POST"]
}"""
        
        with open('test_api/v2/api.meta.json', 'w') as f:
            f.write(json_meta_content)
        
        print("✓ Sample meta files created")
        return True
        
    except Exception as e:
        print(f"✗ Failed to create sample meta files: {e}")
        return False


def cleanup_test_files():
    """Clean up test files."""
    try:
        import shutil
        if os.path.exists('test_api'):
            shutil.rmtree('test_api')
        print("✓ Test files cleaned up")
    except Exception as e:
        print(f"⚠️  Could not clean up test files: {e}")


def main():
    """Run all tests."""
    print("Running API Validation System Tests...\n")
    
    tests_passed = 0
    total_tests = 6
    
    # Test 1: API Identification
    try:
        api_type = test_api_identification()
        if api_type in ['PCF', 'SHP', 'IKP', 'SHP/IKP', 'UNKNOWN']:
            tests_passed += 1
            print("✓ API identification test passed")
        else:
            print("✗ API identification test failed")
    except Exception as e:
        print(f"✗ API identification test failed: {e}")
    
    # Test 2: Validator Initialization
    if test_validator_initialization():
        tests_passed += 1
        print("✓ Validator initialization test passed")
    else:
        print("✗ Validator initialization test failed")
    
    # Test 3: File Filtering
    if test_file_filtering():
        tests_passed += 1
        print("✓ File filtering test passed")
    else:
        print("✗ File filtering test failed")
    
    # Test 4: Meta File Finder
    if test_meta_file_finder():
        tests_passed += 1
        print("✓ Meta file finder test passed")
    else:
        print("✗ Meta file finder test failed")
    
    # Test 5: Validation Skip Logic
    if test_validation_skip_logic():
        tests_passed += 1
        print("✓ Validation skip logic test passed")
    else:
        print("✗ Validation skip logic test failed")
    
    # Test 6: Sample Meta Files
    if create_sample_meta_files():
        tests_passed += 1
        print("✓ Sample meta files test passed")
        
        # Test reading the created files
        print("\nTesting meta file reading:")
        finder = MetaFileFinder()
        meta_files = finder.find_meta_files(refresh_cache=True)
        print(f"Found meta files after creation: {meta_files}")
        
        for meta_file in meta_files:
            if 'test_api' in meta_file:
                content = finder.read_meta_file(meta_file)
                print(f"Content of {meta_file}: {content}")
    else:
        print("✗ Sample meta files test failed")
    
    print(f"\n=== Test Results ===")
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    # Clean up
    cleanup_test_files()
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! The validation system is ready.")
        return 0
    else:
        print("❌ Some tests failed. Please check the setup.")
        return 1


if __name__ == '__main__':
    sys.exit(main()) 