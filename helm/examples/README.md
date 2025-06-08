# 🔐 OAuth Provider Examples

This directory contains ready-to-use Helm values files for different OAuth 2.0 providers.

## 📋 Available Configurations

| Provider | File | Description |
|----------|------|-------------|
| **🟦 Azure AD** | `values-azure.yaml` | Microsoft Azure AD / Entra ID |
| **🟨 Google** | `values-google.yaml` | Google OAuth 2.0 |
| **🟥 Keycloak** | `values-keycloak.yaml` | Open-source identity management |
| **🟧 Okta** | `values-okta.yaml` | Enterprise identity platform |
| **⚫ GitHub** | `values-github.yaml` | GitHub OAuth 2.0 and GitHub Apps |

## 🚀 Quick Start

### 1. Choose Your Provider

Copy the appropriate values file for your OAuth provider:

```bash
# For Azure AD
cp helm/examples/values-azure.yaml helm/values-production.yaml

# For Google OAuth
cp helm/examples/values-google.yaml helm/values-production.yaml

# For Keycloak
cp helm/examples/values-keycloak.yaml helm/values-production.yaml

# For Okta
cp helm/examples/values-okta.yaml helm/values-production.yaml

# For GitHub OAuth
cp helm/examples/values-github.yaml helm/values-production.yaml
```

### 2. Customize Configuration

Edit your copied values file and replace:
- OAuth client credentials
- Your Kubernetes domain
- Schema Registry URLs
- Kubernetes namespace labels

### 3. Deploy

```bash
cd helm
./deploy-k8s-mcp.sh
```

## 🔧 Configuration Details

### Common Settings

All examples include:
- ✅ **Multi-registry support** for dev/staging/production
- ✅ **Ingress with TLS** using Let's Encrypt
- ✅ **Autoscaling** (2-5 replicas)
- ✅ **Security contexts** (non-root user)
- ✅ **Network policies** for K8s security
- ✅ **Resource limits** for production use

### Provider-Specific Notes

#### **🟦 Azure AD** (`values-azure.yaml`)
- Requires: Tenant ID, Client ID, Client Secret
- Scopes: `openid,email,profile,User.Read`
- Best for: Enterprise Microsoft environments

#### **🟨 Google OAuth** (`values-google.yaml`)
- Requires: Google Client ID, Client Secret
- Scopes: `openid,email,profile`
- Best for: Google Workspace organizations

#### **🟥 Keycloak** (`values-keycloak.yaml`)
- Requires: Keycloak Server URL, Realm, Client ID, Client Secret
- Scopes: `openid,email,profile`
- Best for: Self-hosted enterprise identity management

#### **⚫ GitHub** (`values-github.yaml`)
- Requires: GitHub Client ID, Client Secret
- Scopes: `read:user,user:email,read:org,repo`
- Organization restriction: Optional `GITHUB_ORG` setting
- Best for: GitHub-centric development teams and open source projects

#### **🟧 Okta** (`values-okta.yaml`)
- Requires: Okta domain, Client ID, Client Secret
- Authorization Server: `default` (or custom)
- Best for: Enterprise SaaS environments

## 📚 Documentation

For detailed setup instructions, see:
- **[OAuth Providers Guide](../../docs/oauth-providers-guide.md)** - Complete setup instructions
- **[Kubernetes Deployment Guide](../../K8S-DEPLOYMENT-GUIDE.md)** - Full deployment guide

## 🧪 Testing

After deployment, test your OAuth integration:

```bash
# Check MCP server status
kubectl get pods -n kafka-tools

# Test OAuth endpoint
curl -k https://your-mcp-server.com/health

# Port-forward for local testing
kubectl port-forward -n kafka-tools svc/kafka-schema-registry-mcp 8080:80
```

## 🔒 Security Notes

- **Never commit secrets** to version control
- **Use Kubernetes secrets** for sensitive data
- **Rotate client secrets** regularly
- **Review scope permissions** before deployment
- **Enable network policies** in production

## 🆘 Troubleshooting

Common issues and solutions:

### Invalid OAuth Configuration
```bash
# Check OAuth secret
kubectl get secret -n kafka-tools oauth-secret -o yaml

# Check pod logs
kubectl logs -n kafka-tools deployment/kafka-schema-registry-mcp
```

### Ingress/TLS Issues
```bash
# Check certificate
kubectl describe certificate -n kafka-tools mcp-schema-registry-tls

# Check ingress
kubectl describe ingress -n kafka-tools
```

### Network Connectivity
```bash
# Test Schema Registry access
kubectl exec -n kafka-tools deployment/kafka-schema-registry-mcp -- \
    curl -s http://schema-registry-dev.kafka.svc.cluster.local:8081/subjects
```

## 💡 Tips

- **Start with development values** for testing
- **Use environment-specific files** for CI/CD
- **Test OAuth flow** before production deployment
- **Monitor authentication logs** for security
- **Document your customizations** for team reference

Happy secure schema management! 🔐🚀 