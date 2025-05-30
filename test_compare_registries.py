#!/usr/bin/env python3
"""Test script to verify compare_registries function works correctly."""

import asyncio
import json
from kafka_schema_registry_multi_mcp import registry_manager, compare_registries

async def test_compare():
    """Test the compare_registries function."""
    print("Testing compare_registries function...")
    
    # List available registries
    registries = registry_manager.list_registries()
    print(f"\nAvailable registries: {registries}")
    
    if len(registries) >= 2:
        # Compare first two registries
        source = registries[0]
        target = registries[1]
        
        print(f"\nComparing registries: {source} vs {target}")
        
        result = await compare_registries(
            source_registry=source,
            target_registry=target,
            include_contexts=True,
            include_configs=True
        )
        
        print("\nComparison result:")
        print(json.dumps(result, indent=2))
    else:
        print("Error: Need at least 2 registries configured to test comparison")

if __name__ == "__main__":
    asyncio.run(test_compare()) 