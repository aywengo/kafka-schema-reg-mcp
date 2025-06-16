#!/usr/bin/env python3
"""
Simple test to check basic Python functionality and imports
"""

print("=== Python Environment Test ===")

# Test 1: Basic Python
print("1. Python is working")

# Test 2: Standard library imports
try:
    import asyncio
    import json
    import os
    import sys

    print("2. ✅ Standard library imports successful")
    print(f"   Python version: {sys.version}")
    print(f"   Current directory: {os.getcwd()}")
except ImportError as e:
    print(f"2. ❌ Standard library import failed: {e}")

# Test 3: Third-party dependencies
dependencies = [
    "mcp",
    "requests",
    "dotenv",
]

for dep in dependencies:
    try:
        __import__(dep)
        print(f"3. ✅ {dep} available")
    except ImportError as e:
        print(f"3. ❌ {dep} not available: {e}")

# Test 4: Check if MCP server files exist
server_files = [
    "kafka_schema_registry_unified_mcp.py",
    "kafka_schema_registry_unified_mcp.py",
]

for file in server_files:
    if os.path.exists(file):
        print(f"4. ✅ {file} exists")
    else:
        print(f"4. ❌ {file} not found")

# Test 5: Try to read a small portion of server file
try:
    with open("kafka_schema_registry_unified_mcp.py", "r") as f:
        first_line = f.readline().strip()
        print(f"5. ✅ Server file readable: {first_line}")
except Exception as e:
    print(f"5. ❌ Cannot read server file: {e}")

# Test 6: Basic network test (this should work even without Schema Registry)
try:
    import requests

    # Test with a simple URL that should always work
    response = requests.get("http://httpbin.org/status/200", timeout=5)
    print(f"6. ✅ Network requests working: {response.status_code}")
except Exception as e:
    print(f"6. ⚠️ Network test failed: {e}")

print("=== Test Complete ===")
