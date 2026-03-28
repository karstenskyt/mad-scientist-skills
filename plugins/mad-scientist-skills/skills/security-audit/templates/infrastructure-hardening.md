# Infrastructure Hardening Checklist

Cloud-agnostic security checklist for infrastructure-as-code and deployment configurations, with platform-specific guidance for AWS, Azure, GCP, and Kubernetes.

## Purpose

Answer: "Is our infrastructure configured securely? Are we following hardening best practices?"

## Checklist

Before auditing, identify:

- [ ] Which IaC tool is used (Terraform, CloudFormation, Pulumi, CDK, Bicep)
- [ ] Which cloud provider(s) are targeted
- [ ] Whether Kubernetes or containers are involved
- [ ] Where state files and secrets are stored
- [ ] What compliance frameworks apply (SOC2, HIPAA, PCI-DSS, GDPR)

## Universal Hardening Controls

These apply regardless of cloud provider.

### IAM and Access Control

| Control | What to check | Severity if missing |
|---------|---------------|---------------------|
| Least privilege | No `*` in actions or resources | Critical |
| No long-lived credentials | Service accounts use short-lived tokens or instance roles | High |
| MFA enforcement | MFA required for console and privileged operations | High |
| Role separation | Admin, developer, and service roles are distinct | Medium |
| Access reviews | Unused accounts and permissions are revoked | Medium |
| Break-glass procedures | Emergency access is documented and audited | Low |

### Network Security

| Control | What to check | Severity if missing |
|---------|---------------|---------------------|
| No public databases | DB instances have `publicly_accessible = false` | Critical |
| Restricted ingress | No `0.0.0.0/0` on non-public ports | Critical |
| Network segmentation | Web, app, and data tiers in separate subnets | High |
| Egress filtering | Outbound traffic restricted to known destinations | Medium |
| VPC flow logs | Network traffic is logged for forensics | Medium |
| DNS security | DNSSEC enabled, private DNS zones for internal services | Low |

### Encryption

| Control | What to check | Severity if missing |
|---------|---------------|---------------------|
| Encryption at rest | All data stores encrypted (databases, object storage, volumes) | High |
| TLS in transit | All connections use TLS 1.2+ | High |
| KMS-managed keys | Encryption keys managed by cloud KMS, not hardcoded | High |
| Key rotation | Automatic key rotation enabled | Medium |
| Certificate management | Certificates auto-renewed (ACM, Let's Encrypt) | Medium |

### Container Security

| Control | What to check | Severity if missing |
|---------|---------------|---------------------|
| Non-root user | Containers run as non-root user | High |
| Read-only filesystem | Root filesystem is read-only where possible | Medium |
| Resource limits | CPU and memory limits set | Medium |
| Image pinning | Base images pinned to digest, not `latest` tag | Medium |
| No privileged mode | `privileged: false` on all containers | Critical |
| Health checks | Liveness and readiness probes defined | Medium |
| Minimal base image | Use distroless or alpine, not full OS images | Low |

### Logging and Monitoring

| Control | What to check | Severity if missing |
|---------|---------------|---------------------|
| Audit logging | API calls and admin actions logged | High |
| Centralized logs | Logs shipped to central, immutable storage | Medium |
| Log retention | Retention meets compliance requirements | Medium |
| Alerting | Alerts on security-relevant events | Medium |
| No secrets in logs | Sensitive data redacted from log output | High |

### Backup and Recovery

| Control | What to check | Severity if missing |
|---------|---------------|---------------------|
| Automated backups | Databases and critical data backed up automatically | High |
| Backup encryption | Backups encrypted at rest | High |
| Recovery testing | Backups tested for recoverability periodically | Medium |
| Cross-region | Critical backups replicated to a second region | Medium |

### Confidential Computing

Confidential computing protects data **in use** — the third leg of the data protection triad (alongside encryption at rest and in transit). Trusted Execution Environments (TEEs) create hardware-secured enclaves where code and data are invisible to the host OS, hypervisor, and cloud provider during processing.

| Control | What to check | Severity if missing |
|---------|---------------|---------------------|
| TEE availability | If processing sensitive data in shared/cloud environments: are confidential computing VM types available and used? | Context-dependent |
| Attestation verification | TEE attestation reports are cryptographically verified before trusting enclave output | High (if TEEs are used) |
| Memory encryption | Hardware memory encryption enabled (AMD SEV-SNP, Intel TDX) | High (if TEEs are used) |
| Enclave minimization | Only security-critical code runs inside the TEE; non-sensitive logic runs outside | Medium |

**Platform-specific TEE support:**

| Provider | TEE Technology | VM Types / Services |
|----------|---------------|---------------------|
| **Azure** | AMD SEV-SNP | DCasv5, DCadsv5, ECasv5 series; Azure Databricks (classic clusters only, not serverless) |
| **Azure** | Intel TDX | DCesv5, ECesv5 series (limited GA) |
| **AWS** | Nitro Enclaves | Any Nitro-based instance with `EnclaveOptions.Enabled = true` |
| **GCP** | AMD SEV-SNP | C2D, N2D confidential VM types; Confidential GKE nodes |
| **GCP** | Intel TDX | C3 confidential VMs (preview) |

**Important constraints:**
- Serverless compute (AWS Lambda, Azure Functions, Databricks Serverless) generally does **not** support confidential computing — customers cannot select VM types
- Databricks Clean Rooms run on serverless and therefore **cannot** use TEEs
- TEE-based confidential computing requires explicit cluster or VM configuration; it is not a default

**When to require confidential computing:**
- Processing third-party data under contractual obligation to protect data in use
- Multi-party computation where no single party should see all inputs
- Aggregation servers in collaborative/federated architectures
- Regulatory requirements that mandate data-in-use protection

### Privacy-Preserving Computation

Beyond encryption, these techniques enable computation over sensitive data while mathematically limiting what can be learned from the outputs.

| Technique | What it does | When to use | Maturity |
|-----------|-------------|-------------|----------|
| **Differential Privacy (DP)** | Adds calibrated noise to query outputs or model updates, bounding what can be inferred about any individual record | Query-level privacy on analytics; training-time privacy for ML models (DP-SGD) | Production-ready (Google, Apple, US Census deploy at scale) |
| **Homomorphic Encryption (HE)** | Compute on encrypted data without decryption; server never sees plaintext | Cross-organizational analytics where a central server aggregates encrypted contributions from multiple parties | Practical for addition/multiplication-heavy workloads (CKKS, BFV schemes); latency overhead 100-1000x |
| **Secure Multi-Party Computation (SMPC)** | Multiple parties jointly compute a function over their inputs without revealing individual inputs to each other | Joint analytics between organizations with conflicting interests and no trusted third party | Research-to-production; practical for 2-10 parties with modern protocols |
| **Private Set Intersection (PSI)** | Two parties discover common elements in their datasets without revealing non-overlapping elements | Entity matching across organizations (e.g., finding shared customers without exposing full lists) | Production-ready (Google PSI library); used in ad measurement |

**Libraries and tools:**

| Library | Technique | Language |
|---------|-----------|----------|
| OpenDP | Differential privacy | Python, Rust |
| IBM diffprivlib | Differential privacy (scikit-learn compatible) | Python |
| Google DP Library | Differential privacy | C++, Java, Go |
| Microsoft SEAL | Homomorphic encryption (BFV, CKKS) | C++ |
| Concrete ML (Zama) | HE-based ML inference | Python |
| MP-SPDZ | Multi-party computation | C++ with Python bindings |
| Google PSI | Private set intersection | C++ |

**Questions to ask:**
- Does the system process data from multiple parties who should not see each other's raw data?
- Do query or model outputs need mathematical privacy guarantees?
- Are there contractual or regulatory requirements for data-in-use protection?

---

## Platform-Specific Guidance

### AWS

| Service | Control | What to check |
|---------|---------|---------------|
| S3 | Block public access | `aws_s3_bucket_public_access_block` with all four flags `true` |
| S3 | Encryption | `server_side_encryption_configuration` present |
| S3 | Versioning | `versioning.enabled = true` for important buckets |
| RDS | No public access | `publicly_accessible = false` |
| RDS | Encryption | `storage_encrypted = true` |
| RDS | Multi-AZ | `multi_az = true` for production |
| EC2 | IMDSv2 | `metadata_options.http_tokens = "required"` |
| EC2 | No public IP | Use NAT gateway for outbound, not public IPs |
| IAM | No inline policies | Use managed policies attached to roles |
| IAM | No `*` resources | Scope permissions to specific ARNs |
| Lambda | Minimal permissions | Function role scoped to exact resources needed |
| CloudTrail | Enabled | Multi-region trail with log file validation |
| GuardDuty | Enabled | Active in all regions |
| KMS | Key rotation | `enable_key_rotation = true` |
| VPC | Flow logs | Enabled on all VPCs |
| ELB | TLS 1.2+ | Security policy `ELBSecurityPolicy-TLS13-1-2-2021-06` or newer |
| EBS | Encryption | Default EBS encryption enabled for the account |
| Secrets Manager | Rotation | Automatic rotation configured |

### Azure

| Service | Control | What to check |
|---------|---------|---------------|
| Storage | No public access | `allow_blob_public_access = false` |
| Storage | Encryption | Customer-managed keys for sensitive data |
| Storage | HTTPS only | `enable_https_traffic_only = true` |
| SQL Database | No public access | `public_network_access_enabled = false` |
| SQL Database | TDE | Transparent data encryption enabled |
| Key Vault | Soft delete | `soft_delete_enabled = true` |
| Key Vault | Purge protection | `purge_protection_enabled = true` |
| App Service | HTTPS only | `https_only = true` |
| App Service | Managed identity | Use managed identity, not connection strings |
| NSG | No open ports | No `*` in source for non-public ports |
| Activity Log | Export | Exported to Log Analytics workspace |
| Defender | Enabled | Microsoft Defender for Cloud enabled |
| AKS | RBAC | Azure RBAC enabled for Kubernetes |
| AKS | Network policy | Calico or Azure network policies enabled |

### GCP

| Service | Control | What to check |
|---------|---------|---------------|
| GCS | No public access | `uniform_bucket_level_access = true` |
| GCS | Encryption | CMEK for sensitive data |
| Cloud SQL | No public IP | `ip_configuration.ipv4_enabled = false` |
| Cloud SQL | SSL | `require_ssl = true` |
| GKE | Private cluster | `private_cluster_config.enable_private_nodes = true` |
| GKE | Workload identity | Enabled, not node service accounts |
| GKE | Shielded nodes | `enable_shielded_nodes = true` |
| IAM | No primitive roles | Don't use `roles/editor` or `roles/owner` for service accounts |
| IAM | Workload identity | Use WIF for external access, not service account keys |
| VPC | Private Google Access | Enabled on subnets |
| VPC | Firewall rules | No `0.0.0.0/0` source ranges on non-public ports |
| Cloud Audit | Data access logs | Enabled for all services |
| Cloud Armor | WAF | Configured for public-facing services |

### Kubernetes

| Resource | Control | What to check |
|----------|---------|---------------|
| Pod | Security context | `runAsNonRoot: true`, `readOnlyRootFilesystem: true` |
| Pod | Resource limits | `resources.limits.cpu` and `resources.limits.memory` set |
| Pod | No privileged | `securityContext.privileged: false` |
| Pod | Capabilities | `drop: ["ALL"]`, add only what's needed |
| Pod | Service account | Custom SA with minimal RBAC, not `default` |
| NetworkPolicy | Default deny | Default deny ingress and egress policies |
| NetworkPolicy | Explicit allow | Only required traffic allowed |
| RBAC | Least privilege | No `cluster-admin` for workloads |
| RBAC | No wildcard | No `*` verbs or resources |
| Secret | Encryption | etcd encryption at rest enabled |
| Secret | External secrets | Use external-secrets-operator or sealed-secrets |
| Ingress | TLS | TLS termination configured |
| Ingress | WAF | Web application firewall in front of ingress |
| PodDisruptionBudget | Availability | PDBs defined for critical workloads |
| PodSecurityStandard | Enforcement | `restricted` or `baseline` enforced at namespace level |

---

## Terraform-Specific Controls

| Control | What to check | Severity |
|---------|---------------|----------|
| State encryption | Remote backend with encryption (S3+SSE, GCS+CMEK, Azure+encryption) | Critical |
| State access | State file access restricted to CI/CD and designated operators | Critical |
| State locking | DynamoDB (AWS), GCS (GCP), or blob lease (Azure) locking enabled | High |
| Provider pinning | Provider versions pinned with `required_providers` constraints | High |
| Module pinning | Module sources pinned to specific versions or commits | High |
| Sensitive outputs | Outputs containing secrets marked `sensitive = true` | High |
| No local state | `terraform.tfstate` in `.gitignore`, not committed | Critical |
| Plan review | `terraform plan` reviewed before every apply | Medium |
| Drift detection | Regular plan runs to detect manual changes | Medium |
| Variable validation | `validation` blocks on input variables | Low |

---

## Enterprise Tier Controls

These controls require paid cloud services or enterprise subscriptions. Document applicability and configuration status.

### Web Application Firewall (WAF)

| Provider | Service | What to configure |
|----------|---------|------------------|
| AWS | AWS WAF v2 | Managed rule groups (AWSManagedRulesCommonRuleSet, SQLiRuleSet, XSSRuleSet) |
| Azure | Azure Front Door WAF | OWASP 3.2 rule set, custom rules, bot protection |
| GCP | Cloud Armor | Pre-configured WAF rules, rate limiting, bot management |
| Cloudflare | Cloudflare WAF | OWASP rule set, managed rules, custom rules |

### DDoS Protection

| Provider | Service | Tier |
|----------|---------|------|
| AWS | AWS Shield Advanced | $3,000/month — automatic DDoS mitigation, cost protection |
| Azure | Azure DDoS Protection | Standard plan — volumetric + protocol + application layer |
| GCP | Cloud Armor | Adaptive Protection — ML-based DDoS detection |
| Cloudflare | Enterprise | Unlimited DDoS mitigation, analytics |

### Security Information and Event Management (SIEM)

| Service | Integration Pattern |
|---------|-------------------|
| Splunk | Forward CloudTrail, VPC flow logs, application logs |
| Datadog Security | Agent-based log collection, cloud integrations |
| AWS Security Hub | Aggregate findings from GuardDuty, Inspector, Macie |
| Elastic Security | Filebeat + Elastic Agent, cloud-native integrations |

### Container Runtime Security

| Tool | Purpose |
|------|---------|
| Falco | Runtime threat detection (unexpected syscalls, file access, network activity) |
| Sysdig Secure | Runtime security + compliance + forensics |
| Aqua Security | Full container lifecycle security |
| Prisma Cloud | Cloud-native application protection platform |

---

## Best practices

- Start with the universal controls, then add platform-specific checks
- Automate checks with tools like `tfsec`, `checkov`, `trivy`, or `kube-bench`
- Treat infrastructure code with the same rigor as application code (review, test, version)
- Document exceptions with justification and expiration dates
- Re-audit after every significant infrastructure change

## Anti-patterns

- "We'll harden it after launch" — hardening debt compounds rapidly
- Disabling security controls to make something work (e.g., `publicly_accessible = true` for debugging)
- Copy-pasting IAM policies with `*` permissions from Stack Overflow
- Storing Terraform state locally or in an unencrypted bucket
- Using `latest` tags for container images or Terraform providers
