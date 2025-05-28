#!/usr/bin/env python3
"""
Diagnose Schema Registry Migration Issues

This script checks the status and configuration of both DEV and PROD
Schema Registry instances to help debug migration failures.
"""

import requests
import json
import sys

def check_registry(name, url):
    """Check a single registry's status and configuration"""
    print(f"\n🔍 Checking {name} Registry ({url})")
    print("-" * 50)
    
    try:
        # Basic connectivity
        response = requests.get(f"{url}/subjects", timeout=10)
        if response.status_code == 200:
            subjects = response.json()
            print(f"✅ Connectivity: OK ({len(subjects)} subjects)")
        else:
            print(f"❌ Connectivity: Failed ({response.status_code})")
            return False
            
        # Check mode
        try:
            mode_response = requests.get(f"{url}/mode", timeout=10)
            if mode_response.status_code == 200:
                mode_data = mode_response.json()
                mode = mode_data.get('mode', 'Unknown')
                print(f"🔧 Mode: {mode}")
            else:
                print(f"⚠️  Mode: Could not retrieve ({mode_response.status_code})")
        except Exception as e:
            print(f"⚠️  Mode: Error - {e}")
            
        # Check global config
        try:
            config_response = requests.get(f"{url}/config", timeout=10)
            if config_response.status_code == 200:
                config_data = config_response.json()
                compatibility = config_data.get('compatibilityLevel', 'Unknown')
                print(f"⚙️  Global Compatibility: {compatibility}")
            else:
                print(f"⚠️  Global Config: Could not retrieve ({config_response.status_code})")
        except Exception as e:
            print(f"⚠️  Global Config: Error - {e}")
            
        # Test schema registration capability
        test_schema = {
            "type": "record",
            "name": "DiagnosticTest",
            "namespace": "com.example.diagnostic",
            "fields": [
                {"name": "id", "type": "int"},
                {"name": "timestamp", "type": "long"}
            ]
        }
        
        test_payload = {"schema": json.dumps(test_schema)}
        test_subject = "diagnostic-test-subject"
        
        try:
            reg_response = requests.post(
                f"{url}/subjects/{test_subject}-value/versions",
                headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
                json=test_payload,
                timeout=10
            )
            
            if reg_response.status_code in [200, 409]:
                print(f"✅ Schema Registration: Allowed")
                
                # Try to delete the test subject if we created it
                if reg_response.status_code == 200:
                    try:
                        del_response = requests.delete(f"{url}/subjects/{test_subject}", timeout=5)
                        print(f"🗑️  Test cleanup: {'OK' if del_response.status_code in [200, 404] else 'Failed'}")
                    except:
                        pass
                        
            elif reg_response.status_code in [403, 405, 422]:
                print(f"🔒 Schema Registration: Blocked ({reg_response.status_code})")
                try:
                    error_details = reg_response.json()
                    error_msg = error_details.get('message', 'No details')
                    print(f"   Reason: {error_msg}")
                except:
                    print(f"   Raw response: {reg_response.text}")
            else:
                print(f"❌ Schema Registration: Error ({reg_response.status_code})")
                try:
                    error_details = reg_response.json()
                    print(f"   Details: {error_details}")
                except:
                    print(f"   Raw response: {reg_response.text}")
                    
        except Exception as e:
            print(f"❌ Schema Registration Test: Error - {e}")
            
        return True
        
    except requests.exceptions.Timeout:
        print(f"❌ Connectivity: Timeout")
        return False
    except Exception as e:
        print(f"❌ Connectivity: Error - {e}")
        return False

def main():
    """Main diagnostic function"""
    print("🩺 Schema Registry Migration Diagnostic")
    print("=" * 60)
    
    # Check DEV registry
    dev_ok = check_registry("DEV", "http://localhost:38081")
    
    # Check PROD registry  
    prod_ok = check_registry("PROD", "http://localhost:38082")
    
    # Summary
    print(f"\n📊 Diagnostic Summary")
    print("-" * 30)
    print(f"DEV Registry:  {'✅ OK' if dev_ok else '❌ Issues'}")
    print(f"PROD Registry: {'✅ OK' if prod_ok else '❌ Issues'}")
    
    if dev_ok and prod_ok:
        print(f"\n💡 Migration Troubleshooting Tips:")
        print(f"   • Check that DEV registry allows schema registration")
        print(f"   • Verify PROD registry is in READONLY mode (expected)")
        print(f"   • Ensure schemas have proper namespace fields")
        print(f"   • Check compatibility settings if schemas are related")
        print(f"\n🔧 Next Steps:")
        print(f"   1. Run: python3 tests/test_bulk_migration.py")
        print(f"   2. Check detailed error messages")
        print(f"   3. Verify multi-registry environment is running")
    else:
        print(f"\n⚠️  Registry Issues Detected!")
        print(f"   Please ensure multi-registry environment is running:")
        print(f"   ./tests/start_multi_registry_environment.sh")
    
    return dev_ok and prod_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 