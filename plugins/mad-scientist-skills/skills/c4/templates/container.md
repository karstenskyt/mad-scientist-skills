# Container Diagram Template (C4 Level 2) — Structurizr DSL

Zooms into the system boundary to show the **high-level technology decisions**: applications, services, data stores, and how they communicate. This is the diagram you show to developers joining the team, DevOps engineers, and in technical design documents.

## Purpose

Answer: "What are the major deployable/runnable units? What technologies did we choose? How do they talk to each other?"

## Architect's checklist

Before building this diagram, identify:

- [ ] **Web/mobile applications** — Frontend clients users interact with
- [ ] **API services** — Backend services, microservices, serverless functions
- [ ] **Data stores** — Databases, caches, file storage, search indexes
- [ ] **Message infrastructure** — Queues, event buses, streams
- [ ] **Communication protocols** — HTTP, gRPC, WebSocket, AMQP, SQL
- [ ] **External systems** — Carried forward from Level 1 (grey, outside boundary)
- [ ] **Actors** — Carried forward from Level 1

## Layout

```
+--------------------------------------------------+
|  Tab bar: [Context] [Container*] [Component] ...  |
+--------------------------------------------------+
|                                                    |
|  +------+                                          |
|  | User |                                          |
|  +------+                                          |
|      |  HTTPS                                      |
|      v                                             |
|  +-- System Boundary -------------------------+    |
|  |  +----------+     +----------+             |    |
|  |  | Web App  |---->| API      |             |    |
|  |  | React    | API | Node.js  |             |    |
|  |  +----------+     +----------+             |    |
|  |                     |       |              |    |
|  |              reads/ |       | publishes    |    |
|  |              writes |       |              |    |
|  |                v         v             |    |
|  |  +----------+     +----------+             |    |
|  |  | Database |     | Queue    |             |    |
|  |  | Postgres |     | RabbitMQ |             |    |
|  |  +----------+     +----------+             |    |
|  +--------------------------------------------+    |
|                                                    |
+--------------------------------------------------+
|  Structurizr DSL Source                    [Copy]  |
+--------------------------------------------------+
```

## Structurizr DSL syntax for this level

```
workspace "System Name" "Container diagram" {

    model {
        user = person "End User" "A user who does X"

        system = softwareSystem "System Name" "Core description" {
            spa = container "Single-Page App" "Delivers the user experience via the browser" "React, TypeScript"
            api = container "API Service" "Handles business logic, exposes REST endpoints" "Node.js, Express"
            worker = container "Background Worker" "Processes async jobs: emails, reports, imports" "Node.js, Bull"
            db = container "Database" "Stores users, orders, products, and audit logs" "PostgreSQL 15" "Database"
            cache = container "Cache" "Session storage and query result caching" "Redis 7" "Database"
            queue = container "Message Queue" "Decouples API from async processing" "RabbitMQ" "Queue"
        }

        email = softwareSystem "Email Service" "Sendgrid" "External"
        idp = softwareSystem "Identity Provider" "Auth0" "External"

        user -> spa "Views and interacts with" "HTTPS"
        spa -> api "Makes API calls to" "HTTPS/JSON"
        api -> db "Reads from and writes to" "SQL/TCP"
        api -> cache "Caches queries in" "Redis protocol"
        api -> queue "Publishes jobs to" "AMQP"
        worker -> queue "Consumes jobs from" "AMQP"
        worker -> db "Reads from and writes to" "SQL/TCP"
        worker -> email "Sends emails via" "HTTPS/API"
        api -> idp "Validates tokens with" "OIDC/HTTPS"
    }

    views {
        container system "Containers" "Container diagram for System Name" {
            include *
            autoLayout
        }

        styles {
            element "Person" {
                shape Person
                background #08427B
                color #ffffff
            }
            element "Software System" {
                background #1168BD
                color #ffffff
            }
            element "External" {
                background #999999
                color #ffffff
            }
            element "Container" {
                background #438DD5
                color #ffffff
            }
            element "Database" {
                shape Cylinder
            }
            element "Queue" {
                shape Pipe
            }
            relationship "Relationship" {
                color #707070
            }
        }
    }

}
```

## Best practices for Level 2

| Practice | Why |
|----------|-----|
| **Always specify technology** | 3rd param on container: "React, TypeScript" — this is a technology diagram |
| **Use tags for shape distinction** | Tag databases with "Database" (Cylinder) and queues with "Queue" (Pipe) |
| **Protocol on every relationship** | "HTTPS/JSON", "gRPC/Protobuf", "SQL/TCP", "AMQP" — architects care about this |
| **One system boundary** | You're zooming into ONE system from Level 1. External systems stay outside. |
| **Carry forward actors** | Same people from Level 1, now connecting to specific containers |
| **Carry forward external systems** | Same grey boxes, now with relationships to specific containers |
| **Description = responsibility** | "Handles business logic" not "The API" |
| **Separate read/write when meaningful** | "Reads product catalog from" vs "Writes audit events to" |

## Container type guide

| Container type | Tag | Shape | Examples |
|----------------|-----|-------|----------|
| Web application | (none) | Box | React SPA, Angular app, Next.js |
| Mobile app | (none) | Box | iOS app, Android app, React Native |
| API / Service | (none) | Box | REST API, GraphQL, gRPC service |
| Background worker | (none) | Box | Job processor, cron service, Lambda |
| Database | "Database" | Cylinder | PostgreSQL, MongoDB, DynamoDB |
| File storage | "Database" | Cylinder | S3, Azure Blob, local filesystem |
| Search index | "Database" | Cylinder | Elasticsearch, Algolia |
| Cache | "Database" | Cylinder | Redis, Memcached |
| Message queue | "Queue" | Pipe | RabbitMQ, SQS, Kafka topic |
| Event bus | "Queue" | Pipe | EventBridge, NATS, Kafka |

## Communication protocol reference

| Protocol | Use when |
|----------|----------|
| HTTPS/JSON | REST APIs, webhooks |
| HTTPS/GraphQL | GraphQL endpoints |
| gRPC/Protobuf | Service-to-service, high performance |
| WebSocket | Real-time bidirectional (chat, live updates) |
| AMQP | RabbitMQ message passing |
| SQL/TCP | Direct database connections |
| Redis protocol | Cache reads/writes |
| SMTP | Email delivery |
| S3 API | Object storage |

## Anti-patterns to avoid

- **Showing components inside containers** — That's Level 3. Each container is a single box here.
- **Missing technology labels** — "API" is not enough. "Node.js, Express" or "Go, Chi" tells the real story.
- **Vague relationships** — "Communicates with" says nothing. What data? What protocol?
- **Forgetting infrastructure** — Caches, queues, and search indexes are containers too.
- **Multiple system boundaries** — If you need multiple, you're at Level 1 (Context), not Level 2.
