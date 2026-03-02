# Dependency Audit Reference

Supply chain security guide covering dependency vulnerability scanning, lockfile integrity, container image security, and CI/CD pipeline hardening.

## Purpose

Answer: "Are our dependencies safe? Is our supply chain secure from build to deploy?"

## Checklist

Before auditing, identify:

- [ ] Which package ecosystems are in use (npm, pip, go, cargo, maven)
- [ ] Whether lockfiles exist and are committed
- [ ] Which CI/CD platform is used (GitHub Actions, GitLab CI, Jenkins, etc.)
- [ ] Whether container images are built and deployed
- [ ] Whether private registries or artifact repositories are used

## Dependency Vulnerability Scanning

### Node.js

```bash
# npm
npm audit
npm audit --production  # only production dependencies
npm audit fix           # auto-fix where possible

# yarn
yarn audit
yarn audit --groups dependencies  # production only

# pnpm
pnpm audit
pnpm audit --prod
```

**Lockfiles:** `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`

**What to look for:**
- Critical and high severity vulnerabilities in production dependencies
- Dev dependencies with known RCE or code execution vulnerabilities
- Packages with no maintained fork or alternative
- Packages with fewer than 100 weekly downloads (higher risk of typosquatting)

### Python

```bash
# pip-audit (recommended)
pip-audit
pip-audit -r requirements.txt
pip-audit --fix  # auto-fix where possible

# safety (alternative)
safety check
safety check -r requirements.txt

# uv
uv run pip-audit
```

**Lockfiles:** `requirements.txt` (pinned), `poetry.lock`, `uv.lock`, `Pipfile.lock`

**What to look for:**
- Unpinned dependencies in `requirements.txt` (use `==` not `>=`)
- `setup.py` with `install_requires` using loose version ranges
- Python packages with known deserialization vulnerabilities (pickle, yaml)
- Packages that pull in native dependencies (harder to audit)

### Go

```bash
# govulncheck (official Go vulnerability checker)
govulncheck ./...

# nancy (alternative for go.sum)
nancy sleuth < go.sum
```

**Lockfiles:** `go.sum`

**What to look for:**
- Vulnerabilities in standard library (Go patches these — ensure Go version is current)
- `replace` directives pointing to forks or local paths
- Vendored dependencies that are out of date

### Rust

```bash
# cargo-audit
cargo audit

# cargo-deny (comprehensive)
cargo deny check advisories
cargo deny check licenses
cargo deny check bans
```

**Lockfiles:** `Cargo.lock`

**What to look for:**
- `unsafe` code in dependencies
- Crates with `build.rs` scripts (can execute arbitrary code at build time)
- Yanked crate versions

### Java

```bash
# OWASP dependency-check
mvn dependency-check:check

# Gradle
gradle dependencyCheckAnalyze
```

**Lockfiles:** `pom.xml` (Maven), `gradle.lockfile`

**What to look for:**
- Log4j and similar high-profile vulnerabilities
- Transitive dependencies pulling in vulnerable versions
- Dependencies from untrusted repositories

---

## Lockfile Integrity

| Check | How to verify | Severity if failing |
|-------|---------------|---------------------|
| Lockfile exists | File present in repo root | High |
| Lockfile committed | Not in `.gitignore` | High |
| Lockfile in sync | `npm ci` / `pip install --require-hashes` succeeds | High |
| Hash verification | Lockfile includes integrity hashes | Medium |
| No manual edits | Lockfile only modified by package manager | Medium |
| CI uses frozen install | CI runs `npm ci` not `npm install` | High |

### Lockfile drift detection

```bash
# Node.js — verify lockfile is in sync
npm ci --dry-run  # fails if lockfile doesn't match package.json

# Python (poetry)
poetry lock --check  # fails if lockfile is outdated

# Go
go mod verify  # verifies checksums in go.sum

# Rust
cargo update --dry-run  # shows what would change
```

---

## Container Image Supply Chain

### Image Selection

| Practice | What to check | Severity |
|----------|---------------|----------|
| Official images | Use official or verified publisher images | High |
| Minimal base | Use distroless, alpine, or scratch — not full OS | Medium |
| Pinned digest | Reference images by `sha256:` digest, not `latest` | High |
| No `latest` tag | All `FROM` directives use specific version tags | Medium |
| Multi-stage builds | Build tools not present in production image | Medium |

### Image Scanning

```bash
# Trivy (comprehensive)
trivy image myapp:latest
trivy image --severity CRITICAL,HIGH myapp:latest

# Grype (alternative)
grype myapp:latest

# Docker Scout
docker scout cves myapp:latest
```

### Image Signing and Verification

| Practice | Tool | Purpose |
|----------|------|---------|
| Sign images | Cosign (Sigstore) | Prove image provenance |
| Verify before deploy | Cosign verify | Ensure image wasn't tampered |
| SBOM generation | Syft | Software bill of materials |
| Admission control | Kyverno / OPA Gatekeeper | Block unsigned images in cluster |

---

## CI/CD Pipeline Security

### GitHub Actions

| Control | What to check | Severity |
|---------|---------------|----------|
| Pinned actions | Use `@sha256:...` not `@v3` or `@latest` | High |
| Minimal permissions | `permissions:` block with least privilege | High |
| No secrets in logs | `add-mask` for dynamic secrets | High |
| Protected branches | `main` requires PR + review | High |
| No `pull_request_target` + checkout | Command injection risk | Critical |
| OIDC for cloud auth | Use `aws-actions/configure-aws-credentials` with OIDC | Medium |
| Dependency review | `actions/dependency-review-action` on PRs | Medium |

**Dangerous patterns to flag:**

```yaml
# DANGEROUS: pull_request_target with PR checkout
on: pull_request_target
steps:
  - uses: actions/checkout@v4
    with:
      ref: ${{ github.event.pull_request.head.sha }}  # runs untrusted code with write access

# DANGEROUS: script injection via issue/PR title
- run: echo "${{ github.event.issue.title }}"  # command injection

# SAFE alternative: use environment variable
- run: echo "$TITLE"
  env:
    TITLE: ${{ github.event.issue.title }}
```

### GitLab CI

| Control | What to check | Severity |
|---------|---------------|----------|
| Protected variables | Secrets only available on protected branches | High |
| No secrets in logs | `masked: true` on CI/CD variables | High |
| Locked runners | Shared runners disabled for sensitive repos | Medium |
| Include verification | `include:` refs pinned to specific commits | Medium |

### General CI/CD

| Control | What to check | Severity |
|---------|---------------|----------|
| Immutable artifacts | Build artifacts are signed and versioned | Medium |
| Reproducible builds | Same source produces same artifact | Medium |
| Build isolation | Build environment is ephemeral and clean | Medium |
| Audit trail | All deployments logged with who, what, when | High |
| Rollback capability | Previous versions can be deployed quickly | Medium |
| Separation of duties | Different people approve and deploy | Medium |

---

## SBOM Generation

Software Bill of Materials (SBOM) provides a complete inventory of all components in your software.

### Generation Tools

| Ecosystem | Tool | Command |
|-----------|------|---------|
| Any | Syft (Anchore) | `syft dir:. -o cyclonedx-json > sbom.json` |
| Any | Trivy | `trivy fs . --format cyclonedx --output sbom.json` |
| Node.js | cdxgen | `cdxgen -o sbom.json` |
| Python | cyclonedx-bom | `cyclonedx-py environment -o sbom.json` |
| Python | pip-audit | `pip-audit --format cyclonedx-json -o sbom.json` |
| Container | Syft | `syft <image> -o cyclonedx-json > sbom.json` |

### SBOM in CI

```yaml
# GitHub Actions example
- name: Generate SBOM
  uses: anchore/sbom-action@v0
  with:
    format: cyclonedx-json
    output-file: sbom.json
- name: Upload SBOM
  uses: actions/upload-artifact@v4
  with:
    name: sbom
    path: sbom.json
```

## Artifact Signing (Enterprise)

| Tool | Purpose | Usage |
|------|---------|-------|
| Cosign (Sigstore) | Sign and verify container images | `cosign sign --key cosign.key <image>` |
| cosign verify | Verify image signature before deploy | `cosign verify --key cosign.pub <image>` |
| GitHub Artifact Attestations | Provenance for GitHub-built artifacts | `gh attestation verify <artifact>` |
| SLSA Provenance | Build provenance attestation | `slsa-verifier verify-artifact <artifact>` |

## GitHub Actions OIDC

Use OIDC for cloud authentication instead of long-lived secrets:

```yaml
# AWS — GOOD (OIDC, no secrets)
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsRole
    aws-region: us-east-1

# AWS — BAD (long-lived secrets)
- uses: aws-actions/configure-aws-credentials@v4
  with:
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

## Automated Dependency Updates

| Tool | Config File | Features |
|------|-------------|----------|
| Dependabot | `.github/dependabot.yml` | Auto-PRs for updates, security alerts |
| Renovate | `renovate.json` | Auto-merge for minor/patch, grouping, schedules |
| Snyk | `.snyk` | Vulnerability scanning + auto-fix PRs |

**Minimum Dependabot config:**
```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
```

---

## Best practices

- Run dependency audits in CI on every pull request
- Block merges on critical and high severity findings
- Set up automated alerts for new CVEs in your dependency tree (Dependabot, Renovate)
- Review lockfile changes in code review (they can hide malicious additions)
- Use a private registry or proxy for production dependencies
- Generate and publish SBOMs with every release
- Use OIDC for CI/CD cloud authentication — never commit cloud credentials
- Pin GitHub Actions to full SHA (not just major version tags)

## Anti-patterns

- Running `npm install` instead of `npm ci` in CI (ignores lockfile)
- Ignoring audit warnings because "they're only in dev dependencies" (build-time RCE is real)
- Using `@latest` or `@v3` for GitHub Actions (tag can be moved to malicious code)
- Disabling Dependabot/Renovate because the PRs are "annoying"
- Never updating dependencies because "if it works, don't touch it"
- Storing secrets as plaintext CI/CD variables instead of using a secrets manager
