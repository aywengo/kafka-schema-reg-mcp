#!/bin/bash

# Quick Cleanup Script for Test Containers
# Run this if you encounter Docker container name conflicts

echo "🧹 Cleaning up test containers..."

# Stop and remove specific containers
echo "Stopping containers..."
docker stop kafka-test schema-registry-test 2>/dev/null || true

echo "Removing containers..."
docker rm kafka-test schema-registry-test 2>/dev/null || true

# Clean up with docker-compose
echo "Running docker-compose cleanup..."
docker-compose -f docker-compose.yml down --remove-orphans 2>/dev/null || true

# Clean up networks
echo "Cleaning up networks..."
docker network prune -f 2>/dev/null || true

# Remove any test-related volumes (optional)
echo "Cleaning up volumes..."
docker volume prune -f 2>/dev/null || true

echo "✅ Cleanup complete! You can now run ./start_test_environment.sh" 