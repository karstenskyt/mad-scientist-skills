# System Context Diagram Template (C4 Level 1) — Structurizr DSL

The highest level of abstraction. Shows **who uses the system** and **what other systems it interacts with**. This is the diagram you show to non-technical stakeholders, new team members, and in architecture decision records.

## Purpose

Answer: "What is this system? Who uses it? What does it depend on?"

## Architect's checklist

Before building this diagram, identify:

- [ ] **Primary actors** — Who are the humans that use this system? (end users, admins, operators, external partners)
- [ ] **The system under design** — What is the single system we're documenting? (one blue box)
- [ ] **External systems** — What does it call? What calls it? (APIs, SaaS, legacy systems, partner feeds)
- [ ] **Trust boundaries** — Which interactions cross security/network boundaries?

## Layout

```
+--------------------------------------------------+
|  Tab bar: [Context*] [Container] [Component] ...  |
+--------------------------------------------------+
|                                                    |
|  +---------+                                       |
|  | Person  |---uses--->+------------------+        |
|  +---------+           | System Under     |        |
|                        | Design (blue)    |        |
|  +---------+           +------------------+        |
|  | Person  |---uses------->  |    |                |
|  +---------+                 |    |                |
|                    reads from|    |sends to        |
|                              v    v                |
|                   +--------+  +----------+         |
|                   | Ext DB |  | Ext API  |         |
|                   | (grey) |  | (grey)   |         |
|                   +--------+  +----------+         |
|                                                    |
+--------------------------------------------------+
|  Structurizr DSL Source                    [Copy]  |
+--------------------------------------------------+
```

## Structurizr DSL syntax for this level

```
workspace "System Name" "System Context" {

    model {
        user = person "End User" "A user of the system who does X"
        admin = person "Administrator" "Manages configuration and users"

        system = softwareSystem "System Name" "Core description of what this system does"

        email = softwareSystem "Email Service" "Sendgrid, SES, etc." "External"
        idp = softwareSystem "Identity Provider" "Auth0, Okta, etc." "External"
        legacy = softwareSystem "Legacy Database" "Oracle DB inherited from previous system" "External"

        user -> system "Uses" "HTTPS"
        admin -> system "Configures" "HTTPS"
        system -> email "Sends notifications" "SMTP/API"
        system -> idp "Authenticates via" "OIDC"
        system -> legacy "Reads customer data" "JDBC"
    }

    views {
        systemContext system "SystemContext" "System Context diagram for System Name" {
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
            relationship "Relationship" {
                color #707070
            }
        }
    }

}
```

## Best practices for Level 1

| Practice | Why |
|----------|-----|
| **One internal system only** | This level is about context, not internals. Your system is a single box. |
| **Name every relationship** | "Uses" is lazy. Say what: "Places orders", "Retrieves account balance" |
| **Include the protocol/technology** | Second param on `->`: "HTTPS", "gRPC", "AMQP", "JDBC" |
| **Show all external dependencies** | If it goes down and your system breaks, it belongs here |
| **Tag externals with "External"** | Grey styling signals "not ours" immediately |
| **Limit to 5-15 elements** | More than that and the diagram loses its purpose |
| **Actors have roles, not names** | "Claims Adjuster" not "Bob" |
| **Description is mandatory** | Every element gets a one-line description explaining its responsibility |

## Relationship labeling guide

| Bad | Good | Why |
|-----|------|-----|
| "Connects to" | "Sends order events to" | Describes the data/action |
| "Uses" | "Authenticates users via" | Describes the purpose |
| "Calls" | "Fetches product catalog from" | Describes what flows |
| (no label) | "Reads/writes customer profiles" | Direction + data type |

## Anti-patterns to avoid

- **The God diagram** — 30+ systems on one diagram. Split by subdomain instead.
- **Showing internal structure** — No containers, components, or classes at this level.
- **Missing actors** — If nobody uses it, why does it exist?
- **Orphan systems** — Every external system must have at least one relationship.
- **Symmetric relationships** — If data flows both ways, use two separate `->` with distinct labels, or a single descriptive label like "Reads/writes".
