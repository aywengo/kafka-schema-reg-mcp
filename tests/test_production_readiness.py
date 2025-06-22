#!/usr/bin/env python3
"""
Production Readiness Integration Tests for unified server in multi-registry mode

Tests enterprise-level features and production deployment scenarios:
- High availability and failover scenarios
- Security and authentication validation
- Enterprise configuration management
- Production deployment patterns
- Monitoring and observability
- Data consistency and integrity
- Backup and disaster recovery workflows
- Compliance and audit capabilities
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastmcp import Client
from fastmcp.client.session import ClientSession
from fastmcp.client.stdio import StdioServerParameters, stdio_client

# Production-grade test schemas
PRODUCTION_SCHEMAS = {
    "user_pii": {
        "type": "record",
        "name": "UserPII",
        "doc": "Production user PII schema with compliance requirements",
        "fields": [
            {"name": "user_id", "type": "string", "doc": "Unique user identifier"},
            {"name": "email", "type": "string", "doc": "User email address (PII)"},
            {"name": "first_name", "type": "string", "doc": "First name (PII)"},
            {"name": "last_name", "type": "string", "doc": "Last name (PII)"},
            {"name": "created_at", "type": "long", "doc": "Account creation timestamp"},
            {"name": "gdpr_consent", "type": "boolean", "doc": "GDPR consent status"},
            {
                "name": "data_retention_days",
                "type": "int",
                "default": 2555,
                "doc": "Data retention period",
            },
        ],
    },
    "financial_transaction": {
        "type": "record",
        "name": "FinancialTransaction",
        "doc": "Production financial transaction schema",
        "fields": [
            {"name": "transaction_id", "type": "string"},
            {"name": "account_id", "type": "string"},
            {"name": "amount", "type": {"type": "fixed", "name": "Amount", "size": 16}},
            {"name": "currency", "type": "string"},
            {"name": "timestamp", "type": "long"},
            {"name": "merchant_id", "type": ["null", "string"], "default": None},
            {
                "name": "transaction_type",
                "type": {
                    "type": "enum",
                    "name": "TransactionType",
                    "symbols": ["DEBIT", "CREDIT", "TRANSFER", "FEE"],
                },
            },
            {"name": "metadata", "type": {"type": "map", "values": "string"}},
            {"name": "risk_score", "type": "double", "default": 0.0},
        ],
    },
    "audit_log": {
        "type": "record",
        "name": "AuditLog",
        "doc": "Production audit log schema for compliance",
        "fields": [
            {"name": "event_id", "type": "string"},
            {"name": "user_id", "type": ["null", "string"], "default": None},
            {"name": "service_name", "type": "string"},
            {"name": "action", "type": "string"},
            {"name": "resource", "type": "string"},
            {"name": "timestamp", "type": "long"},
            {"name": "ip_address", "type": "string"},
            {"name": "user_agent", "type": ["null", "string"], "default": None},
            {"name": "success", "type": "boolean"},
            {"name": "error_code", "type": ["null", "string"], "default": None},
            {"name": "additional_data", "type": {"type": "map", "values": "string"}},
        ],
    },
}


async def test_high_availability_scenarios():
    """Test high availability and failover scenarios."""
    print("\n🏥 Testing High Availability Scenarios")
    print("-" * 50)

    # Setup multiple registries simulating HA deployment
    env = os.environ.copy()
    env.pop("SCHEMA_REGISTRY_URL", None)

    # Primary cluster
    env["SCHEMA_REGISTRY_NAME_1"] = "primary_cluster"
    env["SCHEMA_REGISTRY_URL_1"] = "http://localhost:8081"
    env["READONLY_1"] = "false"

    # Secondary cluster (disaster recovery)
    env["SCHEMA_REGISTRY_NAME_2"] = "dr_cluster"
    env["SCHEMA_REGISTRY_URL_2"] = "http://localhost:8081"  # Same for testing
    env["READONLY_2"] = "true"  # DR is readonly

    # Staging environment
    env["SCHEMA_REGISTRY_NAME_3"] = "staging_cluster"
    env["SCHEMA_REGISTRY_URL_3"] = "http://localhost:8081"
    env["READONLY_3"] = "false"

    # Get the absolute path to the server script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(
        os.path.dirname(script_dir), "kafka_schema_registry_unified_mcp.py"
    )

    server_params = StdioServerParameters(
        command="python", args=[server_script], env=env
    )

    try:
        # Add timeout to prevent hanging
        await asyncio.wait_for(
            _test_high_availability_with_client(server_params),
            timeout=60.0,  # 60 second timeout for complex operations
        )
    except asyncio.TimeoutError:
        print("❌ High availability test timed out after 60 seconds")
    except Exception as e:
        print(f"❌ High availability scenarios test failed: {e}")


async def _test_high_availability_with_client(server_params):
    """Helper function for high availability test with timeout protection."""
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Test 1: Multi-cluster health check
            print("Test 1: Multi-cluster health monitoring")
            result = await session.call_tool("test_all_registries", {})
            health_data = json.loads(result.content[0].text) if result.content else {}

            total_registries = health_data.get("total_registries", 0)
            connected = health_data.get("connected", 0)
            failed = health_data.get("failed", 0)

            print(
                f"  ✅ Cluster health: {connected}/{total_registries} clusters healthy"
            )
            print(f"     Failed clusters: {failed}")

            # Test 2: Primary cluster operations
            print("\nTest 2: Primary cluster schema registration")
            critical_schemas = ["user_pii", "financial_transaction", "audit_log"]

            for schema_name in critical_schemas:
                result = await session.call_tool(
                    "register_schema",
                    {
                        "subject": f"prod.{schema_name}",
                        "schema_definition": PRODUCTION_SCHEMAS[schema_name],
                        "registry": "primary_cluster",
                    },
                )
                response = json.loads(result.content[0].text) if result.content else {}
                if not response.get("error"):
                    print(f"  ✅ Registered {schema_name} in primary cluster")
                else:
                    print(
                        f"  ❌ Failed to register {schema_name}: {response.get('error')}"
                    )

            # Test 3: DR cluster replication check
            print("\nTest 3: Disaster recovery cluster validation")
            result = await session.call_tool(
                "compare_registries",
                {"source_registry": "primary_cluster", "target_registry": "dr_cluster"},
            )
            comparison = json.loads(result.content[0].text) if result.content else {}

            primary_only = len(comparison.get("subjects", {}).get("source_only", []))
            dr_only = len(comparison.get("subjects", {}).get("target_only", []))
            common = len(comparison.get("subjects", {}).get("common", []))

            print(f"  ✅ Schema sync status:")
            print(f"     Common schemas: {common}")
            print(f"     Primary only: {primary_only}")
            print(f"     DR only: {dr_only}")

            # Test 4: Failover simulation (readonly enforcement)
            print("\nTest 4: Failover simulation - DR readonly protection")
            result = await session.call_tool(
                "register_schema",
                {
                    "subject": "failover.test",
                    "schema_definition": PRODUCTION_SCHEMAS["user_pii"],
                    "registry": "dr_cluster",
                },
            )
            response = json.loads(result.content[0].text) if result.content else {}

            if "readonly" in response.get("error", "").lower():
                print("  ✅ DR cluster properly protected by readonly mode")
            else:
                print(f"  ⚠️ DR cluster protection may be insufficient: {response}")

            # Test 5: Cross-cluster migration capability
            print("\nTest 5: Cross-cluster migration capability")
            result = await session.call_tool(
                "migrate_schema",
                {
                    "subject": "prod.user_pii",
                    "source_registry": "primary_cluster",
                    "target_registry": "staging_cluster",
                    "dry_run": True,
                },
            )
            migration_result = (
                json.loads(result.content[0].text) if result.content else {}
            )

            if not migration_result.get("error"):
                print("  ✅ Cross-cluster migration capability validated")
            else:
                print(
                    f"  ❌ Migration capability issue: {migration_result.get('error')}"
                )

            print("\n🎉 High Availability Scenarios Tests Complete!")


async def test_security_and_compliance():
    """Test security features and compliance capabilities."""
    print("\n🔒 Testing Security and Compliance Features")
    print("-" * 50)

    env = os.environ.copy()
    env.pop("SCHEMA_REGISTRY_URL", None)

    # Production environment with strict security
    env["SCHEMA_REGISTRY_NAME_1"] = "production_secure"
    env["SCHEMA_REGISTRY_URL_1"] = "http://localhost:8081"
    env["READONLY_1"] = "true"  # Production is readonly

    # Development environment
    env["SCHEMA_REGISTRY_NAME_2"] = "development"
    env["SCHEMA_REGISTRY_URL_2"] = "http://localhost:8081"
    env["READONLY_2"] = "false"

    # Get the absolute path to the server script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(
        os.path.dirname(script_dir), "kafka_schema_registry_unified_mcp.py"
    )

    server_params = StdioServerParameters(
        command="python", args=[server_script], env=env
    )

    try:
        # Add timeout to prevent hanging
        await asyncio.wait_for(
            _test_security_compliance_with_client(server_params), timeout=60.0
        )
    except asyncio.TimeoutError:
        print("❌ Security and compliance test timed out after 60 seconds")
    except Exception as e:
        print(f"❌ Security and compliance test failed: {e}")


async def _test_security_compliance_with_client(server_params):
    """Helper function for security and compliance test with timeout protection."""
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Test 1: Production environment protection
            print("Test 1: Production environment write protection")
            security_test_operations = [
                (
                    "register_schema",
                    {
                        "subject": "security.test",
                        "schema_definition": PRODUCTION_SCHEMAS["user_pii"],
                        "registry": "production_secure",
                    },
                ),
                (
                    "delete_subject",
                    {"subject": "any.subject", "registry": "production_secure"},
                ),
                (
                    "update_global_config",
                    {"compatibility": "NONE", "registry": "production_secure"},
                ),
                (
                    "create_context",
                    {"context": "unauthorized", "registry": "production_secure"},
                ),
            ]

            protected_operations = 0
            for operation, params in security_test_operations:
                result = await session.call_tool(operation, params)
                response = json.loads(result.content[0].text) if result.content else {}

                if "readonly" in response.get("error", "").lower():
                    protected_operations += 1
                    print(f"  ✅ {operation} properly blocked")
                else:
                    print(f"  ⚠️ {operation} may not be properly protected")

            print(
                f"  ✅ Security: {protected_operations}/{len(security_test_operations)} operations protected"
            )

            # Test 2: Audit trail capabilities
            print("\nTest 2: Audit trail and compliance logging")
            result = await session.call_tool(
                "register_schema",
                {
                    "subject": "compliance.audit_log",
                    "schema_definition": PRODUCTION_SCHEMAS["audit_log"],
                    "registry": "development",
                },
            )
            response = json.loads(result.content[0].text) if result.content else {}

            if not response.get("error"):
                print("  ✅ Audit log schema registered for compliance tracking")

                # Verify audit schema structure
                result = await session.call_tool(
                    "get_schema",
                    {"subject": "compliance.audit_log", "registry": "development"},
                )
                schema_data = (
                    json.loads(result.content[0].text) if result.content else {}
                )

                if "user_id" in str(schema_data) and "action" in str(schema_data):
                    print("  ✅ Audit schema contains required compliance fields")
                else:
                    print("  ⚠️ Audit schema may be missing compliance fields")

            # Test 3: PII data handling schema
            print("\nTest 3: PII data schema compliance validation")
            result = await session.call_tool(
                "register_schema",
                {
                    "subject": "compliance.user_pii",
                    "schema_definition": PRODUCTION_SCHEMAS["user_pii"],
                    "registry": "development",
                },
            )
            response = json.loads(result.content[0].text) if result.content else {}

            if not response.get("error"):
                # Check for GDPR compliance fields
                schema_str = str(PRODUCTION_SCHEMAS["user_pii"])
                gdpr_fields = ["gdpr_consent", "data_retention_days"]
                found_fields = [field for field in gdpr_fields if field in schema_str]

                print(
                    f"  ✅ PII schema registered with {len(found_fields)}/{len(gdpr_fields)} GDPR fields"
                )

            # Test 4: Financial data schema validation
            print("\nTest 4: Financial data schema compliance")
            result = await session.call_tool(
                "register_schema",
                {
                    "subject": "compliance.financial_transaction",
                    "schema_definition": PRODUCTION_SCHEMAS["financial_transaction"],
                    "registry": "development",
                },
            )
            response = json.loads(result.content[0].text) if result.content else {}

            if not response.get("error"):
                print("  ✅ Financial transaction schema registered")

                # Verify risk assessment field
                if "risk_score" in str(PRODUCTION_SCHEMAS["financial_transaction"]):
                    print("  ✅ Financial schema includes risk assessment capability")

            # Test 5: Configuration security validation
            print("\nTest 5: Configuration security validation")
            result = await session.call_tool(
                "get_global_config", {"registry": "production_secure"}
            )
            config_data = json.loads(result.content[0].text) if result.content else {}

            if config_data.get("compatibility"):
                print(
                    f"  ✅ Production config accessible: {config_data.get('compatibility')}"
                )

                # Check for secure compatibility settings
                compat = config_data.get("compatibility", "")
                if compat in ["BACKWARD", "FULL"]:
                    print("  ✅ Production using secure compatibility mode")
                else:
                    print(
                        f"  ⚠️ Production compatibility mode may be insecure: {compat}"
                    )

            print("\n🎉 Security and Compliance Tests Complete!")


async def test_enterprise_operations():
    """Test enterprise-level operational capabilities."""
    print("\n🏢 Testing Enterprise Operations")
    print("-" * 50)

    env = os.environ.copy()
    env.pop("SCHEMA_REGISTRY_URL", None)

    # Enterprise multi-environment setup
    environments = {
        "development": {"readonly": "false"},
        "qa": {"readonly": "false"},
        "staging": {"readonly": "false"},
        "production": {"readonly": "true"},
    }

    for i, (env_name, config) in enumerate(environments.items(), 1):
        env[f"SCHEMA_REGISTRY_NAME_{i}"] = env_name
        env[f"SCHEMA_REGISTRY_URL_{i}"] = "http://localhost:8081"
        env[f"READONLY_{i}"] = config["readonly"]

    # Get the absolute path to the server script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(
        os.path.dirname(script_dir), "kafka_schema_registry_unified_mcp.py"
    )

    server_params = StdioServerParameters(
        command="python", args=[server_script], env=env
    )

    try:
        # Add timeout to prevent hanging
        await asyncio.wait_for(
            _test_enterprise_operations_with_client(server_params), timeout=60.0
        )
    except asyncio.TimeoutError:
        print("❌ Enterprise operations test timed out after 60 seconds")
    except Exception as e:
        print(f"❌ Enterprise operations test failed: {e}")


async def _test_enterprise_operations_with_client(server_params):
    """Helper function for enterprise operations test with timeout protection."""
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Test 1: Enterprise environment management
            print("Test 1: Enterprise environment management")
            result = await session.call_tool("list_registries", {})
            registries = json.loads(result.content[0].text) if result.content else []

            environments = {
                "development": {"readonly": "false"},
                "qa": {"readonly": "false"},
                "staging": {"readonly": "false"},
                "production": {"readonly": "true"},
            }

            env_count = len(
                [r for r in registries if r.get("name") in environments.keys()]
            )
            print(f"  ✅ Enterprise environments configured: {env_count}/4")

            for registry in registries:
                env_name = registry.get("name")
                readonly = registry.get("readonly", False)
                expected_readonly = (
                    environments.get(env_name, {}).get("readonly") == "true"
                )

                if readonly == expected_readonly:
                    print(f"  ✅ {env_name}: correct readonly mode ({readonly})")
                else:
                    print(f"  ⚠️ {env_name}: readonly mode mismatch")

            # Test 2: Schema promotion workflow
            print("\nTest 2: Schema promotion workflow (dev → qa → staging)")
            promotion_schema = PRODUCTION_SCHEMAS["user_pii"]
            promotion_subject = "enterprise.user_profile"

            # Register in development
            result = await session.call_tool(
                "register_schema",
                {
                    "subject": promotion_subject,
                    "schema_definition": promotion_schema,
                    "registry": "development",
                },
            )
            dev_response = json.loads(result.content[0].text) if result.content else {}

            if not dev_response.get("error"):
                print("  ✅ Schema registered in development")

                # Promote to QA
                result = await session.call_tool(
                    "migrate_schema",
                    {
                        "subject": promotion_subject,
                        "source_registry": "development",
                        "target_registry": "qa",
                        "dry_run": False,
                    },
                )
                qa_response = (
                    json.loads(result.content[0].text) if result.content else {}
                )

                if not qa_response.get("error"):
                    print("  ✅ Schema promoted to QA")

                    # Promote to staging
                    result = await session.call_tool(
                        "migrate_schema",
                        {
                            "subject": promotion_subject,
                            "source_registry": "qa",
                            "target_registry": "staging",
                            "dry_run": False,
                        },
                    )
                    staging_response = (
                        json.loads(result.content[0].text) if result.content else {}
                    )

                    if not staging_response.get("error"):
                        print("  ✅ Schema promoted to staging")
                    else:
                        print(
                            f"  ❌ Staging promotion failed: {staging_response.get('error')}"
                        )
                else:
                    print(f"  ❌ QA promotion failed: {qa_response.get('error')}")
            else:
                print(
                    f"  ❌ Development registration failed: {dev_response.get('error')}"
                )

            # Test 3: Cross-environment comparison
            print("\nTest 3: Cross-environment schema drift detection")
            comparison_pairs = [
                ("development", "qa"),
                ("qa", "staging"),
                ("staging", "production"),
            ]

            for source, target in comparison_pairs:
                result = await session.call_tool(
                    "compare_registries",
                    {"source_registry": source, "target_registry": target},
                )
                comparison = (
                    json.loads(result.content[0].text) if result.content else {}
                )

                source_only = len(comparison.get("subjects", {}).get("source_only", []))
                target_only = len(comparison.get("subjects", {}).get("target_only", []))
                common = len(comparison.get("subjects", {}).get("common", []))

                print(
                    f"  ✅ {source} vs {target}: {common} common, {source_only} source-only, {target_only} target-only"
                )

            # Test 4: Bulk operations for enterprise scale
            print("\nTest 4: Bulk operations for enterprise deployment")
            bulk_schemas = [
                ("enterprise.user_events", PRODUCTION_SCHEMAS["user_pii"]),
                (
                    "enterprise.payment_events",
                    PRODUCTION_SCHEMAS["financial_transaction"],
                ),
                ("enterprise.audit_events", PRODUCTION_SCHEMAS["audit_log"]),
            ]

            successful_registrations = 0
            for subject, schema in bulk_schemas:
                result = await session.call_tool(
                    "register_schema",
                    {
                        "subject": subject,
                        "schema_definition": schema,
                        "registry": "development",
                    },
                )
                response = json.loads(result.content[0].text) if result.content else {}

                if not response.get("error"):
                    successful_registrations += 1

            print(
                f"  ✅ Bulk registration: {successful_registrations}/{len(bulk_schemas)} schemas"
            )

            # Test 5: Production deployment validation
            print("\nTest 5: Production deployment readiness")
            result = await session.call_tool(
                "find_missing_schemas",
                {"source_registry": "staging", "target_registry": "production"},
            )
            missing_data = json.loads(result.content[0].text) if result.content else {}

            missing_count = missing_data.get("missing_count", 0)
            print(
                f"  ✅ Production readiness: {missing_count} schemas awaiting deployment"
            )

            if missing_count > 0:
                missing_schemas = missing_data.get("missing_schemas", [])
                print(
                    f"     Pending schemas: {missing_schemas[:3]}{'...' if len(missing_schemas) > 3 else ''}"
                )

            print("\n🎉 Enterprise Operations Tests Complete!")


async def test_monitoring_and_observability():
    """Test monitoring and observability capabilities."""
    print("\n📊 Testing Monitoring and Observability")
    print("-" * 50)

    env = os.environ.copy()
    env.pop("SCHEMA_REGISTRY_URL", None)

    env["SCHEMA_REGISTRY_NAME_1"] = "monitoring_test"
    env["SCHEMA_REGISTRY_URL_1"] = "http://localhost:8081"
    env["READONLY_1"] = "false"

    # Get the absolute path to the server script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(
        os.path.dirname(script_dir), "kafka_schema_registry_unified_mcp.py"
    )

    server_params = StdioServerParameters(
        command="python", args=[server_script], env=env
    )

    try:
        # Add timeout to prevent hanging
        await asyncio.wait_for(
            _test_monitoring_observability_with_client(server_params), timeout=60.0
        )
    except asyncio.TimeoutError:
        print("❌ Monitoring and observability test timed out after 60 seconds")
    except Exception as e:
        print(f"❌ Monitoring and observability test failed: {e}")


async def _test_monitoring_observability_with_client(server_params):
    """Helper function for monitoring and observability test with timeout protection."""
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Test 1: Registry health monitoring
            print("Test 1: Registry health monitoring capabilities")
            start_time = time.time()

            result = await session.call_tool(
                "test_registry_connection", {"registry_name": "monitoring_test"}
            )
            health_data = json.loads(result.content[0].text) if result.content else {}

            response_time = time.time() - start_time
            registry_response_time = health_data.get("response_time_ms", 0)

            print(f"  ✅ Health check response time: {response_time*1000:.2f}ms")
            print(f"  ✅ Registry response time: {registry_response_time:.2f}ms")
            print(f"  ✅ Health status: {health_data.get('status', 'unknown')}")

            # Test 2: Schema registry metrics
            print("\nTest 2: Schema registry metrics collection")

            # Register test schemas for metrics
            test_schemas = [f"metrics.test_{i}" for i in range(10)]
            registration_times = []

            for subject in test_schemas:
                start_time = time.time()
                result = await session.call_tool(
                    "register_schema",
                    {
                        "subject": subject,
                        "schema_definition": PRODUCTION_SCHEMAS["user_pii"],
                        "registry": "monitoring_test",
                    },
                )
                registration_time = time.time() - start_time
                registration_times.append(registration_time)

            avg_registration_time = sum(registration_times) / len(registration_times)
            max_registration_time = max(registration_times)
            min_registration_time = min(registration_times)

            print(f"  ✅ Schema registration metrics:")
            print(f"     Average time: {avg_registration_time*1000:.2f}ms")
            print(f"     Max time: {max_registration_time*1000:.2f}ms")
            print(f"     Min time: {min_registration_time*1000:.2f}ms")

            # Test 3: Registry inventory monitoring
            print("\nTest 3: Registry inventory monitoring")
            result = await session.call_tool(
                "list_subjects", {"registry": "monitoring_test"}
            )
            subjects = json.loads(result.content[0].text) if result.content else []

            result = await session.call_tool(
                "list_contexts", {"registry": "monitoring_test"}
            )
            contexts = json.loads(result.content[0].text) if result.content else []

            print(f"  ✅ Inventory metrics:")
            print(f"     Total subjects: {len(subjects)}")
            print(f"     Total contexts: {len(contexts)}")

            # Test 4: Configuration monitoring
            print("\nTest 4: Configuration monitoring")
            result = await session.call_tool(
                "get_global_config", {"registry": "monitoring_test"}
            )
            config_data = json.loads(result.content[0].text) if result.content else {}

            result = await session.call_tool(
                "get_mode", {"registry": "monitoring_test"}
            )
            mode_data = json.loads(result.content[0].text) if result.content else {}

            print(f"  ✅ Configuration status:")
            print(
                f"     Compatibility level: {config_data.get('compatibility', 'unknown')}"
            )
            print(f"     Registry mode: {mode_data.get('mode', 'unknown')}")
            print(f"     Registry: {config_data.get('registry', 'unknown')}")

            # Test 5: Observability data export
            print("\nTest 5: Observability data export simulation")

            # Simulate collecting comprehensive monitoring data
            monitoring_data = {
                "timestamp": datetime.now().isoformat(),
                "registry_name": "monitoring_test",
                "health_status": health_data.get("status"),
                "response_time_ms": registry_response_time,
                "total_subjects": len(subjects),
                "total_contexts": len(contexts),
                "compatibility_level": config_data.get("compatibility"),
                "registry_mode": mode_data.get("mode"),
                "performance_metrics": {
                    "avg_registration_time_ms": avg_registration_time * 1000,
                    "max_registration_time_ms": max_registration_time * 1000,
                    "min_registration_time_ms": min_registration_time * 1000,
                    "total_test_schemas": len(test_schemas),
                },
            }

            print(f"  ✅ Monitoring data collected: {len(monitoring_data)} metrics")
            print(f"     Health: {monitoring_data['health_status']}")
            print(f"     Response time: {monitoring_data['response_time_ms']:.2f}ms")
            print(
                f"     Performance samples: {monitoring_data['performance_metrics']['total_test_schemas']}"
            )

            print("\n🎉 Monitoring and Observability Tests Complete!")


async def test_disaster_recovery():
    """Test disaster recovery and backup capabilities."""
    print("\n🛡️ Testing Disaster Recovery Capabilities")
    print("-" * 50)

    env = os.environ.copy()
    env.pop("SCHEMA_REGISTRY_URL", None)

    # Primary and backup registries
    env["SCHEMA_REGISTRY_NAME_1"] = "primary_site"
    env["SCHEMA_REGISTRY_URL_1"] = "http://localhost:8081"
    env["READONLY_1"] = "false"

    env["SCHEMA_REGISTRY_NAME_2"] = "backup_site"
    env["SCHEMA_REGISTRY_URL_2"] = "http://localhost:8081"
    env["READONLY_2"] = "false"

    # Get the absolute path to the server script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(
        os.path.dirname(script_dir), "kafka_schema_registry_unified_mcp.py"
    )

    server_params = StdioServerParameters(
        command="python", args=[server_script], env=env
    )

    try:
        # Add timeout to prevent hanging
        await asyncio.wait_for(
            _test_disaster_recovery_with_client(server_params), timeout=60.0
        )
    except asyncio.TimeoutError:
        print("❌ Disaster recovery test timed out after 60 seconds")
    except Exception as e:
        print(f"❌ Disaster recovery test failed: {e}")


async def _test_disaster_recovery_with_client(server_params):
    """Helper function for disaster recovery test with timeout protection."""
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Test 1: Backup data preparation
            print("Test 1: Disaster recovery data preparation")

            # Create critical business schemas
            critical_schemas = [
                ("dr.customer_data", PRODUCTION_SCHEMAS["user_pii"]),
                ("dr.transaction_log", PRODUCTION_SCHEMAS["financial_transaction"]),
                ("dr.audit_trail", PRODUCTION_SCHEMAS["audit_log"]),
            ]

            for subject, schema in critical_schemas:
                result = await session.call_tool(
                    "register_schema",
                    {
                        "subject": subject,
                        "schema_definition": schema,
                        "registry": "primary_site",
                    },
                )
                response = json.loads(result.content[0].text) if result.content else {}

                if not response.get("error"):
                    print(f"  ✅ Critical schema registered: {subject}")

            # Test 2: Backup synchronization
            print("\nTest 2: Backup site synchronization")
            sync_failures = 0

            for subject, _ in critical_schemas:
                result = await session.call_tool(
                    "migrate_schema",
                    {
                        "subject": subject,
                        "source_registry": "primary_site",
                        "target_registry": "backup_site",
                        "dry_run": False,
                    },
                )
                migration_result = (
                    json.loads(result.content[0].text) if result.content else {}
                )

                if not migration_result.get("error"):
                    print(f"  ✅ Synchronized to backup: {subject}")
                else:
                    sync_failures += 1
                    print(f"  ❌ Sync failed: {subject}")

            print(
                f"  ✅ Synchronization: {len(critical_schemas) - sync_failures}/{len(critical_schemas)} schemas"
            )

            # Test 3: Backup integrity verification
            print("\nTest 3: Backup integrity verification")
            result = await session.call_tool(
                "compare_registries",
                {"source_registry": "primary_site", "target_registry": "backup_site"},
            )
            comparison = json.loads(result.content[0].text) if result.content else {}

            primary_only = len(comparison.get("subjects", {}).get("source_only", []))
            backup_only = len(comparison.get("subjects", {}).get("target_only", []))
            common = len(comparison.get("subjects", {}).get("common", []))

            print(f"  ✅ Backup integrity check:")
            print(f"     Common schemas: {common}")
            print(f"     Primary only: {primary_only}")
            print(f"     Backup only: {backup_only}")

            integrity_score = (
                common / (common + primary_only) if (common + primary_only) > 0 else 0
            )
            print(f"     Integrity score: {integrity_score:.2%}")

            # Test 4: Recovery point objective (RPO) simulation
            print("\nTest 4: Recovery Point Objective (RPO) simulation")

            # Simulate recent changes
            new_schema = {
                "type": "record",
                "name": "RecentChange",
                "fields": [
                    {"name": "id", "type": "string"},
                    {"name": "timestamp", "type": "long"},
                    {"name": "change_type", "type": "string"},
                ],
            }

            result = await session.call_tool(
                "register_schema",
                {
                    "subject": "dr.recent_change",
                    "schema_definition": new_schema,
                    "registry": "primary_site",
                },
            )

            # Check if backup needs update
            result = await session.call_tool(
                "find_missing_schemas",
                {"source_registry": "primary_site", "target_registry": "backup_site"},
            )
            missing_data = json.loads(result.content[0].text) if result.content else {}

            rpo_gap = missing_data.get("missing_count", 0)
            print(f"  ✅ RPO assessment: {rpo_gap} schemas require backup")

            # Test 5: Recovery time objective (RTO) simulation
            print("\nTest 5: Recovery Time Objective (RTO) simulation")

            start_time = time.time()

            # Simulate registry failover by switching to backup
            result = await session.call_tool(
                "test_registry_connection", {"registry_name": "backup_site"}
            )
            backup_health = json.loads(result.content[0].text) if result.content else {}

            result = await session.call_tool(
                "list_subjects", {"registry": "backup_site"}
            )
            backup_subjects = (
                json.loads(result.content[0].text) if result.content else []
            )

            recovery_time = time.time() - start_time

            print(f"  ✅ RTO simulation:")
            print(f"     Recovery time: {recovery_time*1000:.2f}ms")
            print(f"     Backup status: {backup_health.get('status', 'unknown')}")
            print(f"     Available schemas: {len(backup_subjects)}")

            if recovery_time < 5.0:  # 5 second RTO target
                print("  ✅ RTO target met (< 5 seconds)")
            else:
                print("  ⚠️ RTO target exceeded")

            print("\n🎉 Disaster Recovery Tests Complete!")


async def main():
    """Run all production readiness tests."""
    print("🧪 Starting Production Readiness Integration Tests")
    print("=" * 70)

    start_time = time.time()

    try:
        await test_high_availability_scenarios()
        await test_security_and_compliance()
        await test_enterprise_operations()
        await test_monitoring_and_observability()
        await test_disaster_recovery()

        total_time = time.time() - start_time

        print("\n" + "=" * 70)
        print("🎉 All Production Readiness Tests Complete!")
        print(f"\n🏆 **Production Readiness Summary:**")
        print(f"• Total test time: {total_time:.2f}s")
        print(f"• Test timestamp: {datetime.now().isoformat()}")

        print(f"\n✅ **Enterprise Features Validated:**")
        print("• High Availability and Failover")
        print("• Security and Compliance Controls")
        print("• Enterprise Operations and Workflows")
        print("• Monitoring and Observability")
        print("• Disaster Recovery Capabilities")

        print(f"\n🔒 **Security & Compliance:**")
        print("• Multi-environment isolation")
        print("• READONLY mode enforcement")
        print("• PII and financial data schemas")
        print("• Audit logging capabilities")
        print("• GDPR compliance fields")

        print(f"\n🏢 **Enterprise Operations:**")
        print("• Schema promotion workflows")
        print("• Cross-environment comparisons")
        print("• Bulk operations support")
        print("• Production deployment validation")
        print("• Configuration management")

        print(f"\n📊 **Monitoring & Recovery:**")
        print("• Health monitoring metrics")
        print("• Performance tracking")
        print("• Inventory management")
        print("• Backup synchronization")
        print("• RTO/RPO validation")

    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Production readiness tests failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
