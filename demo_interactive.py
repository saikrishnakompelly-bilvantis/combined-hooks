#!/usr/bin/env python3
"""
Demo script for testing the interactive validation dialog
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validation.ui.validation_dialog import show_validation_dialog


def main():
    """Demo the interactive validation dialog."""
    
    # Sample validation results with failures
    validation_results = {
        'errors': [
            'test_api/api.meta - assetVersion "2.0.0" should start with "1.0.0"',
            'test_api/api.meta - API.layer "pAPI" is not in allowed values ["xAPI", "sAPI", "pAPI"]',
            'test_api/api.meta - API.audience "partner" is not in allowed values ["internal", "external"]',
            'test_api/v2/api.meta - API.version.status "staging" is not in allowed values',
            'test_api/v2/api.meta - GBGF "INVALID_GBGF" is not in allowed values'
        ],
        'warnings': [
            'repository - No transaction names specified for sAPI layer'
        ],
        'meta_files': [
            'test_api/api.meta',
            'test_api/v2/api.meta'
        ],
        'api_type': 'PCF'
    }
    
    print("🧪 Testing Interactive Validation Dialog")
    print("This will show the validation failure UI that appears during git push")
    print("\nPress any key to continue...")
    input()
    
    try:
        result, justification = show_validation_dialog(validation_results)
        
        print(f"\n📋 Dialog Result: {result}")
        if justification:
            print(f"📝 Justification: {justification}")
        
        if result == 'proceed':
            print("\n✅ In a real scenario, this would:")
            print("  1. Append the justification to the commit message")
            print("  2. Append all validation failures to the commit message")
            print("  3. Allow the push to continue")
        else:
            print("\n🛑 In a real scenario, this would:")
            print("  1. Cancel the push operation")
            print("  2. Allow the developer to fix issues before pushing")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main()) 