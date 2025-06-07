#!/bin/bash

# Script to manually initialize gh-pages branch for Helm chart repository

set -e

echo "Checking if gh-pages branch exists..."

if git ls-remote --heads origin gh-pages | grep -q gh-pages; then
    echo "gh-pages branch already exists"
    exit 0
fi

echo "Creating gh-pages branch..."

# Save current branch
CURRENT_BRANCH=$(git branch --show-current)

# Create orphan gh-pages branch
git checkout --orphan gh-pages

# Remove all files
git rm -rf .

# Create initial content
cat > README.md << 'EOF'
# Helm Chart Repository

This branch contains the Helm chart repository for kafka-schema-registry-mcp.

## Usage

```bash
helm repo add kafka-schema-registry-mcp https://aywengo.github.io/kafka-schema-reg-mcp
helm repo update
```

## Available Charts

- kafka-schema-registry-mcp: Kafka Schema Registry MCP Server with OAuth2 authentication

For more information, visit the [main repository](https://github.com/aywengo/kafka-schema-reg-mcp).
EOF

# Create basic index.yaml
cat > index.yaml << 'EOF'
apiVersion: v1
entries: {}
generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF

# Add and commit
git add README.md index.yaml
git commit -m "Initialize gh-pages branch for Helm chart repository"

# Push the branch
git push origin gh-pages

# Switch back to original branch
git checkout "$CURRENT_BRANCH"

echo "gh-pages branch created and pushed successfully!" 