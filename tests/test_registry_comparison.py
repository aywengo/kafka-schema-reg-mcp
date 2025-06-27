#!/usr/bin/env python3
"""
Full registry comparison DEV vs PROD

Tests comprehensive comparison of schemas, subjects, and versions between registries.
"""

import sys

import requests


def test_test_registry_comparison():
    """Full registry comparison DEV vs PROD"""

    # DEV Schema Registry
    dev_url = "http://localhost:38081"

    # PROD Schema Registry
    prod_url = "http://localhost:38082"

    print("🧪 Starting registry comparison test...")

    try:
        # Check connectivity
        dev_response = requests.get(f"{dev_url}/subjects", timeout=5)
        prod_response = requests.get(f"{prod_url}/subjects", timeout=5)

        if dev_response.status_code != 200 or prod_response.status_code != 200:
            print("❌ Registry connectivity failed")
            return False

        print("✅ Both registries are accessible")

        # Get subjects from both registries
        dev_subjects = set(dev_response.json())
        prod_subjects = set(prod_response.json())

        print("📊 Registry statistics:")
        print(f"   DEV subjects: {len(dev_subjects)}")
        print(f"   PROD subjects: {len(prod_subjects)}")

        # Find differences
        dev_only = dev_subjects - prod_subjects
        prod_only = prod_subjects - dev_subjects
        common_subjects = dev_subjects & prod_subjects

        print("🔍 Comparison results:")
        print(f"   Common subjects: {len(common_subjects)}")
        print(f"   DEV-only subjects: {len(dev_only)}")
        print(f"   PROD-only subjects: {len(prod_only)}")

        if dev_only:
            print(f"   📋 DEV-only: {list(dev_only)[:5]}{'...' if len(dev_only) > 5 else ''}")

        if prod_only:
            print(f"   📋 PROD-only: {list(prod_only)[:5]}{'...' if len(prod_only) > 5 else ''}")

        # Compare common subjects in detail
        schema_differences = []
        version_differences = []

        for subject in list(common_subjects)[:10]:  # Limit to first 10 for performance
            print(f"🔍 Comparing subject: {subject}")

            try:
                # Get versions from both registries
                dev_versions_resp = requests.get(f"{dev_url}/subjects/{subject}/versions", timeout=5)
                prod_versions_resp = requests.get(f"{prod_url}/subjects/{subject}/versions", timeout=5)

                if dev_versions_resp.status_code == 200 and prod_versions_resp.status_code == 200:
                    dev_versions = dev_versions_resp.json()
                    prod_versions = prod_versions_resp.json()

                    if len(dev_versions) != len(prod_versions):
                        version_differences.append(
                            {
                                "subject": subject,
                                "dev_versions": len(dev_versions),
                                "prod_versions": len(prod_versions),
                            }
                        )
                        print(f"   ⚠️  Version count differs: DEV={len(dev_versions)}, PROD={len(prod_versions)}")

                    # Compare latest versions
                    dev_latest_resp = requests.get(f"{dev_url}/subjects/{subject}/versions/latest", timeout=5)
                    prod_latest_resp = requests.get(f"{prod_url}/subjects/{subject}/versions/latest", timeout=5)

                    if dev_latest_resp.status_code == 200 and prod_latest_resp.status_code == 200:
                        dev_latest = dev_latest_resp.json()
                        prod_latest = prod_latest_resp.json()

                        if dev_latest.get("schema") != prod_latest.get("schema"):
                            schema_differences.append(
                                {
                                    "subject": subject,
                                    "dev_version": dev_latest.get("version"),
                                    "prod_version": prod_latest.get("version"),
                                    "dev_id": dev_latest.get("id"),
                                    "prod_id": prod_latest.get("id"),
                                }
                            )
                            print(
                                f"   ⚠️  Schema differs: DEV v{dev_latest.get('version')} vs PROD v{prod_latest.get('version')}"
                            )
                        else:
                            print(f"   ✅ Schema identical: v{dev_latest.get('version')}")

            except Exception as e:
                print(f"   ❌ Failed to compare {subject}: {e}")

        # Summary of differences
        print("\n📊 Detailed comparison summary:")
        print(f"   Schema differences: {len(schema_differences)}")
        print(f"   Version differences: {len(version_differences)}")

        if schema_differences:
            print("   📋 Subjects with schema differences:")
            for diff in schema_differences[:3]:
                print(f"      • {diff['subject']}: DEV v{diff['dev_version']} ≠ PROD v{diff['prod_version']}")

        if version_differences:
            print("   📋 Subjects with version count differences:")
            for diff in version_differences[:3]:
                print(
                    f"      • {diff['subject']}: DEV={diff['dev_versions']} versions, PROD={diff['prod_versions']} versions"
                )

        # Test registry metadata comparison
        print("\n🔍 Comparing registry metadata...")

        # Get compatibility levels
        try:
            dev_config_resp = requests.get(f"{dev_url}/config", timeout=5)
            prod_config_resp = requests.get(f"{prod_url}/config", timeout=5)

            if dev_config_resp.status_code == 200 and prod_config_resp.status_code == 200:
                dev_config = dev_config_resp.json()
                prod_config = prod_config_resp.json()

                dev_compat = dev_config.get("compatibilityLevel", "UNKNOWN")
                prod_compat = prod_config.get("compatibilityLevel", "UNKNOWN")

                print(f"   DEV compatibility: {dev_compat}")
                print(f"   PROD compatibility: {prod_compat}")

                if dev_compat != prod_compat:
                    print("   ⚠️  Compatibility levels differ!")
                else:
                    print("   ✅ Compatibility levels match")

        except Exception as e:
            print(f"   ⚠️  Could not compare metadata: {e}")

        # Generate comparison score
        total_subjects = len(dev_subjects | prod_subjects)
        if total_subjects > 0:
            common_percentage = (len(common_subjects) / total_subjects) * 100
            print(f"\n📈 Registry similarity: {common_percentage:.1f}%")

            if common_percentage >= 80:
                print("   ✅ Registries are highly similar")
            elif common_percentage >= 50:
                print("   ⚠️  Registries have moderate differences")
            else:
                print("   ❌ Registries are significantly different")

        print("✅ Registry comparison test completed successfully")
        return True

    except requests.exceptions.Timeout:
        print("❌ Test failed: Request timeout")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_normalize_subject():
    from comparison_tools import normalize_subject

    # Test default context (should not change)
    assert normalize_subject("user-value", ".") == "user-value"
    # Test context-prefixed subject
    assert normalize_subject(":.test1:user-value", "test1") == "user-value"
    # Test context-prefixed subject with different context
    assert normalize_subject(":.otherctx:user-value", "otherctx") == "user-value"
    # Test subject that does not match context prefix
    assert normalize_subject("user-value", "test1") == "user-value"
    # Test subject with similar but not exact prefix
    assert normalize_subject(":test1:user-value", "test1") == ":test1:user-value"


def test_context_aware_subject_comparison():
    from comparison_tools import normalize_subject

    # Simulate subjects in two contexts
    source_context = "."
    target_context = "test1"
    source_subjects = ["user-value", "order-value"]
    target_subjects = [":.test1:user-value", ":.test1:product-value"]

    normalized_source = {normalize_subject(s, source_context) for s in source_subjects}
    normalized_target = {normalize_subject(s, target_context) for s in target_subjects}

    # user-value should be common, order-value only in source, product-value only in target
    common = normalized_source & normalized_target
    source_only = normalized_source - normalized_target
    target_only = normalized_target - normalized_source

    assert "user-value" in common
    assert "order-value" in source_only
    assert "product-value" in target_only


if __name__ == "__main__":
    success = test_test_registry_comparison()
    sys.exit(0 if success else 1)
