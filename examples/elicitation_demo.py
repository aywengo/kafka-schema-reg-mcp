#!/usr/bin/env python3
"""
Elicitation Demo Script

Demonstrates the interactive workflow capabilities of the Kafka Schema Registry
MCP server using the MCP 2025-06-18 elicitation specification.

This script shows practical examples of:
- Interactive schema registration
- Migration preference collection
- Compatibility resolution
- Context metadata elicitation
- Export format selection

Run this script to see elicitation in action!
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Demo configuration
DEMO_REGISTRY_URL = os.getenv("DEMO_REGISTRY_URL", "http://localhost:8081")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")


class ElicitationDemo:
    """Demo class showing elicitation capabilities."""

    def __init__(self):
        self.demo_results = []

    async def run_all_demos(self):
        """Run all elicitation demos."""
        print("\n🎭 Kafka Schema Registry MCP - Elicitation Demo")
        print("=" * 60)
        print("This demo shows interactive workflow capabilities")
        print("using the MCP 2025-06-18 elicitation specification.\n")

        demos = [
            ("Interactive Schema Registration", self.demo_schema_registration),
            ("Migration Preference Collection", self.demo_migration_preferences),
            ("Compatibility Resolution", self.demo_compatibility_resolution),
            ("Context Metadata Elicitation", self.demo_context_metadata),
            ("Export Format Selection", self.demo_export_preferences),
            ("Elicitation Management", self.demo_elicitation_management),
        ]

        for name, demo_func in demos:
            print(f"\n🚀 Demo: {name}")
            print("-" * 40)

            try:
                result = await demo_func()
                self.demo_results.append(
                    {
                        "demo": name,
                        "status": "success",
                        "result": result,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
                print(f"✅ {name} completed successfully")

            except Exception as e:
                logger.error(f"Demo {name} failed: {str(e)}")
                self.demo_results.append(
                    {
                        "demo": name,
                        "status": "failed",
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
                print(f"❌ {name} failed: {str(e)}")

        await self.print_summary()

    async def demo_schema_registration(self) -> Dict[str, Any]:
        """Demo interactive schema registration."""
        print("Registering a new schema with interactive field definition...")

        # Simulate calling the interactive tool with incomplete schema
        print("📝 Simulating incomplete schema (missing field definitions)")

        incomplete_schema = {
            "type": "record",
            "name": "UserEvent",
            "namespace": "com.example.events",
            "fields": [],  # Empty - will trigger elicitation
        }

        print(f"Initial schema: {json.dumps(incomplete_schema, indent=2)}")

        # Simulate elicitation responses (in real use, user would provide these)
        simulated_responses = [
            {
                "field_name": "user_id",
                "field_type": "string",
                "nullable": "false",
                "documentation": "Unique identifier for the user",
            },
            {
                "field_name": "event_type",
                "field_type": "string",
                "nullable": "false",
                "documentation": "Type of event (login, logout, action)",
            },
            {
                "field_name": "timestamp",
                "field_type": "long",
                "nullable": "false",
                "documentation": "Event timestamp in milliseconds",
            },
            {
                "field_name": "metadata",
                "field_type": "string",
                "nullable": "true",
                "default_value": "null",
                "documentation": "Optional event metadata as JSON string",
            },
        ]

        print("\n🤔 Elicitation would ask for:")
        for i, response in enumerate(simulated_responses, 1):
            print(f"  Field {i}:")
            print(f"    Name: {response['field_name']}")
            print(f"    Type: {response['field_type']}")
            print(f"    Nullable: {response['nullable']}")
            print(f"    Documentation: {response['documentation']}")

        # Build the complete schema from responses
        complete_schema = await self._build_complete_schema(incomplete_schema, simulated_responses)

        print("\n✨ Complete schema built from elicitation:")
        print(json.dumps(complete_schema, indent=2))

        return {
            "subject": "user-events-demo",
            "initial_schema": incomplete_schema,
            "elicited_responses": simulated_responses,
            "final_schema": complete_schema,
            "elicitation_used": True,
        }

    async def demo_migration_preferences(self) -> Dict[str, Any]:
        """Demo migration preference collection."""
        print("Configuring context migration with preference elicitation...")

        print("📋 Migration scenario: staging → production")
        print("Missing preferences will be elicited from user")

        # Simulate elicitation for migration preferences
        simulated_preferences = {
            "preserve_ids": "true",
            "migrate_all_versions": "false",
            "conflict_resolution": "prompt",
            "batch_size": "10",
            "dry_run": "true",
        }

        print("\n🤔 Elicitation would ask for:")
        questions = [
            (
                "Preserve Schema IDs",
                "preserve_ids",
                "Keep original schema IDs during migration?",
            ),
            (
                "Migrate All Versions",
                "migrate_all_versions",
                "Include all schema versions or just latest?",
            ),
            (
                "Conflict Resolution",
                "conflict_resolution",
                "How to handle conflicts? (skip/overwrite/merge/prompt)",
            ),
            ("Batch Size", "batch_size", "Number of schemas per batch (1-100)"),
            ("Dry Run", "dry_run", "Preview changes before applying?"),
        ]

        for question, key, description in questions:
            print(f"  {question}: {description}")
            print(f"    Response: {simulated_preferences[key]}")

        migration_config = {
            "source_registry": "staging",
            "target_registry": "production",
            "context": "user-service",
            **{k: v == "true" if v in ["true", "false"] else v for k, v in simulated_preferences.items()},
        }

        print("\n✨ Migration configured with elicited preferences:")
        print(json.dumps(migration_config, indent=2))

        return {
            "migration_config": migration_config,
            "elicited_preferences": simulated_preferences,
            "elicitation_used": True,
        }

    async def demo_compatibility_resolution(self) -> Dict[str, Any]:
        """Demo compatibility issue resolution."""
        print("Resolving schema compatibility issues with guidance...")

        # Simulate compatibility errors
        compatibility_errors = [
            "Field 'age' was removed (breaking change)",
            "Field 'email' type changed from string to int (incompatible)",
            "Required field 'user_id' made optional (forward incompatible)",
        ]

        print("⚠️  Compatibility issues detected:")
        for error in compatibility_errors:
            print(f"    • {error}")

        # Simulate resolution guidance elicitation
        resolution_guidance = {
            "resolution_strategy": "modify_schema",
            "compatibility_level": "FORWARD",
            "notes": "Add default values to removed fields, revert type changes",
        }

        print("\n🤔 Elicitation would ask for resolution strategy:")
        print(f"  Strategy: {resolution_guidance['resolution_strategy']}")
        print(f"  Compatibility Level: {resolution_guidance['compatibility_level']}")
        print(f"  Notes: {resolution_guidance['notes']}")

        print("\n✨ Resolution plan generated:")
        resolution_plan = {
            "strategy": resolution_guidance["resolution_strategy"],
            "recommended_changes": [
                "Add default value for 'age' field",
                "Revert 'email' field type to string",
                "Make 'user_id' required with migration strategy",
            ],
            "new_compatibility_level": resolution_guidance["compatibility_level"],
            "migration_notes": resolution_guidance["notes"],
        }

        print(json.dumps(resolution_plan, indent=2))

        return {
            "compatibility_errors": compatibility_errors,
            "resolution_guidance": resolution_guidance,
            "resolution_plan": resolution_plan,
            "elicitation_used": True,
        }

    async def demo_context_metadata(self) -> Dict[str, Any]:
        """Demo context metadata elicitation."""
        print("Creating context with metadata collection...")

        context_name = "payment-processing"
        print(f"📝 Creating context: {context_name}")

        # Simulate metadata elicitation
        metadata_responses = {
            "description": "Payment processing service schemas",
            "owner": "payments-team",
            "environment": "production",
            "tags": "payments,transactions,billing,pci-compliant",
        }

        print("\n🤔 Elicitation would collect metadata:")
        print(f"  Description: {metadata_responses['description']}")
        print(f"  Owner: {metadata_responses['owner']}")
        print(f"  Environment: {metadata_responses['environment']}")
        print(f"  Tags: {metadata_responses['tags']}")

        # Process metadata
        processed_metadata = {
            "context": context_name,
            "description": metadata_responses["description"],
            "owner": metadata_responses["owner"],
            "environment": metadata_responses["environment"],
            "tags": metadata_responses["tags"].split(","),
            "created_at": datetime.utcnow().isoformat(),
            "metadata_source": "elicitation",
        }

        print("\n✨ Context created with rich metadata:")
        print(json.dumps(processed_metadata, indent=2))

        return {
            "context_name": context_name,
            "elicited_metadata": metadata_responses,
            "processed_metadata": processed_metadata,
            "elicitation_used": True,
        }

    async def demo_export_preferences(self) -> Dict[str, Any]:
        """Demo export format preference selection."""
        print("Configuring global export with format preferences...")

        # Simulate export preference elicitation
        export_preferences = {
            "format": "yaml",
            "include_metadata": "true",
            "include_versions": "latest",
            "compression": "gzip",
        }

        print("\n🤔 Elicitation would ask for export preferences:")
        print(f"  Format: {export_preferences['format']} (json/yaml/avro_idl/csv)")
        print(f"  Include Metadata: {export_preferences['include_metadata']}")
        print(f"  Version Selection: {export_preferences['include_versions']} (latest/all/specific)")
        print(f"  Compression: {export_preferences['compression']} (none/gzip/zip)")

        export_config = {
            "registry": "production",
            "format": export_preferences["format"],
            "include_metadata": export_preferences["include_metadata"] == "true",
            "include_config": True,
            "include_versions": export_preferences["include_versions"],
            "compression": export_preferences["compression"],
            "export_timestamp": datetime.utcnow().isoformat(),
        }

        print("\n✨ Export configured with preferences:")
        print(json.dumps(export_config, indent=2))

        return {
            "export_config": export_config,
            "elicited_preferences": export_preferences,
            "elicitation_used": True,
        }

    async def demo_elicitation_management(self) -> Dict[str, Any]:
        """Demo elicitation management capabilities."""
        print("Demonstrating elicitation management tools...")

        # Simulate elicitation status
        elicitation_status = {
            "elicitation_supported": True,
            "total_pending_requests": 2,
            "request_details": [
                {
                    "id": "req-123",
                    "title": "Define Schema Field",
                    "type": "form",
                    "priority": "medium",
                    "created_at": datetime.utcnow().isoformat(),
                    "expired": False,
                },
                {
                    "id": "req-456",
                    "title": "Migration Preferences",
                    "type": "form",
                    "priority": "high",
                    "created_at": datetime.utcnow().isoformat(),
                    "expired": False,
                },
            ],
            "mcp_protocol_version": "2025-06-18",
        }

        print("📊 Current elicitation status:")
        print(f"  Supported: {elicitation_status['elicitation_supported']}")
        print(f"  Pending Requests: {elicitation_status['total_pending_requests']}")

        for req in elicitation_status["request_details"]:
            print(f"    • {req['id']}: {req['title']} ({req['priority']} priority)")

        # Simulate management operations
        management_ops = [
            "list_elicitation_requests - View all pending requests",
            "get_elicitation_request - Get detailed request info",
            "cancel_elicitation_request - Cancel pending request",
            "submit_elicitation_response - Submit response programmatically",
        ]

        print("\n🛠️  Available management operations:")
        for op in management_ops:
            print(f"    • {op}")

        return {
            "elicitation_status": elicitation_status,
            "management_capabilities": management_ops,
            "demonstration": "complete",
        }

    async def _build_complete_schema(self, base_schema: Dict, field_responses: list) -> Dict:
        """Build complete Avro schema from elicitation responses."""
        schema = base_schema.copy()
        schema["fields"] = []

        for response in field_responses:
            field_def = {"name": response["field_name"], "type": response["field_type"]}

            # Handle nullable fields
            if response.get("nullable") == "true":
                field_def["type"] = ["null", field_def["type"]]
                if response.get("default_value"):
                    field_def["default"] = None
            elif response.get("default_value") and response["default_value"] != "null":
                # Add default value for non-nullable fields
                default_val = response["default_value"]
                if response["field_type"] in ["int", "long"]:
                    try:
                        default_val = int(default_val)
                    except ValueError:
                        pass
                elif response["field_type"] in ["float", "double"]:
                    try:
                        default_val = float(default_val)
                    except ValueError:
                        pass
                elif response["field_type"] == "boolean":
                    default_val = default_val.lower() in ["true", "1", "yes"]

                field_def["default"] = default_val

            # Add documentation
            if response.get("documentation"):
                field_def["doc"] = response["documentation"]

            schema["fields"].append(field_def)

        return schema

    async def print_summary(self):
        """Print demo summary."""
        print("\n" + "=" * 60)
        print("🎉 Elicitation Demo Summary")
        print("=" * 60)

        total_demos = len(self.demo_results)
        successful = len([r for r in self.demo_results if r["status"] == "success"])
        failed = total_demos - successful

        print(f"Total Demos: {total_demos}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(successful/total_demos)*100:.1f}%")

        if failed > 0:
            print("\n❌ Failed Demos:")
            for result in self.demo_results:
                if result["status"] == "failed":
                    print(f"  • {result['demo']}: {result['error']}")

        print("\n📋 Key Takeaways:")
        print("  • Elicitation enables interactive, guided workflows")
        print("  • Graceful fallbacks ensure compatibility with all MCP clients")
        print("  • 5 priority tools support interactive operation")
        print("  • Rich management API for monitoring and control")
        print("  • MCP 2025-06-18 compliant implementation")

        print("\n🔗 Next Steps:")
        print("  • Try the interactive tools with a real MCP client")
        print("  • Implement custom elicitation UI in your client")
        print("  • Explore the management APIs for workflow automation")
        print("  • Read the full elicitation guide in docs/elicitation-guide.md")

        # Save detailed results
        summary_file = f"elicitation_demo_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, "w") as f:
            json.dump(
                {
                    "demo_summary": {
                        "total_demos": total_demos,
                        "successful": successful,
                        "failed": failed,
                        "success_rate": f"{(successful/total_demos)*100:.1f}%",
                    },
                    "results": self.demo_results,
                    "timestamp": datetime.utcnow().isoformat(),
                },
                f,
                indent=2,
            )

        print(f"\n💾 Detailed results saved to: {summary_file}")


async def main():
    """Main demo function."""
    demo = ElicitationDemo()
    await demo.run_all_demos()


if __name__ == "__main__":
    asyncio.run(main())
