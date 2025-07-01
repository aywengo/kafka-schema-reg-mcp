# Security Policy

## Supported Versions

We actively maintain security for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 2.x.x   | ✅ Actively maintained |
| 1.x.x   | ⚠️ Security fixes only |
| < 1.0   | ❌ Not supported |

## Reporting a Vulnerability

If you discover a security vulnerability, we appreciate your help in disclosing it to us responsibly.

### How to Report

1. **Do NOT create a public GitHub issue for security vulnerabilities**
2. Send an email to `security@aywengo.dev` with:
   - Description of the vulnerability
   - Steps to reproduce the issue
   - Potential impact assessment
   - Any suggested fixes (optional)

### What to Expect

- **Acknowledgment**: We will acknowledge receipt within 48 hours
- **Assessment**: Initial assessment within 5 business days
- **Updates**: Regular updates on our progress
- **Resolution**: We aim to resolve critical vulnerabilities within 30 days

## Security Measures

### Container Security

Our Docker images implement several security best practices:

1. **Non-root User**: All containers run as non-root user `mcp`
2. **Minimal Base Image**: Using `python:3.13-slim-bookworm` for reduced attack surface
3. **Multi-stage Builds**: Separate build and runtime stages
4. **Security Updates**: Regular package updates and security patches
5. **Vulnerability Scanning**: Automated Trivy scans on every build
6. **File Permissions**: Restrictive permissions on application files

### Dependency Management

1. **Automated Scanning**: Using `safety` and `pip-audit` for Python dependencies
2. **Dependabot**: Automated dependency updates via GitHub Dependabot
3. **Version Pinning**: Explicit version pinning in `requirements.txt`
4. **Regular Updates**: Monthly security review of all dependencies

### Code Security

1. **Secrets Detection**: Automated scanning with TruffleHog
2. **Static Analysis**: Security-focused code analysis
3. **Input Validation**: Comprehensive input validation and sanitization
4. **OAuth Security**: Proper JWT token validation and OAuth flows

### Infrastructure Security

1. **HTTPS Only**: All communications over HTTPS
2. **Environment Variables**: Sensitive configuration via environment variables
3. **Logging**: Comprehensive security event logging
4. **Monitoring**: Automated security monitoring and alerting

## Vulnerability Management

### Severity Classification

We classify vulnerabilities according to the following severity levels:

- **Critical**: Immediate risk to confidentiality, integrity, or availability
- **High**: Significant risk requiring prompt attention
- **Medium**: Moderate risk to be addressed in regular updates
- **Low**: Minimal risk, addressed during maintenance cycles

### Response Timeline

| Severity | Acknowledgment | Initial Response | Fix Timeline |
|----------|----------------|------------------|--------------|
| Critical | 24 hours | 48 hours | 7 days |
| High | 48 hours | 5 days | 30 days |
| Medium | 5 days | 10 days | 60 days |
| Low | 10 days | 30 days | Next release |

### Security Exception Handling

Some vulnerabilities may not be applicable to our use case. We document these in `.trivyignore` with:

1. **CVE Number**: Specific vulnerability identifier
2. **Rationale**: Why it's not exploitable in our context
3. **References**: Links to upstream decisions or security analyses
4. **Review Date**: When the exception should be reviewed

Examples include:
- System-level vulnerabilities in containerized environments
- Vulnerabilities in unused libraries or features
- Issues marked as "will_not_fix" by upstream maintainers

## Security Best Practices for Users

### Deployment Security

1. **Use Official Images**: Only use official images from Docker Hub
2. **Network Security**: Deploy behind a reverse proxy with HTTPS
3. **Environment Variables**: Use secure methods for configuration
4. **Regular Updates**: Keep images updated with latest security patches

### Configuration Security

1. **OAuth Configuration**: Properly configure OAuth settings
2. **Access Controls**: Implement appropriate access controls
3. **Monitoring**: Enable security monitoring and logging
4. **Backup Security**: Secure backup and disaster recovery procedures

### Schema Registry Security

1. **Authentication**: Enable authentication on Schema Registry
2. **Authorization**: Use proper RBAC for schema management
3. **Network Isolation**: Isolate Schema Registry network access
4. **Audit Logging**: Enable comprehensive audit logging

## Security Updates

### Automated Security Scans

We run automated security scans:

- **Container Vulnerabilities**: Trivy scans on every build
- **Dependency Vulnerabilities**: Python package security checks
- **Secrets Detection**: Source code secrets scanning
- **Docker Security**: Docker Bench Security compliance

### Security Notifications

Subscribe to security notifications:

1. **GitHub Security Advisories**: Watch repository for security updates
2. **Release Notes**: Review security sections in release notes
3. **CVE Tracking**: Monitor CVE databases for relevant vulnerabilities

## Compliance and Standards

Our security practices align with:

- **OWASP Application Security**: Following OWASP guidelines
- **CIS Docker Benchmarks**: Docker security best practices
- **NIST Cybersecurity Framework**: Security controls and processes
- **SSDLC**: Secure Software Development Lifecycle practices

## Contact

For security-related questions:
- **Security Issues**: `security@aywengo.dev`
- **General Security Questions**: Create a GitHub Discussion
- **Documentation**: Check our security documentation in `/docs`

## Acknowledgments

We appreciate the security research community and acknowledge responsible disclosure of vulnerabilities. Contributors who responsibly report security issues may be acknowledged in our security advisories (with their permission).

## License

This security policy is licensed under the same terms as the project.
