#!/usr/bin/env python3
"""
Schema drift detection between registries

Tests detection of schema drift and evolution differences between DEV and PROD.
"""

import json
import sys
from datetime import datetime

import requests


def test_test_schema_drift():
    """Schema drift detection between registries"""

    # DEV Schema Registry
    dev_url = "http://localhost:38081"

    # PROD Schema Registry
    prod_url = "http://localhost:38082"

    print("🧪 Starting schema drift detection test...")

    try:
        # Check connectivity
        dev_response = requests.get(f"{dev_url}/subjects", timeout=5)
        prod_response = requests.get(f"{prod_url}/subjects", timeout=5)

        if dev_response.status_code != 200 or prod_response.status_code != 200:
            print("❌ Registry connectivity failed")
            return False

        print("✅ Both registries are accessible")

        # Create test schemas to simulate drift
        drift_test_subject = "drift-test-event"

        # Base schema (v1) - create in both registries
        base_schema = {
            "type": "record",
            "name": "Event",
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "timestamp", "type": "long"},
                {"name": "eventType", "type": "string"},
            ],
        }

        print("📝 Creating base schema in DEV...")
        base_payload = {"schema": json.dumps(base_schema)}

        dev_create = requests.post(
            f"{dev_url}/subjects/{drift_test_subject}-value/versions",
            headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
            json=base_payload,
            timeout=5,
        )

        if dev_create.status_code not in [200, 409]:
            print(f"⚠️  Failed to create base schema in DEV: {dev_create.status_code}")
        else:
            print("✅ Base schema created in DEV")

        # Simulate evolved schema in DEV (v2)
        evolved_schema = {
            "type": "record",
            "name": "Event",
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "timestamp", "type": "long"},
                {"name": "eventType", "type": "string"},
                {"name": "metadata", "type": ["null", "string"], "default": None},
                {"name": "version", "type": "int", "default": 1},
            ],
        }

        print("📝 Creating evolved schema v2 in DEV...")
        evolved_payload = {"schema": json.dumps(evolved_schema)}

        dev_evolve = requests.post(
            f"{dev_url}/subjects/{drift_test_subject}-value/versions",
            headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
            json=evolved_payload,
            timeout=5,
        )

        if dev_evolve.status_code in [200, 409]:
            print("✅ Evolved schema v2 created in DEV")
        else:
            print(f"⚠️  Failed to create evolved schema: {dev_evolve.status_code}")

        # Get all subjects from both registries for drift analysis
        dev_subjects = set(dev_response.json())
        prod_subjects = set(prod_response.json())

        print(
            f"\n🔍 Analyzing schema drift across {len(dev_subjects | prod_subjects)} total subjects..."
        )

        drift_analysis = {
            "subjects_analyzed": 0,
            "version_drifts": [],
            "schema_drifts": [],
            "missing_in_prod": [],
            "missing_in_dev": [],
            "identical_subjects": [],
        }

        # Analyze common subjects for drift
        common_subjects = dev_subjects & prod_subjects
        dev_only_subjects = dev_subjects - prod_subjects
        prod_only_subjects = prod_subjects - dev_subjects

        print("📊 Subject distribution:")
        print(f"   Common subjects: {len(common_subjects)}")
        print(f"   DEV-only subjects: {len(dev_only_subjects)}")
        print(f"   PROD-only subjects: {len(prod_only_subjects)}")

        # Record missing subjects as drift
        drift_analysis["missing_in_prod"] = list(dev_only_subjects)
        drift_analysis["missing_in_dev"] = list(prod_only_subjects)

        # Analyze each common subject for drift
        for subject in list(common_subjects)[:5]:  # Analyze first 5 for performance
            print(f"🔍 Analyzing drift for: {subject}")
            drift_analysis["subjects_analyzed"] += 1

            try:
                # Get versions from both registries
                dev_versions_resp = requests.get(
                    f"{dev_url}/subjects/{subject}/versions", timeout=5
                )
                prod_versions_resp = requests.get(
                    f"{prod_url}/subjects/{subject}/versions", timeout=5
                )

                if (
                    dev_versions_resp.status_code == 200
                    and prod_versions_resp.status_code == 200
                ):
                    dev_versions = dev_versions_resp.json()
                    prod_versions = prod_versions_resp.json()

                    # Check for version count drift
                    if len(dev_versions) != len(prod_versions):
                        drift_analysis["version_drifts"].append(
                            {
                                "subject": subject,
                                "dev_versions": len(dev_versions),
                                "prod_versions": len(prod_versions),
                                "drift_magnitude": abs(
                                    len(dev_versions) - len(prod_versions)
                                ),
                            }
                        )
                        print(
                            f"   ⚠️  Version count drift: DEV={len(dev_versions)}, PROD={len(prod_versions)}"
                        )

                    # Compare latest schemas
                    dev_latest_resp = requests.get(
                        f"{dev_url}/subjects/{subject}/versions/latest", timeout=5
                    )
                    prod_latest_resp = requests.get(
                        f"{prod_url}/subjects/{subject}/versions/latest", timeout=5
                    )

                    if (
                        dev_latest_resp.status_code == 200
                        and prod_latest_resp.status_code == 200
                    ):
                        dev_latest = dev_latest_resp.json()
                        prod_latest = prod_latest_resp.json()

                        dev_schema = json.loads(dev_latest["schema"])
                        prod_schema = json.loads(prod_latest["schema"])

                        # Check for schema content drift
                        if dev_schema != prod_schema:
                            # Analyze the type of drift
                            dev_fields = set()
                            prod_fields = set()

                            if (
                                dev_schema.get("type") == "record"
                                and prod_schema.get("type") == "record"
                            ):
                                dev_fields = {
                                    f["name"] for f in dev_schema.get("fields", [])
                                }
                                prod_fields = {
                                    f["name"] for f in prod_schema.get("fields", [])
                                }

                            new_fields = dev_fields - prod_fields
                            removed_fields = prod_fields - dev_fields

                            drift_analysis["schema_drifts"].append(
                                {
                                    "subject": subject,
                                    "dev_version": dev_latest.get("version"),
                                    "prod_version": prod_latest.get("version"),
                                    "new_fields": list(new_fields),
                                    "removed_fields": list(removed_fields),
                                    "field_drift_count": len(new_fields)
                                    + len(removed_fields),
                                }
                            )

                            print("   ⚠️  Schema content drift detected")
                            if new_fields:
                                print(f"      New fields in DEV: {list(new_fields)}")
                            if removed_fields:
                                print(
                                    f"      Removed fields from DEV: {list(removed_fields)}"
                                )
                        else:
                            drift_analysis["identical_subjects"].append(subject)
                            print("   ✅ Schemas identical")

            except Exception as e:
                print(f"   ❌ Failed to analyze {subject}: {e}")

        # Generate drift report
        print("\n📊 Schema Drift Analysis Report")
        print("=" * 50)
        print(f"Analysis timestamp: {datetime.now().isoformat()}")
        print(f"Subjects analyzed: {drift_analysis['subjects_analyzed']}")

        print("\n🔍 Drift Summary:")
        print(f"   Version drifts: {len(drift_analysis['version_drifts'])}")
        print(f"   Schema content drifts: {len(drift_analysis['schema_drifts'])}")
        print(f"   Missing in PROD: {len(drift_analysis['missing_in_prod'])}")
        print(f"   Missing in DEV: {len(drift_analysis['missing_in_dev'])}")
        print(f"   Identical schemas: {len(drift_analysis['identical_subjects'])}")

        # Calculate drift severity
        total_drift_issues = (
            len(drift_analysis["version_drifts"])
            + len(drift_analysis["schema_drifts"])
            + len(drift_analysis["missing_in_prod"])
            + len(drift_analysis["missing_in_dev"])
        )

        total_analyzed = (
            drift_analysis["subjects_analyzed"]
            + len(drift_analysis["missing_in_prod"])
            + len(drift_analysis["missing_in_dev"])
        )

        if total_analyzed > 0:
            drift_percentage = (total_drift_issues / total_analyzed) * 100
            print(f"\n📈 Overall drift level: {drift_percentage:.1f}%")

            if drift_percentage < 10:
                print("   ✅ Low drift - registries are well synchronized")
            elif drift_percentage < 30:
                print("   ⚠️  Moderate drift - consider synchronization")
            else:
                print("   ❌ High drift - immediate attention required")

        # Show detailed drift information
        if drift_analysis["schema_drifts"]:
            print("\n📋 Schema Content Drifts (first 3):")
            for drift in drift_analysis["schema_drifts"][:3]:
                print(
                    f"   • {drift['subject']}: {drift['field_drift_count']} field changes"
                )
                if drift["new_fields"]:
                    print(f"     + New: {drift['new_fields']}")
                if drift["removed_fields"]:
                    print(f"     - Removed: {drift['removed_fields']}")

        if drift_analysis["version_drifts"]:
            print("\n📋 Version Drifts (first 3):")
            for drift in drift_analysis["version_drifts"][:3]:
                print(
                    f"   • {drift['subject']}: DEV={drift['dev_versions']}, PROD={drift['prod_versions']}"
                )

        # Test drift detection algorithms
        print("\n🔍 Testing drift detection algorithms...")

        # Algorithm 1: Field count comparison
        field_drift_subjects = [
            d for d in drift_analysis["schema_drifts"] if d["field_drift_count"] > 0
        ]
        print(f"   Field-based drift detection: {len(field_drift_subjects)} subjects")

        # Algorithm 2: Version lag detection
        version_lag_subjects = [
            d for d in drift_analysis["version_drifts"] if d["drift_magnitude"] > 1
        ]
        print(f"   Version lag detection: {len(version_lag_subjects)} subjects")

        # Algorithm 3: Missing subject detection
        missing_subjects = len(drift_analysis["missing_in_prod"]) + len(
            drift_analysis["missing_in_dev"]
        )
        print(f"   Missing subject detection: {missing_subjects} subjects")

        print("✅ Schema drift detection test completed successfully")
        return True

    except requests.exceptions.Timeout:
        print("❌ Test failed: Request timeout")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_test_schema_drift()
    sys.exit(0 if success else 1)
