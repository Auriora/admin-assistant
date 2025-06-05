# Security Scanning

This document describes the security scanning setup for the admin-assistant project.

## Current Security Scanning

This repository uses comprehensive security scanning with both GitHub's CodeQL and additional security tools:

### Tools Used

1. **CodeQL** - GitHub's semantic code analysis engine (primary security scanning)
2. **Safety** - Checks Python dependencies for known security vulnerabilities
3. **Bandit** - Static security analysis for Python code
4. **Semgrep** - Advanced static analysis with security rules

### Security Workflows

#### CodeQL Analysis (`.github/workflows/codeql.yml`)
- **Semantic Code Analysis**: Deep analysis of code structure and data flow
- **Security Vulnerability Detection**: Identifies complex security issues
- **Automated Scheduling**: Runs weekly and on every push/PR
- **GitHub Security Integration**: Results appear in the Security tab

#### Additional Security Scanning (`.github/workflows/test.yml`)
- **Dependency Vulnerability Scanning**: Safety checks all Python dependencies against known vulnerability databases
- **Static Code Analysis**: Bandit scans for common security issues in Python code
- **Advanced Pattern Matching**: Semgrep provides comprehensive security rule checking

### Reports

#### CodeQL Results
- **GitHub Security Tab**: View detailed security findings and recommendations
- **Pull Request Checks**: Automatic security analysis on code changes
- **SARIF Reports**: Structured security analysis results

#### Additional Security Reports
Security scan results are uploaded as artifacts for each workflow run:
- `safety-report.json` - Dependency vulnerability report
- `bandit-report.json` - Static security analysis report
- `semgrep-report.json` - Advanced security pattern analysis

## CodeQL Integration (Enabled)

CodeQL is now enabled and provides comprehensive security analysis for this public repository.

### CodeQL Features

- **Deep Semantic Analysis**: Understands code structure and data flow
- **Security Vulnerability Detection**: Identifies complex security issues including:
  - SQL injection vulnerabilities
  - Cross-site scripting (XSS)
  - Command injection
  - Path traversal
  - Insecure cryptography usage
  - And many more security patterns
- **GitHub Security Integration**: Results appear in the Security tab
- **Automated Scheduling**: Runs weekly and on every push/PR
- **Pull Request Integration**: Security checks on code changes

## Running Security Scans Locally

You can run the security tools locally for development:

```bash
# Install security tools
pip install safety bandit semgrep

# Check dependencies for vulnerabilities
safety check

# Run static security analysis
bandit -r src/

# Run semgrep security rules
semgrep --config=auto src/
```

## Security Best Practices

1. **Regular Updates**: Keep dependencies updated to avoid known vulnerabilities
2. **Code Review**: Review security scan results in pull requests
3. **Secrets Management**: Never commit secrets or API keys to the repository
4. **Input Validation**: Validate all user inputs and external data
5. **Least Privilege**: Follow principle of least privilege for permissions

## Monitoring and Alerts

- Security scan results are available in GitHub Actions artifacts
- Failed security scans will be visible in the workflow status
- Consider setting up notifications for security scan failures

## Future Enhancements

When GitHub Advanced Security becomes available:
1. Enable CodeQL for comprehensive security scanning
2. Enable secret scanning for credential detection
3. Enable dependency review for pull request security checks
4. Set up security advisories for vulnerability disclosure
