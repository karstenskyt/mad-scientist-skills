# STRIDE Threat Model Reference

A structured approach to identifying security threats by categorizing them into six types. Apply STRIDE to each component, data flow, and trust boundary in the system.

## Purpose

Answer: "What can go wrong with this system? What threats exist at each boundary and component?"

## Checklist

Before applying STRIDE, ensure you have:

- [ ] A list of all system components (services, databases, queues, storage, external APIs)
- [ ] A data flow diagram or equivalent understanding of how data moves
- [ ] Identified trust boundaries (where data crosses security contexts)
- [ ] An understanding of actors (users, admins, services, external partners)

## STRIDE Categories

### Spoofing (Authentication threats)

**Definition:** An attacker pretends to be someone or something they are not.

**Examples:**
- Forged authentication tokens (JWT without signature verification)
- IP address spoofing to bypass allow-lists
- DNS spoofing to redirect service-to-service calls
- Email spoofing for phishing or account recovery abuse
- Replaying captured authentication credentials

**Mitigation patterns:**
- Mutual TLS (mTLS) for service-to-service authentication
- JWT with proper signature verification and expiration
- OAuth 2.0 with PKCE for user authentication
- API key rotation and scoping
- Multi-factor authentication for privileged operations
- Certificate pinning for critical connections

**Questions to ask:**
- How does each component prove its identity?
- Can authentication tokens be forged, replayed, or stolen?
- Are service-to-service calls authenticated?

---

### Tampering (Integrity threats)

**Definition:** An attacker modifies data in transit, at rest, or in processing without authorization.

**Examples:**
- Man-in-the-middle modification of API responses
- SQL injection modifying database records
- Tampering with configuration files or environment variables
- Modifying client-side state (cookies, local storage, hidden form fields)
- Altering log entries to cover tracks
- Package substitution in dependency resolution

**Mitigation patterns:**
- TLS 1.2+ for all data in transit
- Digital signatures on critical messages and artifacts
- Input validation and parameterized queries
- Integrity checks (checksums, HMAC) on stored data
- Immutable audit logs (append-only storage)
- Signed commits and verified builds in CI/CD

**Questions to ask:**
- Can data be modified between components without detection?
- Are database writes validated and authorized?
- Can configuration or code be tampered with at rest?

---

### Repudiation (Accountability threats)

**Definition:** An attacker performs an action and later denies it, with no way to prove otherwise.

**Examples:**
- Deleting records without an audit trail
- Performing admin actions with shared credentials
- Modifying data through direct database access (bypassing application logs)
- Claiming "I never placed that order" with no proof of the transaction

**Mitigation patterns:**
- Structured audit logging for all security-relevant events
- Individual user accounts (no shared credentials)
- Centralized, tamper-proof log storage
- Digital signatures on critical transactions
- Timestamp and user attribution on all data modifications
- Log retention policies that meet compliance requirements

**Questions to ask:**
- Can every significant action be attributed to a specific user or service?
- Are audit logs protected from modification or deletion?
- Can actions be reconstructed forensically?

---

### Information Disclosure (Confidentiality threats)

**Definition:** Sensitive data is exposed to unauthorized parties.

**Examples:**
- Stack traces in production error responses
- PII in application logs
- Secrets in source code, environment variables visible to unauthorized users
- Database query results returning more fields than needed
- Side-channel attacks (timing, error messages revealing existence of resources)
- Unencrypted backups or data exports

**Mitigation patterns:**
- Generic error messages in production (log details server-side only)
- Data classification and access controls matching sensitivity
- Field-level encryption for highly sensitive data
- Minimize data returned in API responses (select only needed fields)
- Scrub PII from logs using structured logging with redaction
- Encrypt backups and enforce access controls on backup storage

**Questions to ask:**
- What sensitive data exists and where is it stored?
- Can error messages or logs reveal sensitive information?
- Is data encrypted at rest and in transit?
- Do API responses include more data than the caller needs?

---

### Denial of Service (Availability threats)

**Definition:** The system is made unavailable to legitimate users.

**Examples:**
- HTTP flood overwhelming API endpoints
- Resource exhaustion via expensive queries or operations
- Regex denial of service (ReDoS)
- Storage exhaustion through uncontrolled uploads
- Lock contention from concurrent operations
- Dependency failure cascading to the entire system

**Mitigation patterns:**
- Rate limiting per user, IP, and API key
- Request size limits and timeout enforcement
- Circuit breakers for external dependencies
- Auto-scaling with upper bounds
- Query complexity limits (pagination, depth limits for GraphQL)
- Graceful degradation when dependencies fail
- CDN and DDoS protection for public endpoints

**Questions to ask:**
- What are the most expensive operations in the system?
- Can a single user consume disproportionate resources?
- What happens when an external dependency fails?
- Are there resource limits on all inputs (file size, query complexity, batch size)?

---

### Elevation of Privilege (Authorization threats)

**Definition:** An attacker gains access to resources or operations beyond their authorized level.

**Examples:**
- IDOR (Insecure Direct Object Reference) — accessing other users' data by changing an ID
- Privilege escalation through parameter manipulation (changing `role=user` to `role=admin`)
- Path traversal to access files outside the intended directory
- JWT claim manipulation (changing user ID or role in the token payload)
- Exploiting missing authorization checks on admin endpoints
- Container escape to host system

**Mitigation patterns:**
- Authorization checks on every request (not just the UI)
- Server-side role validation (never trust client-provided roles)
- Indirect object references (map to internal IDs server-side)
- Principle of least privilege for all accounts and services
- Row-level security in databases
- Mandatory access control in containers (AppArmor, SELinux)
- Regular access reviews and permission audits

**Questions to ask:**
- Are authorization checks enforced server-side on every endpoint?
- Can a user access another user's data by manipulating request parameters?
- Are admin functions separated and protected?
- Do service accounts have minimal required permissions?

---

## Trust Boundary Patterns

Trust boundaries are where data crosses from one security context to another. Apply STRIDE at every boundary.

### Client to Server

```
[Browser/App] ---HTTPS---> [API Gateway/Load Balancer] ---> [Application Server]
     ^                              ^                              ^
     |                              |                              |
  Untrusted                    Semi-trusted                    Trusted
  (user input)              (authenticated but                (internal)
                             rate-limited)
```

**Key threats:** Spoofing (auth bypass), Injection (malicious input), DoS (rate abuse)

**Controls:** Input validation, authentication, rate limiting, WAF

### Service to Service

```
[Service A] ---mTLS---> [Service B]
     ^                       ^
     |                       |
  Internal                Internal
  (may have               (may have
   different               different
   privilege)              privilege)
```

**Key threats:** Spoofing (impersonation), Tampering (man-in-the-middle), Elevation (privilege confusion)

**Controls:** mTLS, service mesh, network policies, request signing

### Service to Database

```
[Application Server] ---TLS---> [Database]
         ^                          ^
         |                          |
    Authenticated               Data store
    (connection pool)         (row-level security)
```

**Key threats:** Injection (SQL/NoSQL), Information Disclosure (over-fetching), Tampering (unauthorized writes)

**Controls:** Parameterized queries, connection encryption, least-privilege DB users, row-level security

### Public to Private Network

```
[Internet] ---> [WAF/CDN] ---> [Load Balancer] ---> [Private Subnet]
     ^               ^                ^                     ^
     |               |                |                     |
  Untrusted      Filtering        Routing              Trusted
                                                      (internal)
```

**Key threats:** All six STRIDE categories apply at this boundary

**Controls:** WAF rules, DDoS protection, network segmentation, ingress controls, IDS/IPS

### Cross-Organizational Boundaries

When data, models, or computation cross organizational boundaries — between partner companies, consortia members, data vendors, or collaborative environments — a distinct threat class emerges. These boundaries involve parties that are neither fully trusted nor fully untrusted: they are authorized collaborators with potentially conflicting interests.

#### Outbound Data Sharing

```
[Internal Data Store] ---> [Data Sharing Protocol] ---> [External Partner]
         ^                         ^                          ^
         |                         |                          |
     Your data               Trust boundary              Their environment
   (you control)          (contractual + technical)     (you do NOT control)
```

**Key threats:**
- **Information Disclosure**: Data shared beyond agreed scope; recipient re-identifies anonymized data; aggregate statistics leak individual records
- **Repudiation**: Partner claims they never received data, or denies how they used it
- **Tampering**: Shared data modified after transmission without detection

**Controls:**
- Data minimization (share only what is contractually required)
- Purpose limitation (technical enforcement, not just contractual)
- Differential privacy on shared aggregates (epsilon-bounded noise)
- Immutable audit logs of all shared data with recipient, timestamp, and scope
- Data sharing agreements with explicit retention and deletion clauses
- Delta Sharing or equivalent protocols with revocable access

**Questions to ask:**
- What is the minimum data needed for the partner's purpose?
- Can the partner re-identify individuals from the shared data?
- Is there an audit trail proving what was shared with whom and when?
- Can access be revoked if the agreement is terminated?

#### Inbound Data and Model Ingestion

```
[External Source] ---> [Ingestion Boundary] ---> [Internal Processing]
       ^                       ^                        ^
       |                       |                        |
  Their artifact          Validation gate           Your environment
(model, dataset,       (schema, integrity,        (trusted execution)
  API response)         malware scanning)
```

**Key threats:**
- **Tampering**: Poisoned training data or manipulated model weights that degrade or bias downstream models
- **Spoofing**: Model artifacts that impersonate a trusted source (no provenance verification)
- **Information Disclosure**: Malicious model artifacts that exfiltrate data during inference (trojan models)
- **Elevation of Privilege**: Deserialization attacks via pickle, torch.load, or other unsafe model formats (CWE-502)

**Controls:**
- Schema validation on all ingested data before processing
- Checksum/signature verification on model artifacts
- Prefer safe serialization formats (safetensors, XGBoost JSON) over pickle-based formats
- Malware scanning on downloaded model files (HuggingFace built-in scanning, modelscan)
- Authenticated connections to external registries (explicit tokens, not ambient credentials)
- Sandboxed execution for untrusted models (separate compute, network isolation)

**Questions to ask:**
- Can you verify the provenance of every external model and dataset?
- What happens if an external data source is compromised?
- Are ingested artifacts validated before entering the trusted processing environment?
- Could a malicious model artifact execute code during loading?

#### Collaborative Compute Environments

```
[Party A Data] --->                            ---> [Shared Result]
                    [Collaborative Environment]
[Party B Data] --->  (Clean Room, Federated,   ---> [Shared Result]
                      Secure Enclave)
```

**Key threats:**
- **Information Disclosure**: Raw data leaking through the collaborative environment (insufficient isolation); model updates revealing properties of training data (gradient leakage, membership inference)
- **Tampering**: A malicious participant contributing poisoned updates that degrade the shared model or bias results toward their advantage
- **Spoofing**: A participant claiming to contribute genuine computation while submitting fabricated or recycled results (free-riding)
- **Repudiation**: A participant denying their contribution or disputing the integrity of the collaborative result

**Controls:**
- Secure aggregation (multiparty homomorphic encryption, secret sharing, or trusted execution environments)
- Differential privacy on shared model updates or query results
- Contribution verification (gradient cosine similarity, leave-one-out validation)
- Cryptographic audit trail of all contributions (hash log with participant identity and timestamp)
- Result verification (all parties can confirm aggregation correctness without seeing individual inputs)
- Contractual governance (consortium agreement, purpose limitation, exit clauses)

**Questions to ask:**
- Can any participant infer another participant's raw data from the shared outputs?
- Can a malicious participant degrade the shared result for others?
- Can participants verify the collaborative computation was performed correctly?
- What happens if a participant withdraws — can they demand deletion of their contributions?

---

## Threat Severity Scoring

Score each threat by Likelihood and Impact to determine priority:

### Likelihood

| Level | Criteria |
|-------|----------|
| **High** | Easily exploitable, public attack tools exist, no special access needed |
| **Medium** | Requires some knowledge or access, but feasible for a motivated attacker |
| **Low** | Requires significant insider access, zero-day, or highly unlikely conditions |

### Impact

| Level | Criteria |
|-------|----------|
| **High** | Data breach, full system compromise, regulatory violation, significant financial loss |
| **Medium** | Partial data exposure, service degradation, limited financial impact |
| **Low** | Minor information leak, brief service interruption, no data loss |

### Severity Matrix

|  | Impact: Low | Impact: Medium | Impact: High |
|--|-------------|----------------|--------------|
| **Likelihood: High** | Medium | High | Critical |
| **Likelihood: Medium** | Low | Medium | High |
| **Likelihood: Low** | Low | Low | Medium |

---

## Best practices

- Apply STRIDE to every trust boundary, not just the perimeter
- Involve the development team — they know the implicit trust assumptions
- Update the threat model when architecture changes
- Track threat mitigations as acceptance criteria in stories
- Review the threat model periodically, not just at design time

## Anti-patterns

- Treating threat modeling as a one-time checkbox exercise
- Only modeling external threats (insider threats are often higher impact)
- Assuming a framework handles all security (Django CSRF is great, but custom endpoints may bypass it)
- Ignoring threats because "we'll fix it later" — track them formally
- Scoring all threats as "Medium" to avoid difficult conversations
