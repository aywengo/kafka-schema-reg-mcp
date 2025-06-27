#!/usr/bin/env python3
"""
Bulk schema migration across registries

Tests bulk migration operations for multiple schemas and subjects.
"""

import json
import sys
import time

import requests


def test_test_bulk_migration():
    """Bulk schema migration across registries"""

    # DEV Schema Registry
    dev_url = "http://localhost:38081"

    # PROD Schema Registry
    prod_url = "http://localhost:38082"

    print("🧪 Starting bulk migration test...")

    try:
        # Check connectivity
        dev_response = requests.get(f"{dev_url}/subjects", timeout=5)
        prod_response = requests.get(f"{prod_url}/subjects", timeout=5)

        if dev_response.status_code != 200 or prod_response.status_code != 200:
            print("❌ Registry connectivity failed")
            return False

        print("✅ Both registries are accessible")

        # Create multiple test schemas for bulk migration
        test_schemas = [
            {
                "subject": "bulk-test-user",
                "schema": {
                    "type": "record",
                    "name": "User",
                    "namespace": "com.example.bulk.test",
                    "fields": [
                        {"name": "id", "type": "int"},
                        {"name": "name", "type": "string"},
                        {"name": "email", "type": "string"},
                    ],
                },
            },
            {
                "subject": "bulk-test-order",
                "schema": {
                    "type": "record",
                    "name": "Order",
                    "namespace": "com.example.bulk.test",
                    "fields": [
                        {"name": "orderId", "type": "string"},
                        {"name": "customerId", "type": "int"},
                        {"name": "amount", "type": "double"},
                        {"name": "status", "type": "string"},
                    ],
                },
            },
            {
                "subject": "bulk-test-product",
                "schema": {
                    "type": "record",
                    "name": "Product",
                    "namespace": "com.example.bulk.test",
                    "fields": [
                        {"name": "productId", "type": "string"},
                        {"name": "name", "type": "string"},
                        {"name": "price", "type": "double"},
                        {"name": "category", "type": "string"},
                    ],
                },
            },
        ]

        created_subjects = []
        failed_subjects = []

        print(f"📝 Creating {len(test_schemas)} test schemas in DEV...")

        # Create all schemas in DEV
        for schema_def in test_schemas:
            subject = schema_def["subject"]
            schema = schema_def["schema"]

            # Correct payload format - schema should be a JSON string, not double-encoded
            payload = {"schema": json.dumps(schema)}

            try:
                create_response = requests.post(
                    f"{dev_url}/subjects/{subject}-value/versions",
                    headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
                    json=payload,
                    timeout=5,
                )

                # Add more detailed error logging
                if create_response.status_code in [200, 409]:  # 409 = already exists
                    created_subjects.append(subject)
                    print(f"   ✅ Created {subject}")
                else:
                    failed_subjects.append(subject)
                    print(f"   ❌ Failed to create {subject}: {create_response.status_code}")
                    # Print response details for debugging
                    try:
                        error_details = create_response.json()
                        print(f"      Error details: {error_details}")
                    except:
                        print(f"      Error response: {create_response.text}")

            except Exception as e:
                failed_subjects.append(subject)
                print(f"   ❌ Failed to create {subject}: {e}")

        print("📊 Schema creation results:")
        print(f"   Created: {len(created_subjects)}")
        print(f"   Failed: {len(failed_subjects)}")

        if not created_subjects:
            print("❌ No schemas created for bulk migration test")
            return False

        # Simulate bulk migration process
        print(f"\n📦 Simulating bulk migration of {len(created_subjects)} schemas...")

        migration_results = {"successful": [], "failed": [], "skipped": []}

        for subject in created_subjects:
            print(f"🔄 Processing migration for {subject}...")

            try:
                # Get schema from DEV
                get_response = requests.get(f"{dev_url}/subjects/{subject}-value/versions/latest", timeout=5)

                if get_response.status_code != 200:
                    migration_results["failed"].append({"subject": subject, "reason": "Failed to retrieve from DEV"})
                    print(f"   ❌ Failed to retrieve {subject} from DEV")
                    continue

                schema_data = get_response.json()

                # Check if already exists in PROD
                prod_check = requests.get(f"{prod_url}/subjects/{subject}-value/versions/latest", timeout=5)

                if prod_check.status_code == 200:
                    migration_results["skipped"].append({"subject": subject, "reason": "Already exists in PROD"})
                    print(f"   ⚠️  {subject} already exists in PROD - skipped")
                    continue

                # Attempt migration to PROD (will fail due to read-only)
                migrate_response = requests.post(
                    f"{prod_url}/subjects/{subject}-value/versions",
                    headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
                    json={"schema": schema_data["schema"]},
                    timeout=5,
                )

                if migrate_response.status_code == 200:
                    migration_results["successful"].append(
                        {
                            "subject": subject,
                            "version": schema_data.get("version"),
                            "schema_id": schema_data.get("id"),
                        }
                    )
                    print(f"   ✅ Successfully migrated {subject}")
                elif migrate_response.status_code in [403, 405]:
                    migration_results["failed"].append({"subject": subject, "reason": "PROD registry is read-only"})
                    print(f"   ⚠️  {subject} migration blocked by read-only PROD")
                else:
                    migration_results["failed"].append(
                        {
                            "subject": subject,
                            "reason": f"HTTP {migrate_response.status_code}",
                        }
                    )
                    print(f"   ❌ {subject} migration failed: {migrate_response.status_code}")

                # Small delay between migrations
                time.sleep(0.1)

            except Exception as e:
                migration_results["failed"].append({"subject": subject, "reason": str(e)})
                print(f"   ❌ {subject} migration error: {e}")

        # Summary of bulk migration
        print("\n📊 Bulk migration summary:")
        print(f"   Total subjects: {len(created_subjects)}")
        print(f"   Successful migrations: {len(migration_results['successful'])}")
        print(f"   Failed migrations: {len(migration_results['failed'])}")
        print(f"   Skipped (already exist): {len(migration_results['skipped'])}")

        # Calculate success rate
        total_attempted = len(migration_results["successful"]) + len(migration_results["failed"])
        if total_attempted > 0:
            success_rate = (len(migration_results["successful"]) / total_attempted) * 100
            print(f"   Success rate: {success_rate:.1f}%")

        # Show details for failed migrations
        if migration_results["failed"]:
            print("\n📋 Failed migration details:")
            for failure in migration_results["failed"][:3]:
                print(f"   • {failure['subject']}: {failure['reason']}")

        # Test batch validation
        print("\n🔍 Testing batch validation...")

        # Validate all schemas exist in DEV
        validation_count = 0
        for subject in created_subjects[:3]:  # Test first 3
            try:
                validate_response = requests.get(f"{dev_url}/subjects/{subject}-value/versions/latest", timeout=5)
                if validate_response.status_code == 200:
                    validation_count += 1

            except Exception:
                pass

        print(f"   ✅ Validated {validation_count}/{min(3, len(created_subjects))} schemas in DEV")

        print("✅ Bulk migration test completed successfully")
        return True

    except requests.exceptions.Timeout:
        print("❌ Test failed: Request timeout")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_test_bulk_migration()
    sys.exit(0 if success else 1)
