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
