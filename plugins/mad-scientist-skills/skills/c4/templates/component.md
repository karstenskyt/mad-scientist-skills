# Component Diagram Template (C4 Level 3) — Structurizr DSL

Zooms into a **single container** to show its internal structure: the major classes, modules, or services and how they collaborate. This is the diagram you use during detailed design, code reviews of architecture, and onboarding developers to a specific service.

## Purpose

Answer: "How is this container organized internally? What are its major building blocks and their responsibilities?"

## Architect's checklist

Before building this diagram, identify:

- [ ] **Which container** — You're zooming into exactly ONE container from Level 2
- [ ] **Architectural pattern** — MVC? Hexagonal? Layered? CQRS? This shapes the boundaries
- [ ] **Key components** — Controllers, services, repositories, adapters, handlers, middleware
- [ ] **Internal interfaces** — How do components call each other?
- [ ] **External touchpoints** — Which components talk to databases, queues, or external APIs?

## Layout

```
+--------------------------------------------------+
|  Tab bar: [Context] [Container] [Component*] ...  |
+--------------------------------------------------+
|                                                    |
|  +-- API Service (Container Boundary) --------+   |
|  |                                             |   |
|  |  +------------+    +----------------+       |   |
|  |  | Auth       |--->| User           |       |   |
|  |  | Middleware  |    | Controller     |       |   |
|  |  +------------+    +----------------+       |   |
|  |                          |                  |   |
|  |                     uses |                  |   |
|  |                          v                  |   |
|  |                    +----------------+       |   |
|  |                    | User Service   |       |   |
|  |                    +----------------+       |   |
|  |                     /            \          |   |
|  |                    v              v         |   |
|  |  +------------+    +----------------+       |   |
|  |  | Cache      |    | User           |       |   |
|  |  | Adapter    |    | Repository     |       |   |
|  |  +------------+    +----------------+       |   |
|  +---------------------------------------------+  |
|       |                      |                     |
|       v                      v                     |
|  +----------+          +----------+                |
|  | Redis    |          | Postgres |                |
|  +----------+          +----------+                |
|                                                    |
+--------------------------------------------------+
|  Structurizr DSL Source                    [Copy]  |
+--------------------------------------------------+
```

## Structurizr DSL syntax for this level

```
workspace "Container Name - Components" "Component diagram" {

    model {
        system = softwareSystem "System Name" "What the system does" {
            api = container "API Service" "Handles business logic" "Node.js, Express" {
                authMw = component "Auth Middleware" "Validates JWT tokens, extracts user context" "Express Middleware"
                userCtrl = component "User Controller" "Handles HTTP requests for /api/users/*" "Express Router"
                orderCtrl = component "Order Controller" "Handles HTTP requests for /api/orders/*" "Express Router"
                userSvc = component "User Service" "Business logic for user operations" "TypeScript Class"
                orderSvc = component "Order Service" "Business logic for order lifecycle" "TypeScript Class"
                userRepo = component "User Repository" "Data access for user entities" "TypeScript Class"
                orderRepo = component "Order Repository" "Data access for order entities" "TypeScript Class"
                cacheAdapter = component "Cache Adapter" "Abstraction over Redis for caching" "TypeScript Class"
                eventPub = component "Event Publisher" "Publishes domain events to message queue" "TypeScript Class"
            }

            db = container "Database" "Stores users, orders, products" "PostgreSQL 15" "Database"
            cache = container "Cache" "Cached query results and sessions" "Redis 7" "Database"
            queue = container "Message Queue" "Domain event transport" "RabbitMQ" "Queue"
        }

        idp = softwareSystem "Identity Provider" "Auth0" "External"

        authMw -> idp "Validates tokens with" "OIDC/HTTPS"
        authMw -> userCtrl "Passes authenticated request to"
        authMw -> orderCtrl "Passes authenticated request to"
        userCtrl -> userSvc "Delegates to"
        orderCtrl -> orderSvc "Delegates to"
        userSvc -> userRepo "Reads/writes users via"
        userSvc -> cacheAdapter "Caches user lookups in"
        orderSvc -> orderRepo "Reads/writes orders via"
        orderSvc -> eventPub "Publishes order events to"
        userRepo -> db "Queries" "SQL"
        orderRepo -> db "Queries" "SQL"
        cacheAdapter -> cache "Gets/sets" "Redis protocol"
        eventPub -> queue "Publishes to" "AMQP"
    }

    views {
        component api "Components" "Component diagram for API Service" {
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
            element "Component" {
                background #85BBF0
                color #000000
            }
            relationship "Relationship" {
                color #707070
            }
        }
    }

}
```

## Best practices for Level 3

| Practice | Why |
|----------|-----|
| **One container only** | You're inside a single deployable. Other containers appear as external boxes. |
| **Technology = implementation** | "Express Router", "TypeScript Class", "Prisma Model" — be specific |
| **Follow real code structure** | Components should map to actual files/modules, not abstract ideas |
| **Show the pattern** | If it's layered: Controller -> Service -> Repository. If hexagonal: Adapter -> Port -> UseCase |
| **External containers as context** | Database, cache, queue from Level 2 appear outside the container scope |
| **8-15 components** | Fewer = too vague. More = too detailed (you're approaching Level 4) |
| **Responsibilities, not implementations** | "Handles HTTP requests for /api/users/*" not "Has GET, POST, PUT, DELETE methods" |

## Architectural pattern guides

### Layered / MVC
```
Controller -> Service -> Repository -> Database
              |
          Event Publisher -> Queue
```
Boundaries: Presentation | Business Logic | Data Access

### Hexagonal / Ports & Adapters
```
Driving Adapter (Controller) -> Port (Interface) -> Use Case -> Port (Interface) -> Driven Adapter (Repository)
```
Boundaries: Driving Adapters | Application Core | Driven Adapters

### CQRS
```
Command Controller -> Command Handler -> Write Repository -> Write DB
Query Controller -> Query Handler -> Read Repository -> Read DB
                                                         ^
Event Handler -> Projection Builder ---------____________/
```
Boundaries: Command Side | Query Side | Event Processing

## Component naming conventions

| Layer | Naming pattern | Example |
|-------|---------------|---------|
| HTTP handling | `[Resource]Controller` | `UserController`, `OrderController` |
| Business logic | `[Domain]Service` | `UserService`, `PaymentService` |
| Data access | `[Entity]Repository` | `UserRepository`, `OrderRepository` |
| External integration | `[System]Adapter` or `[System]Client` | `CacheAdapter`, `StripeClient` |
| Event handling | `[Event]Publisher` / `[Event]Handler` | `EventPublisher`, `OrderCreatedHandler` |
| Cross-cutting | `[Concern]Middleware` | `AuthMiddleware`, `RateLimitMiddleware` |
| Validation | `[Resource]Validator` | `OrderValidator`, `InputSanitizer` |

## Anti-patterns to avoid

- **Showing every class** — This is components (logical groupings), not a UML class diagram.
- **Mixing containers** — If you're showing internals of two containers, make two separate diagrams.
- **No relationships** — If a component has no arrows, it's either missing connections or shouldn't be here.
- **Generic descriptions** — "Handles stuff" is not a responsibility. Be specific about what data/operations.
- **Components outside container scope** — In Structurizr DSL, components must be nested inside the container they belong to.
