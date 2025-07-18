# Security Scan Configuration

This document outlines the security scanning configuration for the Kafka Schema Registry MCP project.

## Overview

The project uses multiple security scanning tools to ensure the safety and security of the codebase and container images. As of the latest update, **ALL security scans across all workflows** are configured to focus on **CRITICAL and HIGH severity issues only**, excluding MEDIUM and LOW severity findings from reports and automated actions.

## Severity Filtering Policy

### Included Severities
- 🔴 **CRITICAL**: Always reported, automatically creates issues, and can fail builds
- 🟠 **HIGH**: Always reported and automatically creates issues for review

### Excluded Severities
- ⚪ **MEDIUM**: Excluded from automated reports and issue creation
- ⚪ **LOW**: Excluded from automated reports and issue creation

### Rationale
This filtering approach allows teams to focus on the most impactful security vulnerabilities while reducing noise from lower-severity issues that may not pose immediate threats in the specific deployment context.

## Security Scanning Workflows

### 1. Main Security Scan (`security-scan.yml`)
**Triggers:**
- Push to `main` and `develop` branches
- Pull requests to `main`
- Scheduled runs on the 7th and 21st of each month at 2 AM UTC

**Components:**
- **Trivy Container Scan**: Vulnerability scanning of Docker images
- **Docker Security Best Practices**: Docker Bench Security scan
- **Dependency Security Check**: Python package vulnerability scanning with Safety and pip-audit
- **Secrets Detection**: TruffleHog scan for leaked credentials

**Severity Configuration:**
- SARIF upload: `CRITICAL,HIGH`
- JSON processing: `CRITICAL,HIGH`
- Table format: `CRITICAL,HIGH`
- Build failure trigger: `CRITICAL` only

### 2. Docker Security Scan (`docker-security-scan.yml`)
**Triggers:**
- Every Monday at 9 AM UTC (scheduled)
- Manual workflow dispatch
- Push to `main` with changes to `Dockerfile`, `requirements.txt`, or the workflow file

**Components:**
- **Trivy Container Scan**: Focused vulnerability scanning
- **Automated Issue Creation**: Only for HIGH and CRITICAL vulnerabilities

**Severity Configuration:**
- All scans: `CRITICAL,HIGH`
- Issue creation: Triggered only by CRITICAL or HIGH findings

### 3. Build Workflow (`build.yml`)
**Triggers:**
- Push to `main` with code/Docker changes
- Pull requests to `main` with code/Docker changes

**Components:**
- **Docker Image Build**: Multi-stage build and testing
- **Trivy Container Scan**: Security validation of built images

**Severity Configuration:**
- Trivy scan: `CRITICAL,HIGH`
- SARIF upload: `CRITICAL,HIGH`

### 4. Test Workflow (`test.yml`)
**Triggers:**
- Pull requests to `main` and `develop`
- Push to `main` and `develop`
- Manual workflow dispatch

**Components:**
- **Code Quality**: Linting, formatting, type checking
- **Docker Build and Test**: Container functionality validation
- **Trivy Security Scan**: Vulnerability scanning with HTML reporting

**Severity Configuration:**
- Trivy scan: `CRITICAL,HIGH`
- HTML report: `CRITICAL,HIGH`
- SARIF upload: `CRITICAL,HIGH`

### 5. Publish Workflow (`publish.yml`)
**Triggers:**
- Push with version tags (`v*`)
- Manual workflow dispatch

**Components:**
- **Multi-platform Build**: AMD64 and ARM64 image builds
- **DockerHub Publishing**: Multi-platform image publishing
- **Trivy Security Scan**: Post-publish vulnerability validation

**Severity Configuration:**
- Trivy scan: `CRITICAL,HIGH`
- Table format output: `CRITICAL,HIGH`
- SARIF upload: `CRITICAL,HIGH`

## Automated Actions

### Issue Creation
- **Trigger**: CRITICAL vulnerabilities found during scheduled scans
- **Labels**: `security`, `vulnerability`, `critical`, `high-priority`
- **Content**: Detailed vulnerability information with remediation guidance

### Build Failures
- **Trigger**: CRITICAL vulnerabilities in pull requests and main branch builds
- **Behavior**: Workflow fails with exit code 1

### Notifications
- Security scan summaries are generated for each workflow run
- Results are uploaded to the GitHub Security tab (SARIF format)
- Artifacts are retained for 30-90 days for audit purposes

## Exception Handling

### Trivy Ignore File (`.trivyignore`)
Documented security exceptions are maintained in the `.trivyignore` file. Each exception includes:
- CVE number
- Clear justification for the exception
- Mitigation measures taken
- References to upstream decisions

### Current Exceptions
The project maintains exceptions for:
- System-level vulnerabilities not exploitable in containerized Python applications
- Base image vulnerabilities marked as `will_not_fix` by upstream maintainers
- Library vulnerabilities not relevant to the application's use case

## Security Reports

### GitHub Security Tab
- All CRITICAL and HIGH severity findings are uploaded in SARIF format
- Historical vulnerability data is maintained
- Integration with GitHub's security advisory database

### Artifacts
Each scan run produces downloadable artifacts containing:
- Trivy scan results (SARIF and JSON formats)
- Dependency scan reports
- Detailed vulnerability tables
- HTML security reports (test workflow)

## Workflow Coverage Summary

| Workflow | Trivy Scan | Severity Filter | SARIF Upload | Issue Creation |
|----------|------------|-----------------|--------------|----------------|
| `security-scan.yml` | ✅ | `CRITICAL,HIGH` | ✅ | Critical only |
| `docker-security-scan.yml` | ✅ | `CRITICAL,HIGH` | ✅ | High/Critical |
| `build.yml` | ✅ | `CRITICAL,HIGH` | ✅ | No |
| `test.yml` | ✅ | `CRITICAL,HIGH` | ✅ | No |
| `publish.yml` | ✅ | `CRITICAL,HIGH` | ✅ | No |

**✅ 100% Coverage**: All workflows now consistently apply the CRITICAL and HIGH severity-only policy.

## Best Practices

### For Developers
1. **Review Security Issues**: Monitor automatically created security issues
2. **Update Dependencies**: Regularly update base images and Python packages
3. **Document Exceptions**: Add justified exceptions to `.trivyignore` with proper documentation
4. **Test Security Changes**: Use `workflow_dispatch` to trigger manual security scans

### For Security Teams
1. **Regular Reviews**: Review the `.trivyignore` file quarterly
2. **Severity Assessment**: Periodically evaluate if the CRITICAL/HIGH-only policy meets security requirements
3. **Exception Audits**: Validate that security exceptions remain relevant and justified

## Configuration Changes

To modify the severity filtering across all workflows:

1. **Include MEDIUM severity**: Change `CRITICAL,HIGH` to `CRITICAL,HIGH,MEDIUM` in all workflow files
2. **Include only CRITICAL**: Change `CRITICAL,HIGH` to `CRITICAL` in all workflow files
3. **Disable filtering**: Remove severity restrictions to scan for all levels

**Files to update:**
- `.github/workflows/security-scan.yml`
- `.github/workflows/docker-security-scan.yml`
- `.github/workflows/build.yml`
- `.github/workflows/test.yml` (already correctly configured)
- `.github/workflows/publish.yml`

## Monitoring and Maintenance

- **Scheduled Scans**: Biweekly for comprehensive security scans, weekly for Docker-specific scans
- **Build-time Scans**: Every build, test, and publish operation includes security validation
- **Dependency Updates**: Monitor for new CVEs affecting documented exceptions
- **Policy Reviews**: Annual review of severity filtering policy effectiveness

## Recent Changes (July 2025)

- ✅ Updated all workflows to consistently exclude MEDIUM and LOW severity issues
- ✅ Enhanced documentation and scan summaries across all workflows
- ✅ Standardized severity filtering policy: `CRITICAL,HIGH` only
- ✅ Improved automated issue creation logic for better signal-to-noise ratio

---

*Last Updated: July 2025*
*Security Policy: CRITICAL and HIGH severity only across all workflows*
