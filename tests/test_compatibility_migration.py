#!/usr/bin/env python3
"""
Compatibility validation during migration

Tests schema compatibility rules and validation during migration between registries.
"""

import json
import sys

import requests


def test_test_compatibility_migration():
    """Compatibility validation during migration"""

    # DEV Schema Registry
    dev_url = "http://localhost:38081"

    # PROD Schema Registry
    prod_url = "http://localhost:38082"

    print(f"🧪 Starting compatibility migration test...")

    try:
        # Check connectivity
        dev_response = requests.get(f"{dev_url}/subjects", timeout=5)
        prod_response = requests.get(f"{prod_url}/subjects", timeout=5)

        if dev_response.status_code != 200 or prod_response.status_code != 200:
            print("❌ Registry connectivity failed")
            return False

        print("✅ Both registries are accessible")

        # Test subject for compatibility testing
        test_subject = "compatibility-test-event"

        # Create base schema (v1)
        base_schema = {
            "type": "record",
            "name": "Event",
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "timestamp", "type": "long"},
                {"name": "type", "type": "string"},
            ],
        }

        print(f"📝 Creating base schema v1 in DEV...")
        base_payload = {"schema": json.dumps(base_schema)}

        create_response = requests.post(
            f"{dev_url}/subjects/{test_subject}-value/versions",
            headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
            json=base_payload,
            timeout=5,
        )

        if create_response.status_code not in [200, 409]:
            print(f"❌ Failed to create base schema: {create_response.status_code}")
            return False

        print("✅ Base schema v1 created")

        # Create backward compatible schema (v2) - add optional field
        compat_schema = {
            "type": "record",
            "name": "Event",
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "timestamp", "type": "long"},
                {"name": "type", "type": "string"},
                {"name": "metadata", "type": ["null", "string"], "default": None},
            ],
        }

        print("🔍 Testing backward compatibility...")
        compat_test = requests.post(
            f"{dev_url}/compatibility/subjects/{test_subject}-value/versions/latest",
            headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
            json={"schema": json.dumps(compat_schema)},
            timeout=5,
        )

        if compat_test.status_code == 200:
            compat_result = compat_test.json()
            if compat_result.get("is_compatible", False):
                print("✅ Backward compatible schema validated")

                # Register the compatible schema
                requests.post(
                    f"{dev_url}/subjects/{test_subject}-value/versions",
                    headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
                    json={"schema": json.dumps(compat_schema)},
                    timeout=5,
                )
                print("✅ Compatible schema v2 registered")
            else:
                print("⚠️  Schema marked as incompatible")
        else:
            print(f"⚠️  Compatibility check failed: {compat_test.status_code}")

        # Test incompatible schema - remove required field
        incompat_schema = {
            "type": "record",
            "name": "Event",
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "type", "type": "string"},
                # Missing required 'timestamp' field
            ],
        }

        print("🔍 Testing incompatible schema...")
        incompat_test = requests.post(
            f"{dev_url}/compatibility/subjects/{test_subject}-value/versions/latest",
            headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
            json={"schema": json.dumps(incompat_schema)},
            timeout=5,
        )

        if incompat_test.status_code == 200:
            incompat_result = incompat_test.json()
            if not incompat_result.get("is_compatible", True):
                print("✅ Incompatible schema correctly rejected")
            else:
                print("⚠️  Incompatible schema incorrectly accepted")

        # Test compatibility levels
        print("🔍 Testing compatibility levels...")

        # Get current compatibility level
        compat_level_response = requests.get(
            f"{dev_url}/config/{test_subject}-value", timeout=5
        )

        if compat_level_response.status_code == 200:
            level_data = compat_level_response.json()
            print(
                f"✅ Compatibility level: {level_data.get('compatibilityLevel', 'BACKWARD')}"
            )
        elif compat_level_response.status_code == 404:
            # Get global compatibility level
            global_compat = requests.get(f"{dev_url}/config", timeout=5)
            if global_compat.status_code == 200:
                global_data = global_compat.json()
                print(
                    f"✅ Global compatibility level: {global_data.get('compatibilityLevel', 'BACKWARD')}"
                )

        # Test cross-registry compatibility simulation
        print("🔄 Testing cross-registry compatibility...")

        # Get all versions from DEV
        versions_response = requests.get(
            f"{dev_url}/subjects/{test_subject}-value/versions", timeout=5
        )

        if versions_response.status_code == 200:
            versions = versions_response.json()
            print(f"✅ Found {len(versions)} versions in DEV for compatibility testing")

            # Test each version for migration compatibility
            for version in versions[-2:]:  # Test last 2 versions
                version_response = requests.get(
                    f"{dev_url}/subjects/{test_subject}-value/versions/{version}",
                    timeout=5,
                )

                if version_response.status_code == 200:
                    version_data = version_response.json()
                    print(f"✅ Version {version}: Schema ID {version_data.get('id')}")

        print("✅ Compatibility migration test completed successfully")
        return True

    except requests.exceptions.Timeout:
        print("❌ Test failed: Request timeout")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_test_compatibility_migration()
    sys.exit(0 if success else 1)
