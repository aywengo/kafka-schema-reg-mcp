# 📦 Helm Chart Publishing Guide

This guide shows you how to publish your Kafka Schema Registry MCP Server Helm chart to various repositories.

## 🚀 Quick Start

Use our interactive publishing script:

```bash
./scripts/publish-helm-chart.sh
```

## 📋 Publishing Options

### 1. 🐙 GitHub Pages (Recommended - FREE)

**Best for**: Open-source projects, free hosting, automatic updates

#### Setup Steps:

1. **Enable GitHub Pages in your repository:**
   - Go to `Settings` → `Pages`
   - Source: `GitHub Actions`
   - Save the configuration

2. **Push your changes:**
   ```bash
   git add .
   git commit -m "Add Helm chart and publishing workflow"
   git push origin main
   ```

3. **Create a release tag:**
   ```bash
   git tag v1.8.0
   git push origin v1.8.0
   ```

4. **GitHub Actions will automatically:**
   - ✅ Validate and lint the chart
   - ✅ Package the chart
   - ✅ Create a GitHub release
   - ✅ Publish to GitHub Pages
   - ✅ Update the chart index

5. **Your chart repository will be available at:**
   ```
   https://aywengo.github.io/kafka-schema-reg-mcp
   ```

#### Usage for end users:
```bash
# Add the repository
helm repo add kafka-mcp https://aywengo.github.io/kafka-schema-reg-mcp
helm repo update

# Install the chart
helm install my-mcp-server kafka-mcp/kafka-schema-registry-mcp

# With custom values
helm install my-mcp-server kafka-mcp/kafka-schema-registry-mcp \
  --set auth.enabled=true \
  --set ingress.hosts[0].host=mcp.yourdomain.com
```

---

### 2. 📦 OCI Registry (Docker Hub, GHCR, etc.)

**Best for**: Private registries, enterprise environments, existing container workflows

#### Supported Registries:
- Docker Hub (`registry-1.docker.io`)
- GitHub Container Registry (`ghcr.io`)
- Amazon ECR (`<account>.dkr.ecr.<region>.amazonaws.com`)
- Azure Container Registry (`<registry>.azurecr.io`)
- Google Container Registry (`gcr.io`)

#### Setup Steps:

1. **Login to your registry:**
   ```bash
   # Docker Hub
   helm registry login registry-1.docker.io -u <username>
   
   # GitHub Container Registry
   echo $GITHUB_TOKEN | helm registry login ghcr.io -u <username> --password-stdin
   
   # AWS ECR
   aws ecr get-login-password --region <region> | helm registry login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
   ```

2. **Package and push:**
   ```bash
   # Package the chart
   helm package helm/
   
   # Push to OCI registry
   helm push kafka-schema-registry-mcp-1.8.0.tgz oci://ghcr.io/aywengo
   ```

#### Usage for end users:
```bash
# Install directly from OCI registry
helm install my-mcp-server oci://ghcr.io/aywengo/kafka-schema-registry-mcp --version 1.8.0
```

---

### 3. 🏛️ Artifact Hub

**Best for**: Public discovery, increased visibility, community adoption

Artifact Hub is the official Helm chart discovery platform.

#### Setup Steps:

1. **First, publish to GitHub Pages** (prerequisite)

2. **Create `artifacthub-repo.yml` in your repository root:**
   ```yaml
   # Artifact Hub repository metadata file
   repositoryID: kafka-schema-registry-mcp
   kind: helm
   name: Kafka Schema Registry MCP Server
   displayName: Kafka Schema Registry MCP Server
   description: True MCP server for Kafka Schema Registry with OAuth2 authentication
   url: https://aywengo.github.io/kafka-schema-reg-mcp
   logoURL: https://github.com/aywengo/kafka-schema-reg-mcp/raw/main/docs/assets/logo.png
   links:
     - name: GitHub
       url: https://github.com/aywengo/kafka-schema-reg-mcp
     - name: Documentation
       url: https://github.com/aywengo/kafka-schema-reg-mcp/tree/main/docs
   maintainers:
     - name: aywengo
       email: your-email@example.com
   ```

3. **Submit to Artifact Hub:**
   - Go to [Artifact Hub Control Panel](https://artifacthub.io/control-panel)
   - Add repository: `https://aywengo.github.io/kafka-schema-reg-mcp`
   - Artifact Hub will automatically index your charts

4. **Your chart will be discoverable at:**
   ```
   https://artifacthub.io/packages/helm/kafka-schema-registry-mcp/kafka-schema-registry-mcp
   ```

---

### 4. 🌐 Custom Repository

**Best for**: Private repositories, custom infrastructure, full control

#### Setup Steps:

1. **Package your chart:**
   ```bash
   helm package helm/
   ```

2. **Generate repository index:**
   ```bash
   helm repo index . --url https://charts.yourdomain.com
   ```

3. **Upload to your web server:**
   - Upload `*.tgz` files
   - Upload `index.yaml` file

#### Usage for end users:
```bash
helm repo add your-charts https://charts.yourdomain.com
helm repo update
helm install my-mcp-server your-charts/kafka-schema-registry-mcp
```

---

## 🔧 Advanced Configuration

### Automated Version Management

The GitHub Actions workflow automatically:
- Updates chart version from Git tags
- Validates chart templates
- Runs security scans
- Creates GitHub releases

### Chart Versioning Strategy

We recommend [Semantic Versioning](https://semver.org/):
- `1.8.0` - Major.Minor.Patch
- `1.8.1` - Bug fixes
- `1.9.0` - New features
- `2.0.0` - Breaking changes

### Multi-Environment Publishing

You can publish to multiple repositories:

```bash
# GitHub Pages (public)
git tag v1.8.0 && git push origin v1.8.0

# OCI Registry (private)
helm push kafka-schema-registry-mcp-1.8.0.tgz oci://your-private-registry.com

# Custom Repository (enterprise)
helm repo index . --url https://internal-charts.company.com
```

---

## 📊 Publishing Comparison

| Method | Cost | Difficulty | Best For | Visibility |
|--------|------|------------|----------|------------|
| GitHub Pages | FREE | Easy | Open Source | High |
| OCI Registry | Varies | Medium | Private/Enterprise | Medium |
| Artifact Hub | FREE | Easy | Public Discovery | Very High |
| Custom Repository | Varies | Hard | Full Control | Low |

---

## 🛠️ Troubleshooting

### Common Issues

1. **Chart validation fails:**
   ```bash
   helm lint helm/
   helm template test helm/ --debug
   ```

2. **GitHub Actions fails:**
   - Check repository permissions
   - Verify GitHub Pages is enabled
   - Check workflow logs

3. **OCI push fails:**
   ```bash
   # Verify login
   helm registry login <registry>
   
   # Check chart package
   helm package helm/ --debug
   ```

4. **Custom repository issues:**
   ```bash
   # Verify index generation
   helm repo index . --url <base-url> --debug
   
   # Test repository
   helm repo add test <repo-url>
   helm search repo test/
   ```

### Getting Help

- 📖 [Helm Documentation](https://helm.sh/docs/)
- 🐛 [GitHub Issues](https://github.com/aywengo/kafka-schema-reg-mcp/issues)
- 💬 [Kubernetes Slack #helm-users](https://kubernetes.slack.com/channels/helm-users)

---

## 🎯 Recommended Workflow

For maximum reach and reliability:

1. **Start with GitHub Pages** - Free, reliable, automated
2. **Submit to Artifact Hub** - Increases discoverability
3. **Consider OCI registries** - For private/enterprise use
4. **Monitor usage** - Track downloads and issues

This approach gives you:
- ✅ Free public hosting
- ✅ Automatic updates
- ✅ High visibility
- ✅ Enterprise-ready options
- ✅ Community adoption

---

## 📈 Next Steps

After publishing:

1. **Update documentation** with installation instructions
2. **Create usage examples** for different scenarios
3. **Set up monitoring** for chart usage
4. **Engage with community** for feedback and contributions
5. **Plan regular updates** aligned with application releases

Happy publishing! 🚀 