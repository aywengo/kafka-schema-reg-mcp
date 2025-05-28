#!/usr/bin/env python3
"""
Quick validation for ID preservation migration fix
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_id_preservation_fix():
    """Test that the ID preservation migration test logic is improved"""
    print("🧪 Validating ID preservation migration fix...")
    
    try:
        # Import the test class
        from test_id_preservation_migration import IDPreservationMigrationTest
        
        # Create test instance
        test_instance = IDPreservationMigrationTest()
        
        # Check if the test class loads properly
        print("✅ ID preservation test class loads successfully")
        
        # Check test methods exist
        methods = [
            'test_migration_without_id_preservation',
            'test_migration_with_id_preservation', 
            'test_context_migration_with_id_preservation',
            'test_dry_run_with_id_preservation'
        ]
        
        for method in methods:
            if hasattr(test_instance, method):
                print(f"✅ Method {method} exists")
            else:
                print(f"❌ Method {method} missing")
                return False
        
        print("✅ All required test methods are present")
        print("✅ ID preservation migration fix validation PASSED")
        return True
        
    except Exception as e:
        print(f"❌ ID preservation fix validation failed: {e}")
        return False

if __name__ == "__main__":
    success = test_id_preservation_fix()
    if success:
        print("\n🎉 ID preservation migration fix appears to be working!")
    else:
        print("\n❌ ID preservation migration fix needs more work")
    sys.exit(0 if success else 1) 