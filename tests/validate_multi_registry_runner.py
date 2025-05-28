#!/usr/bin/env python3
"""
Multi-Registry Test Runner Validation

This script validates that the run_multi_registry_tests.sh script
can find all its referenced test components.
"""

import os
import sys

def validate_multi_registry_runner():
    """Validate that all components for multi-registry testing are available"""
    print("🔍 Validating Multi-Registry Test Runner Components")
    print("=" * 60)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Test scripts that should exist
    required_scripts = [
        "run_multi_registry_tests.sh",
        "test_multi_registry_validation.py", 
        "test_lightweight_migration_integration.py",
        "run_default_context_dot_tests.sh",
        "run_all_versions_migration_tests.sh", 
        "run_id_preservation_tests.sh",
        "test_end_to_end_workflows.py",
        "test_error_handling.py",
        "test_performance_load.py"
    ]
    
    # Optional scripts (won't fail validation if missing)
    optional_scripts = [
        "start_multi_registry_environment.sh",
        "stop_multi_registry_environment.sh",
        "docker-compose.multi-test.yml"
    ]
    
    missing_required = []
    missing_optional = []
    found_required = []
    found_optional = []
    
    print("📋 Checking Required Test Scripts:")
    for script in required_scripts:
        script_path = os.path.join(script_dir, script)
        if os.path.exists(script_path):
            print(f"   ✅ {script}")
            found_required.append(script)
        else:
            print(f"   ❌ {script} (MISSING)")
            missing_required.append(script)
    
    print(f"\n📋 Checking Optional Test Scripts:")
    for script in optional_scripts:
        script_path = os.path.join(script_dir, script)
        if os.path.exists(script_path):
            print(f"   ✅ {script}")
            found_optional.append(script)
        else:
            print(f"   ⚠️  {script} (optional, not found)")
            missing_optional.append(script)
    
    print(f"\n📊 Validation Summary:")
    print(f"   Required Scripts: {len(found_required)}/{len(required_scripts)} found")
    print(f"   Optional Scripts: {len(found_optional)}/{len(optional_scripts)} found")
    
    if missing_required:
        print(f"\n❌ VALIDATION FAILED")
        print(f"   Missing required scripts:")
        for script in missing_required:
            print(f"     • {script}")
        print(f"\n   The multi-registry test runner may not work properly.")
        return False
    else:
        print(f"\n✅ VALIDATION PASSED")
        print(f"   All required components are available!")
        print(f"   The multi-registry test runner is ready to use.")
        
        if missing_optional:
            print(f"\n⚠️  Optional components missing:")
            for script in missing_optional:
                print(f"     • {script}")
            print(f"   You may need to start the test environment manually.")
        
        print(f"\n🚀 Usage:")
        print(f"   ./run_multi_registry_tests.sh           # Run all tests")
        print(f"   ./run_multi_registry_tests.sh --help    # Show options")
        
        return True

if __name__ == "__main__":
    success = validate_multi_registry_runner()
    sys.exit(0 if success else 1) 