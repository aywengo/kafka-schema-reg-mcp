#!/usr/bin/env python3
"""
Fix Schema Registry Modes for Migration Testing

This script checks and fixes the modes of DEV and PROD registries:
- DEV (38081): Should be READWRITE or IMPORT for testing
- PROD (38082): Can be VIEWONLY for production safety
"""

import requests


def check_and_fix_registry_mode(registry_name, url, desired_mode="READWRITE"):
    """Check and fix a registry's mode"""
    print(f"\n🔧 Checking {registry_name} Registry ({url})")
    print("-" * 50)

    try:
        # Check current mode
        mode_response = requests.get(f"{url}/mode", timeout=10)
        if mode_response.status_code == 200:
            current_mode_data = mode_response.json()
            current_mode = current_mode_data.get("mode", "Unknown")
            print(f"   Current Mode: {current_mode}")

            if current_mode == desired_mode:
                print(f"   ✅ Mode is already correct ({desired_mode})")
                return True
            else:
                print(f"   ⚠️  Mode needs to be changed: {current_mode} → {desired_mode}")

                # Attempt to change mode
                print(f"   🔄 Attempting to change mode to {desired_mode}...")
                change_response = requests.put(
                    f"{url}/mode",
                    headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
                    json={"mode": desired_mode},
                    timeout=10,
                )

                if change_response.status_code in [200, 204]:
                    print(f"   ✅ Successfully changed mode to {desired_mode}")
                    return True
                else:
                    print(f"   ❌ Failed to change mode: {change_response.status_code}")
                    try:
                        error_details = change_response.json()
                        print(f"      Error: {error_details}")
                    except Exception:
                        print(f"      Raw response: {change_response.text}")
                    return False
        else:
            print(f"   ❌ Failed to get current mode: {mode_response.status_code}")
            return False

    except Exception as e:
        print(f"   ❌ Error checking/fixing mode: {e}")
        return False


def main():
    """Main function to fix registry modes"""
    print("🛠️  Schema Registry Mode Fixer")
    print("=" * 50)

    # Check connectivity first
    dev_url = "http://localhost:38081"
    prod_url = "http://localhost:38082"

    try:
        print("🔍 Testing connectivity...")
        dev_response = requests.get(f"{dev_url}/subjects", timeout=5)
        prod_response = requests.get(f"{prod_url}/subjects", timeout=5)

        if dev_response.status_code != 200:
            print(f"❌ DEV registry not accessible: {dev_response.status_code}")
            return False

        if prod_response.status_code != 200:
            print(f"❌ PROD registry not accessible: {prod_response.status_code}")
            return False

        print("✅ Both registries are accessible")

    except Exception as e:
        print(f"❌ Connectivity check failed: {e}")
        print("💡 Make sure multi-registry environment is running:")
        print("   ./tests/start_multi_registry_environment.sh")
        return False

    # Fix DEV registry (should allow writes)
    dev_success = check_and_fix_registry_mode("DEV", dev_url, "READWRITE")

    # Check PROD registry (can be read-only for safety, but let's make it writable for testing)
    prod_success = check_and_fix_registry_mode("PROD", prod_url, "READWRITE")

    print("\n📊 Results Summary")
    print("-" * 30)
    print(f"DEV Registry:  {'✅ Fixed' if dev_success else '❌ Issues'}")
    print(f"PROD Registry: {'✅ Fixed' if prod_success else '❌ Issues'}")

    if dev_success and prod_success:
        print("\n🎉 All registries are now configured correctly!")
        print("   DEV: READWRITE (allows schema creation)")
        print("   PROD: READWRITE (allows migration testing)")
        print("\n🧪 You can now run migration tests:")
        print("   python3 tests/test_bulk_migration.py")
        print("   python3 tests/test_schema_migration.py")
        return True
    else:
        print("\n⚠️  Some registries need manual intervention")
        print("   Check Docker container logs:")
        print("   docker logs schema-registry-dev")
        print("   docker logs schema-registry-prod")
        return False


if __name__ == "__main__":
    success = main()
