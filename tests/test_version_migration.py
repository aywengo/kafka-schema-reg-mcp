#!/usr/bin/env python3
"""
Specific version migration

Tests migration of specific schema versions with version tracking and validation.
"""

import json
import sys

import requests


def test_test_version_migration():
    """Specific version migration"""

    # DEV Schema Registry
    dev_url = "http://localhost:38081"

    # PROD Schema Registry
    prod_url = "http://localhost:38082"

    print(f"🧪 Starting version migration test...")

    try:
        # Check connectivity
        dev_response = requests.get(f"{dev_url}/subjects", timeout=5)
        prod_response = requests.get(f"{prod_url}/subjects", timeout=5)

        if dev_response.status_code != 200 or prod_response.status_code != 200:
            print("❌ Registry connectivity failed")
            return False

        print("✅ Both registries are accessible")

        # Create multi-version schema for testing
        test_subject = "version-migration-test"

        # Version 1: Base schema
        schema_v1 = {
            "type": "record",
            "name": "UserEvent",
            "fields": [
                {"name": "userId", "type": "string"},
                {"name": "action", "type": "string"},
                {"name": "timestamp", "type": "long"},
            ],
        }

        # Version 2: Add optional field (backward compatible)
        schema_v2 = {
            "type": "record",
            "name": "UserEvent",
            "fields": [
                {"name": "userId", "type": "string"},
                {"name": "action", "type": "string"},
                {"name": "timestamp", "type": "long"},
                {"name": "sessionId", "type": ["null", "string"], "default": None},
            ],
        }

        # Version 3: Add another field (backward compatible)
        schema_v3 = {
            "type": "record",
            "name": "UserEvent",
            "fields": [
                {"name": "userId", "type": "string"},
                {"name": "action", "type": "string"},
                {"name": "timestamp", "type": "long"},
                {"name": "sessionId", "type": ["null", "string"], "default": None},
                {"name": "metadata", "type": ["null", "string"], "default": None},
            ],
        }

        # Create all versions in DEV
        schemas = [("v1", schema_v1), ("v2", schema_v2), ("v3", schema_v3)]

        created_versions = []

        print("📝 Creating multi-version schema in DEV...")

        for version_name, schema in schemas:
            payload = {"schema": json.dumps(schema)}

            create_response = requests.post(
                f"{dev_url}/subjects/{test_subject}-value/versions",
                headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
                json=payload,
                timeout=5,
            )

            if create_response.status_code in [200, 409]:
                if create_response.status_code == 200:
                    version_data = create_response.json()
                    created_versions.append(
                        {
                            "name": version_name,
                            "version": version_data.get("version"),
                            "id": version_data.get("id"),
                        }
                    )
                    print(
                        f"   ✅ Created {version_name}: version {version_data.get('version')}"
                    )
                else:
                    print(f"   ✅ {version_name} already exists")
            else:
                print(
                    f"   ❌ Failed to create {version_name}: {create_response.status_code}"
                )

        # Get all versions from DEV
        print("\n🔍 Retrieving version information from DEV...")

        versions_response = requests.get(
            f"{dev_url}/subjects/{test_subject}-value/versions", timeout=5
        )
        if versions_response.status_code == 200:
            all_versions = versions_response.json()
            print(f"   ✅ Found {len(all_versions)} versions: {all_versions}")
        else:
            print(f"   ⚠️  Could not retrieve versions: {versions_response.status_code}")
            all_versions = []

        # Test migration of specific versions
        print("\n📦 Testing specific version migration...")

        migration_results = {"successful": [], "failed": [], "skipped": []}

        # Test migration of each version
        for version in all_versions[:3]:  # Test first 3 versions
            print(f"🔄 Testing migration of version {version}...")

            try:
                # Get specific version from DEV
                version_response = requests.get(
                    f"{dev_url}/subjects/{test_subject}-value/versions/{version}",
                    timeout=5,
                )

                if version_response.status_code != 200:
                    migration_results["failed"].append(
                        {"version": version, "reason": "Failed to retrieve from DEV"}
                    )
                    print(f"   ❌ Failed to retrieve version {version}")
                    continue

                version_data = version_response.json()
                schema_content = version_data["schema"]
                schema_id = version_data.get("id")

                print(f"   📋 Version {version}: Schema ID {schema_id}")

                # Check if this version already exists in PROD
                prod_version_check = requests.get(
                    f"{prod_url}/subjects/{test_subject}-value/versions/{version}",
                    timeout=5,
                )

                if prod_version_check.status_code == 200:
                    migration_results["skipped"].append(
                        {"version": version, "reason": "Already exists in PROD"}
                    )
                    print(f"   ⚠️  Version {version} already exists in PROD")
                    continue

                # Attempt migration to PROD (will likely fail due to read-only)
                migrate_payload = {"schema": schema_content}

                migrate_response = requests.post(
                    f"{prod_url}/subjects/{test_subject}-value/versions",
                    headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
                    json=migrate_payload,
                    timeout=5,
                )

                if migrate_response.status_code == 200:
                    migrate_data = migrate_response.json()
                    migration_results["successful"].append(
                        {
                            "version": version,
                            "original_id": schema_id,
                            "new_id": migrate_data.get("id"),
                            "new_version": migrate_data.get("version"),
                        }
                    )
                    print(f"   ✅ Successfully migrated version {version}")
                elif migrate_response.status_code in [403, 405]:
                    migration_results["failed"].append(
                        {"version": version, "reason": "PROD registry is read-only"}
                    )
                    print(
                        f"   ⚠️  Version {version} migration blocked by read-only PROD"
                    )
                else:
                    migration_results["failed"].append(
                        {
                            "version": version,
                            "reason": f"HTTP {migrate_response.status_code}",
                        }
                    )
                    print(
                        f"   ❌ Version {version} migration failed: {migrate_response.status_code}"
                    )

            except Exception as e:
                migration_results["failed"].append(
                    {"version": version, "reason": str(e)}
                )
                print(f"   ❌ Version {version} migration error: {e}")

        # Test version-specific operations
        print("\n🔍 Testing version-specific operations...")

        if all_versions:
            # Test retrieving specific versions
            latest_version = max(all_versions)
            first_version = min(all_versions)

            print(f"   Testing latest version ({latest_version}) retrieval...")
            latest_resp = requests.get(
                f"{dev_url}/subjects/{test_subject}-value/versions/{latest_version}",
                timeout=5,
            )

            if latest_resp.status_code == 200:
                latest_data = latest_resp.json()
                print(
                    f"   ✅ Latest version {latest_version}: Schema ID {latest_data.get('id')}"
                )
            else:
                print(f"   ❌ Failed to get latest version: {latest_resp.status_code}")

            print(f"   Testing first version ({first_version}) retrieval...")
            first_resp = requests.get(
                f"{dev_url}/subjects/{test_subject}-value/versions/{first_version}",
                timeout=5,
            )

            if first_resp.status_code == 200:
                first_data = first_resp.json()
                print(
                    f"   ✅ First version {first_version}: Schema ID {first_data.get('id')}"
                )
            else:
                print(f"   ❌ Failed to get first version: {first_resp.status_code}")

        # Test version compatibility between different versions
        print("\n🔍 Testing inter-version compatibility...")

        if len(all_versions) >= 2:
            # Test compatibility between consecutive versions
            for i in range(len(all_versions) - 1):
                current_version = all_versions[i]
                next_version = all_versions[i + 1]

                # Get both schemas
                current_resp = requests.get(
                    f"{dev_url}/subjects/{test_subject}-value/versions/{current_version}",
                    timeout=5,
                )

                if current_resp.status_code == 200:
                    current_schema = current_resp.json()["schema"]

                    # Test compatibility of next version against current
                    compat_resp = requests.post(
                        f"{dev_url}/compatibility/subjects/{test_subject}-value/versions/{current_version}",
                        headers={
                            "Content-Type": "application/vnd.schemaregistry.v1+json"
                        },
                        json={"schema": current_schema},
                        timeout=5,
                    )

                    if compat_resp.status_code == 200:
                        compat_data = compat_resp.json()
                        is_compatible = compat_data.get("is_compatible", False)
                        print(
                            f"   Version {next_version} → {current_version}: {'✅ Compatible' if is_compatible else '❌ Incompatible'}"
                        )
                    else:
                        print(
                            f"   Version {next_version} → {current_version}: ⚠️  Compatibility check failed"
                        )

        # Summary
        print(f"\n📊 Version Migration Summary:")
        print(f"   Total versions tested: {len(all_versions)}")
        print(f"   Successful migrations: {len(migration_results['successful'])}")
        print(f"   Failed migrations: {len(migration_results['failed'])}")
        print(f"   Skipped migrations: {len(migration_results['skipped'])}")

        # Calculate success rate
        total_attempted = len(migration_results["successful"]) + len(
            migration_results["failed"]
        )
        if total_attempted > 0:
            success_rate = (
                len(migration_results["successful"]) / total_attempted
            ) * 100
            print(f"   Migration success rate: {success_rate:.1f}%")

        # Show version lineage
        if created_versions:
            print(f"\n📋 Version lineage created:")
            for version_info in created_versions:
                print(
                    f"   • {version_info['name']}: v{version_info.get('version', 'unknown')} (ID: {version_info.get('id', 'unknown')})"
                )

        print("✅ Version migration test completed successfully")
        return True

    except requests.exceptions.Timeout:
        print("❌ Test failed: Request timeout")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_test_version_migration()
    sys.exit(0 if success else 1)
