#!/usr/bin/env python3
"""
Quick test script to verify Schema Registry connections
"""

import json
import os
from typing import Any, Dict

import requests


def test_registry_connection(url: str) -> Dict[str, Any]:
    """Test connection to a Schema Registry instance."""
    try:
        response = requests.get(f"{url}/subjects", timeout=5)
        if response.status_code == 200:
            subjects = response.json()
            return {
                "status": "connected",
                "url": url,
                "subjects_count": len(subjects),
                "subjects": subjects[:5],  # Show first 5 subjects
            }
        else:
            return {
                "status": "error",
                "url": url,
                "error": f"HTTP {response.status_code}: {response.text}",
            }
    except Exception as e:
        return {"status": "error", "url": url, "error": str(e)}


def main():
    # Test DEV registry
    print("\nTesting DEV Schema Registry (localhost:38081)...")
    dev_result = test_registry_connection("http://localhost:38081")
    print(json.dumps(dev_result, indent=2))

    # Test PROD registry
    print("\nTesting PROD Schema Registry (localhost:38082)...")
    prod_result = test_registry_connection("http://localhost:38082")
    print(json.dumps(prod_result, indent=2))

    # Print summary
    print("\nConnection Summary:")
    print(f"DEV Registry: {'✅ Connected' if dev_result['status'] == 'connected' else '❌ Failed'}")
    print(
        f"PROD Registry: {'✅ Connected' if prod_result['status'] == 'connected' else '❌ Failed'}"
    )


if __name__ == "__main__":
    main()
