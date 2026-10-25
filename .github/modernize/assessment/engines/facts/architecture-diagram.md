# Architecture Diagram

Les diagrammes résument les limites entre l'interface, l'API, les services métier, le stockage et les intégrations décrites dans le dépôt.

## Application Architecture

<!-- mermaid-checked: no \n, no em-dash/en-dash, no {} in labels, subgraphs are id["label"], arrows are -->|"label"|, all subgraphs closed by end, ids unique -->
~~~mermaid
flowchart TD
    subgraph aClient["Client Layer"]
        aBrowser["Web browser"]
    end
    subgraph aFrontend["Frontend Layer"]
        aReact["React TypeScript Vite"]
    end
    subgraph aBackend["Backend Layer"]
        aApi["FastAPI REST API"]
        aAuth["JWT and role access"]
        aServices["Quotation business services"]
        aPdf["Jinja2 and WeasyPrint"]
        aEmail["SMTP email service"]
        aCron["Scheduled expiry task"]
    end
    subgraph aData["Data Layer"]
        aPostgres[("PostgreSQL production target")]
        aPdfStore[("Persistent PDF disk target")]
    end
    aSmtp["External SMTP server"]
    aBrowser -->|"uses"| aReact
    aReact -->|"HTTP API calls"| aApi
    aApi --> aAuth
    aApi --> aServices
    aServices -->|"SQLAlchemy"| aPostgres
    aServices --> aPdf
    aPdf -->|"writes PDF"| aPdfStore
    aServices --> aEmail
    aEmail -->|"sends message"| aSmtp
    aCron -->|"expires quotations"| aPostgres
~~~

### Technology Stack Summary

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Frontend | React, TypeScript, Vite | React 19; TypeScript 6; Vite 8 in manifest | Browser application |
| API | Python, FastAPI, Uvicorn | FastAPI 0.141.1; Uvicorn 0.52.0 | HTTP API and application server |
| Data access | SQLAlchemy, Alembic | SQLAlchemy 2.0.51; Alembic 1.20.0 | ORM and database schema migrations |
| Database | SQLite locally; PostgreSQL declared for production | Version target not pinned in manifest | Persist users, quotations, articles and audit |
| Identity | python-jose, Passlib | python-jose 3.5.0; Passlib 1.7.4 | JWT encoding and password hashing |
| PDF | Jinja2, WeasyPrint | Jinja2 3.1.6; WeasyPrint 69.0 | Render HTML template to quotation PDF |
| Email | Python smtplib | Standard library | SMTP delivery of quotation PDF |
| Scheduled work | Celery task code; Render Cron in blueprint | Celery 5.6.3 | Expire quotations after validity |
| Hosting | Render blueprint and Docker | Configured, not a runtime version | Declares web, database, disk and cron services |

### Data Storage & External Services

The local configuration defaults to SQLite; the Render blueprint links the API and the expiry Cron to a PostgreSQL database. Generated PDFs are configured for a persistent Render disk. SMTP is an external dependency configured with environment variables. No Redis service is declared in the current blueprint, despite older README text referring to a worker and Render Key Value. The blueprint is a deployment declaration, not evidence that its resources are running.

### Key Architectural Decisions

- A browser frontend uses a versioned REST API; role enforcement and quotation ownership checks occur in the backend.
- SQLAlchemy models and Alembic migrations separate relational persistence from API schemas and business services.
- PDF rendering, email delivery and expiry are distinct services; their operation depends on system libraries, SMTP configuration and the declared scheduled process.

## Component Relationships

<!-- mermaid-checked: no \n, no em-dash/en-dash, no {} in labels, subgraphs are id["label"], arrows are -->|"label"|, all subgraphs closed by end, ids unique -->
~~~mermaid
flowchart LR
    subgraph cPresentation["Presentation"]
        cWeb["React frontend"]
        cRoutes["FastAPI routers"]
    end
    subgraph cBusiness["Business Logic"]
        cAuth["Auth and role dependencies"]
        cQuoteSvc["Quotation and article routes"]
        cStatusSvc["Status service"]
        cCalcSvc["Calculation service"]
        cPdfSvc["PDF service"]
        cMailSvc["Email service"]
        cDashSvc["Dashboard service"]
        cExpire["Expiry task"]
    end
    subgraph cData["Data Access"]
        cOrm["SQLAlchemy models and sessions"]
        cDb[("SQLite or PostgreSQL")]
        cFiles[("PDF storage")]
    end
    subgraph cInfra["Infrastructure"]
        cSmtp["SMTP provider"]
        cCron["Render Cron declaration"]
        cAudit["Audit log model"]
    end
    cWeb -->|"HTTP JSON"| cRoutes
    cRoutes --> cAuth
    cRoutes --> cQuoteSvc
    cQuoteSvc --> cCalcSvc
    cQuoteSvc --> cStatusSvc
    cQuoteSvc --> cPdfSvc
    cQuoteSvc --> cMailSvc
    cRoutes --> cDashSvc
    cQuoteSvc --> cOrm
    cDashSvc --> cOrm
    cExpire --> cStatusSvc
    cStatusSvc --> cOrm
    cOrm --> cDb
    cPdfSvc --> cFiles
    cMailSvc --> cSmtp
    cQuoteSvc -.->|"records actions"| cAudit
    cCron -->|"runs expiry command"| cExpire
~~~

### Component Inventory

| Component | Layer | Type | Responsibility |
|---|---|---|---|
| React frontend | Presentation | SPA | User views and API requests |
| FastAPI routers | Presentation/API | HTTP routes | Authentication, users, quotations, articles, dashboard, reminders |
| Auth dependencies | Cross-cutting | FastAPI dependencies | Authenticate JWT, authorize role, check quotation ownership |
| Quotation/article routes | Business | API handlers | Validate, persist and audit quotation/article actions |
| Status service | Business | Domain service | Enforce allowed quotation transitions |
| Calculation service | Business | Domain service | Calculate line values and quotation total |
| PDF service | Business | Rendering service | Render quotation template and write PDF |
| Email service | Integration | SMTP adapter | Send quotation PDF and payment reminders |
| Dashboard service | Business | Query service | Summarize quotations and produce chart data |
| Expiry task | Background | Celery task/command | Expire sent quotations after validity |
| SQLAlchemy models | Data access | ORM | Map entities and relations |
| Database | Data | Relational store | Persist application state |
| Audit log | Cross-cutting/data | ORM entity | Record user and system operations |
| SMTP provider | External | Mail server | Deliver outgoing messages |
| Render Cron | Operations | Scheduled job | Declared hourly expiry invocation; runtime not confirmed |
