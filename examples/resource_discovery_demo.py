#!/usr/bin/env python3
"""
Resource Discovery Demo

This script demonstrates how to use the new resource discovery tools
to help clients migrate from tools to resources.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure environment
os.environ["SCHEMA_REGISTRY_URL"] = "http://localhost:8081"
os.environ["SLIM_MODE"] = "true"


async def demo_resource_discovery():
    """Demonstrate resource discovery tools."""

    print("🔍 Resource Discovery Demo")
    print("=" * 50)

    # Import the MCP tools functions directly for demo
    from kafka_schema_registry_unified_mcp import (
        list_available_resources,
        suggest_resource_for_tool,
        generate_resource_templates,
    )

    # Demo 1: List all available resources
    print("\n1️⃣ Listing all available resources:")
    print("-" * 30)

    try:
        result = list_available_resources()
        resources = result.get("available_resources", {})

        print(f"📋 Found {result.get('total_resources', 0)} resources total")

        # Show registry resources
        registry_resources = resources.get("registry_resources", {})
        print(f"\n🏢 Registry Resources ({len(registry_resources)}):")
        for uri, info in registry_resources.items():
            print(f"   • {uri}")
            print(f"     └─ {info['description']}")
            if info.get("replaces_tool"):
                print(f"     └─ Replaces: {info['replaces_tool']}")

        # Show schema resources
        schema_resources = resources.get("schema_resources", {})
        print(f"\n📄 Schema Resources ({len(schema_resources)}):")
        for uri, info in schema_resources.items():
            print(f"   • {uri}")
            print(f"     └─ {info['description']}")

    except Exception as e:
        print(f"❌ Error: {e}")

    # Demo 2: Get migration suggestions for specific tools
    print("\n2️⃣ Getting migration suggestions:")
    print("-" * 30)

    removed_tools = ["list_subjects", "list_registries", "get_schema", "get_mode"]

    for tool in removed_tools:
        try:
            suggestion = suggest_resource_for_tool(tool)

            if suggestion.get("status") == "migrated_to_resource":
                print(f"\n🔄 {tool}:")
                print(f"   Status: {suggestion['status']}")
                print(f"   Use Resource: {suggestion['suggested_resource']}")
                print(f"   Example: {suggestion['example_uri']}")
                print("   Benefits:")
                for benefit in suggestion.get("benefits", []):
                    print(f"     • {benefit}")
            else:
                print(f"\n✅ {tool}: {suggestion.get('message', 'Still available')}")

        except Exception as e:
            print(f"❌ Error getting suggestion for {tool}: {e}")

    # Demo 3: Generate resource templates
    print("\n3️⃣ Generating resource templates:")
    print("-" * 30)

    try:
        templates = generate_resource_templates(registry_name="production", context="users", subject="user-events")

        template_data = templates.get("templates", {})
        config = templates.get("configuration", {})

        print(f"🎯 Templates for configuration:")
        print(f"   Registry: {config.get('registry_name')}")
        print(f"   Context: {config.get('context')}")
        print(f"   Subject: {config.get('subject')}")
        print(f"   Mode: {config.get('registry_mode')}")

        # Show registry templates
        registry_templates = template_data.get("registry_resources", {})
        print(f"\n🏢 Registry Resource Templates:")
        for purpose, uri in registry_templates.items():
            print(f"   • {purpose}: {uri}")

        # Show schema templates
        schema_templates = template_data.get("schema_resources", {})
        print(f"\n📄 Schema Resource Templates:")
        for purpose, uri in schema_templates.items():
            print(f"   • {purpose}: {uri}")

        # Show usage example
        usage_examples = template_data.get("usage_examples", {})
        if "python_async" in usage_examples:
            print(f"\n💻 Usage Example:")
            print(usage_examples["python_async"])

    except Exception as e:
        print(f"❌ Error generating templates: {e}")

    print("\n✅ Resource discovery demo completed!")
    print("\n💡 Next steps:")
    print("   1. Use list_available_resources() to see all resources")
    print("   2. Use suggest_resource_for_tool() for specific migration help")
    print("   3. Use generate_resource_templates() for your configuration")
    print("   4. Update your client code to use resources instead of tools")


async def demo_claude_desktop_usage():
    """Show how this would work with Claude Desktop."""

    print("\n🤖 Claude Desktop Usage Examples")
    print("=" * 50)

    examples = [
        {
            "human": "What resources are available for listing schemas?",
            "claude_action": "Uses list_available_resources() tool",
            "result": "Shows all registry and schema resources with descriptions",
        },
        {
            "human": "How do I replace the list_subjects tool?",
            "claude_action": "Uses suggest_resource_for_tool('list_subjects') tool",
            "result": "Provides migration code and resource URI examples",
        },
        {
            "human": "Generate resource templates for my production environment",
            "claude_action": "Uses generate_resource_templates() tool",
            "result": "Creates customized resource URIs for production setup",
        },
    ]

    for i, example in enumerate(examples, 1):
        print(f"\n{i}️⃣ Example {i}:")
        print(f"   Human: \"{example['human']}\"")
        print(f"   Claude: {example['claude_action']}")
        print(f"   Result: {example['result']}")


if __name__ == "__main__":
    asyncio.run(demo_resource_discovery())
    asyncio.run(demo_claude_desktop_usage())
