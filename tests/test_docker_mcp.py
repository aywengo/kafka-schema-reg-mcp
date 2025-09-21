#!/usr/bin/env python3
"""
Test the MCP server running in Docker container
"""

import asyncio
import os
import platform
import subprocess
from typing import Optional

IMAGE_CANDIDATES = [
    "kafka-schema-registry-mcp:test",  # Preferred, matches build logs
    "kafka-schema-reg-mcp:test",  # Backward compatibility
]


def docker_image_exists(image_name: str) -> bool:
    """Return True if the given Docker image exists locally."""
    try:
        result = subprocess.run(["docker", "images", "-q", image_name], capture_output=True, text=True, timeout=10)
        return result.returncode == 0 and bool(result.stdout.strip())
    except Exception:
        return False


def get_available_image_name() -> Optional[str]:
    """Return the first available image name from candidates, or None if none found."""
    for candidate in IMAGE_CANDIDATES:
        if docker_image_exists(candidate):
            print(f"✅ Docker image '{candidate}' found")
            return candidate
    print("❌ No matching Docker image found. Tried:", ", ".join(IMAGE_CANDIDATES))
    print("   Please build the Docker image first:")
    print("   docker build -t kafka-schema-registry-mcp:test .")
    return None


async def test_docker_mcp_server(image_name: str) -> bool:
    """Test the MCP server running in Docker.

    Args:
        image_name: The Docker image tag to run
    """

    print("🐳 Testing MCP server in Docker container...")

    # Generate unique container name to avoid conflicts
    import random

    container_name = f"test-mcp-server-{random.randint(1000, 9999)}"

    try:
        # Set environment variables for the Docker run
        os.environ["SCHEMA_REGISTRY_URL"] = "http://localhost:38081"

        # Clean up any existing containers with the same name (just in case)
        print("🧹 Pre-cleanup: removing any existing test containers...")
        cleanup_cmd = ["docker", "rm", "-f", container_name]
        subprocess.run(cleanup_cmd, capture_output=True, timeout=10)

        print("📦 Starting MCP server in Docker container...")

        # Start Docker container in background
        # Use host networking on Linux; use host.docker.internal on macOS/Windows
        system_name = platform.system()
        docker_cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            container_name,
        ]

        if system_name == "Linux":
            docker_cmd += ["--network", "host", "-e", "SCHEMA_REGISTRY_URL=http://localhost:38081"]
        else:
            docker_cmd += [
                "-e",
                "SCHEMA_REGISTRY_URL=http://host.docker.internal:38081",
            ]

        docker_cmd += [
            image_name,
            "python",
            "-c",
            "import kafka_schema_registry_unified_mcp as m; print('MCP server test mode'); import time; time.sleep(60)",
        ]

        # Start the container
        result = subprocess.run(docker_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Failed to start Docker container: {result.stderr}")
            return False

        container_id = result.stdout.strip()
        print(f"✅ Started container: {container_id[:12]}")

        # Wait for container to be ready
        print("⏳ Waiting for container to initialize...")
        await asyncio.sleep(5)

        # Check if container is still running
        check_cmd = ["docker", "ps", "-q", "-f", f"id={container_id}"]
        check_result = subprocess.run(check_cmd, capture_output=True, text=True)

        if not check_result.stdout.strip():
            # Container stopped, get logs
            logs_cmd = ["docker", "logs", container_id]
            logs_result = subprocess.run(logs_cmd, capture_output=True, text=True)
            print(f"❌ Container stopped. Logs:\n{logs_result.stdout}")
            print(f"Error logs:\n{logs_result.stderr}")
            return False

        print("✅ Container is running successfully!")

        # Test basic container functionality by checking logs
        print("\n📄 Checking container logs...")
        # Wait a bit more for logs to appear
        await asyncio.sleep(2)
        logs_cmd = ["docker", "logs", container_id]
        logs_result = subprocess.run(logs_cmd, capture_output=True, text=True)

        if logs_result.returncode == 0:
            logs = logs_result.stdout
            error_logs = logs_result.stderr

            if logs and ("MCP server test mode" in logs or "kafka_schema_registry_unified_mcp" in logs):
                print("✅ Container successfully imported MCP module")
                print(f"   Container output: {logs.strip()}")
            elif logs:
                print("✅ Container produced output (logs available)")
                print(f"   Output: {logs.strip()[:200]}{'...' if len(logs.strip()) > 200 else ''}")
            else:
                print("ℹ️  Container is running but no output logs yet")

            if error_logs:
                print(f"   Error logs: {error_logs.strip()[:200]}{'...' if len(error_logs.strip()) > 200 else ''}")
        else:
            print(f"⚠️ Could not get container logs: {logs_result.stderr}")

        # Test container health with a simpler command
        print("\n🔍 Testing container health...")
        health_cmd = [
            "docker",
            "exec",
            container_name,
            "python",
            "-c",
            "print('Container is responsive')",
        ]
        health_result = subprocess.run(health_cmd, capture_output=True, text=True, timeout=10)

        if health_result.returncode == 0:
            print("✅ Container is healthy and responsive")
            if health_result.stdout.strip():
                print(f"   Health check output: {health_result.stdout.strip()}")
        else:
            print(f"⚠️ Container health check failed: {health_result.stderr}")
            # Try a simpler test
            simple_health_cmd = ["docker", "exec", container_name, "echo", "alive"]
            simple_result = subprocess.run(simple_health_cmd, capture_output=True, text=True, timeout=5)
            if simple_result.returncode == 0:
                print("✅ Container basic responsiveness confirmed")

        print("\n🎉 Docker MCP server test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Error during Docker test: {e}")
        return False

    finally:
        # Clean up: stop and remove the test container
        print("\n🧹 Cleaning up test container...")
        try:
            # Force stop container
            stop_cmd = ["docker", "kill", container_name]
            stop_result = subprocess.run(stop_cmd, capture_output=True, timeout=15)

            if stop_result.returncode == 0:
                print("✅ Container stopped")
            else:
                print(f"⚠️ Container stop: {stop_result.stderr.decode() if stop_result.stderr else 'unknown error'}")

            # Remove container
            rm_cmd = ["docker", "rm", container_name]
            rm_result = subprocess.run(rm_cmd, capture_output=True, timeout=10)

            if rm_result.returncode == 0:
                print("✅ Container removed")
            else:
                print(f"⚠️ Container removal: {rm_result.stderr.decode() if rm_result.stderr else 'unknown error'}")

            print("✅ Cleanup completed")
        except subprocess.TimeoutExpired:
            print("⚠️ Cleanup timed out - container may still be running")
        except Exception as cleanup_e:
            print(f"⚠️ Cleanup failed: {cleanup_e}")


async def test_docker_image_exists() -> Optional[str]:
    """Return the available Docker image name, or None if not found."""
    print("🔍 Checking if Docker image exists...")
    try:
        return get_available_image_name()
    except Exception as e:
        print(f"❌ Error checking Docker image: {e}")
        return None


async def main():
    """Main test function."""
    print("🐳 Docker MCP Server Test")
    print("=" * 50)

    # Check if Docker image exists first
    available_image = await test_docker_image_exists()
    if not available_image:
        print("\n❌ Skipping Docker test - image not available")
        return 1

    # Run the Docker test
    success = await test_docker_mcp_server(available_image)

    if success:
        print("\n✅ Docker MCP test passed!")
        return 0
    else:
        print("\n❌ Docker MCP test failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    import sys

    sys.exit(exit_code)
