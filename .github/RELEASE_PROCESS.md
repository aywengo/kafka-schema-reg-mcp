# Release Process

This document outlines the process for creating releases of the Kafka Schema Registry MCP Server.

## 🚀 Release Workflow

### 1. Prepare Release

Ensure all changes are merged to `main` and tests are passing:

```bash
# Verify tests pass
./run_integration_tests.sh

# Check current status
git status
git log --oneline -10
```

### 2. Create and Push Tag

Create a semantic version tag:

```bash
# Create tag
git tag v1.3.0

# Push tag to trigger release workflow
git push origin v1.3.0
```

### 3. Automated Release Process

The GitHub Actions workflows will automatically:

1. **Build Multi-Platform Images**: AMD64 + ARM64
2. **Security Scan**: Trivy vulnerability scanning
3. **Push to DockerHub**: Multiple tags (v1.3.0, v1.3, v1, latest)
4. **Update DockerHub Description**: Sync README with repository
5. **Create GitHub Release**: With Docker pull commands and changelog
6. **Upload Security Reports**: SARIF files to GitHub Security tab

### 4. Verify Release

After the workflows complete:

```bash
# Test DockerHub image
docker pull aywengo/kafka-schema-reg-mcp:v1.3.0
docker run -p 38000:8000 aywengo/kafka-schema-reg-mcp:v1.3.0

# Verify health
curl http://localhost:38000/
```

## 🔧 Workflow Permissions

The workflows require specific GitHub permissions:

### Build Workflow
- `contents: read` - Access repository code
- `security-events: write` - Upload SARIF security scan results

### Publish Workflow  
- `contents: read` - Access repository code
- `packages: write` - Push to container registry
- `security-events: write` - Upload SARIF security scan results
- `id-token: write` - For container attestation

### Create Release
- `contents: write` - Create GitHub releases

## 🐛 Troubleshooting

### SARIF Upload Failures

If you see "Resource not accessible by integration" errors:

1. **Check Permissions**: Ensure `security-events: write` is set
2. **Repository Settings**: Verify Code Scanning is enabled
3. **Fallback**: The workflow uses `continue-on-error: true` so releases won't fail

### DockerHub Push Failures

1. **Check Secrets**: Verify `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`
2. **Token Permissions**: Ensure token has push permissions
3. **Repository Exists**: Verify `aywengo/kafka-schema-reg-mcp` exists

### Multi-Platform Build Issues

1. **Buildx Setup**: Ensure Docker Buildx is properly configured
2. **Platform Support**: Both AMD64 and ARM64 are supported
3. **Cache Issues**: Clear GitHub Actions cache if needed

## 📋 Release Checklist

Before creating a release:

- [ ] All tests passing (53/53)
- [ ] Documentation updated
- [ ] Version bumped in relevant files
- [ ] CHANGELOG.md updated
- [ ] Docker image builds successfully
- [ ] Security scan passes
- [ ] Export functionality tested

After release:

- [ ] DockerHub image available
- [ ] GitHub release created
- [ ] Documentation links work
- [ ] Multi-platform images working
- [ ] Security reports uploaded

## 🔄 Version Strategy

We follow semantic versioning (SemVer):

- **Major** (v2.0.0): Breaking changes
- **Minor** (v1.3.0): New features, backward compatible  
- **Patch** (v1.3.1): Bug fixes, backward compatible

### Tag Examples

```bash
# New major version
git tag v2.0.0

# New minor version (new features)
git tag v1.4.0  

# Patch release (bug fixes)
git tag v1.3.1
```

## 📚 Documentation

After each release, ensure documentation is updated:

- README.md
- docs/deployment.md  
- docs/api-reference.md
- Docker tags and examples

The workflows automatically update DockerHub descriptions from README.md. 